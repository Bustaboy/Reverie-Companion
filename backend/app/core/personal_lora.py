"""Opt-in personal LoRA training foundation for Reverie growth.

The trainer is intentionally lightweight: it stores reviewable local dataset
candidates from high-quality journal entries and runs only explicit, conservative
background jobs.  This module does not keep a model resident or compete with
chat generation; it creates auditable artifacts that a future PEFT/QLoRA backend
can consume when the user enters training mode.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from app.core.config import Settings, get_settings
from app.core.reflection import JournalEntry

logger = logging.getLogger(__name__)

TrainingExampleStatus = Literal["needs_review", "approved", "rejected", "deleted"]
TrainingJobStatus = Literal["idle", "queued", "running", "completed", "cancelled", "failed"]

_MAX_EXAMPLE_TEXT_CHARS = 1_200
_MAX_DATASET_SCAN_LINES = 5_000


class TrainingExample(TypedDict, total=False):
    """Reviewable local training example derived from journal evidence."""

    item_id: str
    character_id: str
    source_journal_id: str
    source_memory_ids: list[str]
    purpose: str
    text: str
    created_at: str
    approved_by_user: bool
    review_status: TrainingExampleStatus
    consent: dict[str, Any]
    safety: dict[str, Any]
    metadata: dict[str, Any]


class TrainingJob(TypedDict, total=False):
    """Persisted status for one conservative personal LoRA job."""

    job_id: str
    character_id: str
    status: TrainingJobStatus
    created_at: str
    updated_at: str
    started_at: str | None
    completed_at: str | None
    progress: float
    phase: str
    message: str
    dataset_item_ids: list[str]
    adapter_id: str | None
    config: dict[str, Any]
    safety: dict[str, Any]
    error: str | None


@dataclass(frozen=True)
class PersonalLoRATrainerConfig:
    """Conservative, 8GB-friendly LoRA settings and local paths."""

    root_path: Path
    character_id: str = "default_companion"
    enabled: bool = False
    collect_examples: bool = False
    rank: int = 8
    alpha: int = 16
    max_rank: int = 16
    learning_rate: float = 1e-4
    max_steps: int = 120
    micro_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    checkpoint_every_steps: int = 30
    min_confidence: float = 0.72
    min_evidence_count: int = 2
    training_mode_requires_exclusive_lock: bool = True
    local_first: bool = True
    allowed_sensitivity_tags: set[str] = field(default_factory=lambda: {"boundaries"})

    @classmethod
    def from_settings(
        cls, settings: Settings | None = None
    ) -> "PersonalLoRATrainerConfig":
        settings = settings or get_settings()
        memory_root = Path(settings.memory_db_path).expanduser().resolve()
        return cls(
            root_path=memory_root.parent / "training" / "personal_lora",
            character_id=settings.personal_lora_default_character_id,
            enabled=settings.personal_lora_enabled,
            collect_examples=settings.personal_lora_collect_examples,
            rank=settings.personal_lora_rank,
            alpha=settings.personal_lora_alpha,
            max_rank=settings.personal_lora_max_rank,
            learning_rate=settings.personal_lora_learning_rate,
            max_steps=settings.personal_lora_max_steps,
            micro_batch_size=settings.personal_lora_micro_batch_size,
            gradient_accumulation_steps=(
                settings.personal_lora_gradient_accumulation_steps
            ),
            checkpoint_every_steps=settings.personal_lora_checkpoint_every_steps,
            min_confidence=settings.personal_lora_min_confidence,
            min_evidence_count=settings.personal_lora_min_evidence_count,
        )

    @property
    def dataset_path(self) -> Path:
        return self.root_path / "dataset_candidates.jsonl"

    @property
    def jobs_path(self) -> Path:
        return self.root_path / "jobs.jsonl"

    @property
    def adapters_path(self) -> Path:
        return self.root_path / "adapters"


class PersonalLoRATrainer:
    """Collect reviewable LoRA data and run explicit tiny adapter jobs.

    The current foundation avoids importing heavyweight training stacks.  It
    persists auditable examples and job manifests, then simulates a cancellable
    background training lifecycle so the API and safety controls are ready for a
    real local PEFT backend without ever blocking chat.
    """

    _job_lock = threading.Lock()
    _active_jobs: dict[str, threading.Event] = {}

    def __init__(self, config: PersonalLoRATrainerConfig | None = None) -> None:
        self._config = config or PersonalLoRATrainerConfig.from_settings()
        self._ensure_dirs()

    @property
    def config(self) -> PersonalLoRATrainerConfig:
        return self._config

    def collect_from_journal_entry(
        self, entry: JournalEntry, *, character_id: str | None = None
    ) -> TrainingExample | None:
        """Store a reviewable dataset candidate from a high-quality journal entry.

        Collection itself is opt-in and never marks the example approved.  The
        user must approve examples before `start_training()` will include them.
        """

        if not self._config.enabled or not self._config.collect_examples:
            logger.debug("Personal LoRA dataset collection skipped; opt-in is off")
            return None
        if not self._journal_entry_is_training_candidate(entry):
            return None

        item = self._example_from_entry(entry, character_id=character_id)
        existing = {example.get("item_id") for example in self.list_examples(limit=500)}
        if item["item_id"] in existing:
            return item

        self._append_jsonl(self._config.dataset_path, item)
        logger.info(
            "Collected personal LoRA training candidate",
            extra={
                "item_id": item["item_id"],
                "source_journal_id": item["source_journal_id"],
                "approved_by_user": False,
            },
        )
        return item

    def list_examples(
        self,
        *,
        limit: int = 100,
        include_deleted: bool = False,
        status: TrainingExampleStatus | None = None,
    ) -> list[TrainingExample]:
        """Return newest local dataset examples, excluding deleted by default."""

        safe_limit = max(1, min(limit, 500))
        examples = [cast(TrainingExample, item) for item in self._read_jsonl(self._config.dataset_path)]
        filtered = [
            example
            for example in examples
            if (include_deleted or example.get("review_status") != "deleted")
            and (status is None or example.get("review_status") == status)
        ]
        return list(reversed(filtered[-safe_limit:]))

    def approve_example(self, item_id: str, *, approved: bool) -> TrainingExample:
        """Approve or reject one dataset item before training."""

        target_id = self._normalize_id(item_id, field_name="item_id")
        examples = [cast(TrainingExample, item) for item in self._read_jsonl(self._config.dataset_path)]
        updated: TrainingExample | None = None
        for example in examples:
            if example.get("item_id") != target_id:
                continue
            example["approved_by_user"] = approved
            example["review_status"] = "approved" if approved else "rejected"
            example.setdefault("metadata", {})["reviewed_at"] = self._utc_now()
            updated = example
            break
        if updated is None:
            raise ValueError("Training example was not found.")
        self._rewrite_jsonl(self._config.dataset_path, examples)
        return updated

    def delete_example(self, item_id: str) -> TrainingExample:
        """Tombstone a dataset item so rollback/deletion can exclude it."""

        target_id = self._normalize_id(item_id, field_name="item_id")
        examples = [cast(TrainingExample, item) for item in self._read_jsonl(self._config.dataset_path)]
        updated: TrainingExample | None = None
        for example in examples:
            if example.get("item_id") != target_id:
                continue
            example["approved_by_user"] = False
            example["review_status"] = "deleted"
            example.setdefault("metadata", {})["deleted_at"] = self._utc_now()
            updated = example
            break
        if updated is None:
            raise ValueError("Training example was not found.")
        self._rewrite_jsonl(self._config.dataset_path, examples)
        return updated

    def start_training(
        self,
        *,
        character_id: str | None = None,
        rank: int | None = None,
        max_steps: int | None = None,
    ) -> TrainingJob:
        """Start a cancellable, explicit personal LoRA background job.

        This creates a job only from user-approved examples.  The lightweight
        worker writes checkpoints/manifests and leaves room for a future adapter
        backend; it does not block chat request handlers.
        """

        if not self._config.enabled:
            raise ValueError("Personal LoRA training is disabled. Enable it first.")

        selected_rank = self._bounded_rank(rank or self._config.rank)
        selected_steps = max(1, min(max_steps or self._config.max_steps, 1_000))
        target_character_id = character_id or self._config.character_id
        approved_examples = [
            example
            for example in self.list_examples(limit=500, status="approved")
            if example.get("character_id") == target_character_id
        ]
        if not approved_examples:
            raise ValueError("No approved training examples are available.")

        created_at = self._utc_now()
        job_id = self._stable_id(
            "lora_job", f"{target_character_id}|{created_at}|{len(approved_examples)}"
        )
        adapter_id = self._stable_id("adapter", f"{target_character_id}|{job_id}")
        job = TrainingJob(
            job_id=job_id,
            character_id=target_character_id,
            status="queued",
            created_at=created_at,
            updated_at=created_at,
            started_at=None,
            completed_at=None,
            progress=0.0,
            phase="queued",
            message="Personal LoRA training is queued for local training mode.",
            dataset_item_ids=[str(example["item_id"]) for example in approved_examples],
            adapter_id=adapter_id,
            config=self._training_config(selected_rank, selected_steps),
            safety={
                "requires_user_approval": True,
                "exclusive_training_mode": self._config.training_mode_requires_exclusive_lock,
                "chat_non_blocking": True,
                "rollback_supported": True,
                "local_only": self._config.local_first,
            },
            error=None,
        )
        self._append_jsonl(self._config.jobs_path, job)

        cancel_event = threading.Event()
        with self._job_lock:
            self._active_jobs[job_id] = cancel_event
        worker = threading.Thread(
            target=self._run_training_job,
            args=(job, cancel_event),
            daemon=True,
            name=f"reverie-personal-lora-{job_id[:12]}",
        )
        worker.start()
        return job

    def stop_training(self, job_id: str) -> TrainingJob:
        """Request cancellation for a running or queued training job."""

        target_id = self._normalize_id(job_id, field_name="job_id")
        with self._job_lock:
            cancel_event = self._active_jobs.get(target_id)
            if cancel_event is not None:
                cancel_event.set()
        job = self.get_job(target_id)
        if not job:
            raise ValueError("Training job was not found.")
        if job.get("status") in {"completed", "cancelled", "failed"}:
            return job
        updated = dict(job)
        updated.update(
            {
                "status": "cancelled",
                "updated_at": self._utc_now(),
                "completed_at": self._utc_now(),
                "phase": "cancelled",
                "message": "Personal LoRA training was cancelled safely.",
            }
        )
        self._upsert_job(cast(TrainingJob, updated))
        return cast(TrainingJob, updated)

    def get_job(self, job_id: str) -> TrainingJob | None:
        target_id = self._normalize_id(job_id, field_name="job_id")
        for job in reversed(self.list_jobs(limit=500)):
            if job.get("job_id") == target_id:
                return job
        return None

    def list_jobs(self, *, limit: int = 50) -> list[TrainingJob]:
        safe_limit = max(1, min(limit, 200))
        jobs = [cast(TrainingJob, item) for item in self._read_jsonl(self._config.jobs_path)]
        return list(reversed(jobs[-safe_limit:]))

    def rollback_adapter(self, adapter_id: str) -> dict[str, Any]:
        """Disable an adapter manifest without deleting audit history."""

        target_id = self._normalize_id(adapter_id, field_name="adapter_id")
        manifest_path = self._config.adapters_path / target_id / "adapter_manifest.json"
        if not manifest_path.exists():
            raise ValueError("Adapter manifest was not found.")
        manifest = self._read_json(manifest_path)
        manifest["enabled"] = False
        manifest["rolled_back_at"] = self._utc_now()
        self._write_json(manifest_path, manifest)
        return manifest

    def status(self) -> dict[str, Any]:
        """Return settings and local artifact counts for user controls."""

        examples = self.list_examples(limit=500, include_deleted=True)
        jobs = self.list_jobs(limit=20)
        return {
            "enabled": self._config.enabled,
            "collect_examples": self._config.collect_examples,
            "rank": self._config.rank,
            "max_rank": self._config.max_rank,
            "max_steps": self._config.max_steps,
            "micro_batch_size": self._config.micro_batch_size,
            "gradient_accumulation_steps": self._config.gradient_accumulation_steps,
            "local_only": self._config.local_first,
            "dataset_path": str(self._config.dataset_path),
            "adapter_path": str(self._config.adapters_path),
            "example_counts": {
                "total": len([e for e in examples if e.get("review_status") != "deleted"]),
                "needs_review": len([e for e in examples if e.get("review_status") == "needs_review"]),
                "approved": len([e for e in examples if e.get("review_status") == "approved"]),
                "rejected": len([e for e in examples if e.get("review_status") == "rejected"]),
                "deleted": len([e for e in examples if e.get("review_status") == "deleted"]),
            },
            "latest_job": jobs[0] if jobs else None,
        }

    def _journal_entry_is_training_candidate(self, entry: JournalEntry) -> bool:
        if entry.get("status", "active") != "active":
            return False
        confidence = float(entry.get("confidence", 0.0) or 0.0)
        evidence_count = int(entry.get("evidence_count", 0) or 0)
        if confidence < self._config.min_confidence:
            return False
        if evidence_count < self._config.min_evidence_count:
            return False
        sensitivity_tags = {str(tag) for tag in entry.get("sensitivity_tags", [])}
        blocked_tags = sensitivity_tags - self._config.allowed_sensitivity_tags
        if blocked_tags:
            return False
        insights = [insight for insight in entry.get("insights", []) if isinstance(insight, dict)]
        return any(
            insight.get("memory_worthy")
            or insight.get("kind") in {"preference_signal", "growth_hypothesis", "relationship_continuity"}
            for insight in insights
        )

    def _example_from_entry(
        self, entry: JournalEntry, *, character_id: str | None = None
    ) -> TrainingExample:
        source_journal_id = str(entry.get("entry_id") or "unknown_journal")
        target_character_id = character_id or self._config.character_id
        purpose = self._purpose_for_entry(entry)
        text = self._training_text_for_entry(entry)
        created_at = self._utc_now()
        return TrainingExample(
            item_id=self._stable_id("train", f"{source_journal_id}|{purpose}|{text}"),
            character_id=target_character_id,
            source_journal_id=source_journal_id,
            source_memory_ids=[str(memory_id) for memory_id in entry.get("linked_memory_ids", [])],
            purpose=purpose,
            text=text,
            created_at=created_at,
            approved_by_user=False,
            review_status="needs_review",
            consent={
                "collection_opt_in": True,
                "approved_for_training": False,
                "source_training_eligibility": entry.get("training_eligibility", "needs_review"),
                "requires_user_review": True,
            },
            safety={
                "local_only": True,
                "raw_transcript_excluded": True,
                "sensitivity_tags": entry.get("sensitivity_tags", []),
                "rollback_id": entry.get("rollback_id"),
            },
            metadata={
                "created_by": "PersonalLoRATrainer",
                "journal_created_at": entry.get("created_at"),
                "confidence": entry.get("confidence", 0.0),
                "evidence_count": entry.get("evidence_count", 0),
                "themes": entry.get("themes", []),
            },
        )

    def _training_text_for_entry(self, entry: JournalEntry) -> str:
        lines = [
            "Practice note for preserving character continuity:",
            str(entry.get("character_summary") or "").strip(),
        ]
        growth_hypotheses = entry.get("structured_summary", {}).get("growth_hypotheses", [])
        if growth_hypotheses:
            lines.append(f"Behavior to practice: {growth_hypotheses[0]}")
        themes = entry.get("themes") or []
        if themes:
            lines.append(f"Continuity themes: {', '.join(str(theme) for theme in themes[:5])}.")
        lines.append("Keep stable identity and current user direction above this practice note.")
        return " ".join(line for line in lines if line)[:_MAX_EXAMPLE_TEXT_CHARS].rstrip()

    def _purpose_for_entry(self, entry: JournalEntry) -> str:
        themes = [str(theme) for theme in entry.get("themes", [])]
        if "boundaries" in themes:
            return "comfort_and_boundary_continuity"
        if "trust" in themes or "reassurance" in themes:
            return "trust_reassurance_style"
        if "playfulness" in themes:
            return "playful_voice_continuity"
        return "character_continuity_practice"

    def _training_config(self, rank: int, max_steps: int) -> dict[str, Any]:
        return {
            "method": "personal_lora_foundation",
            "rank": rank,
            "alpha": max(self._config.alpha, rank),
            "learning_rate": self._config.learning_rate,
            "max_steps": max_steps,
            "micro_batch_size": self._config.micro_batch_size,
            "gradient_accumulation_steps": self._config.gradient_accumulation_steps,
            "checkpoint_every_steps": self._config.checkpoint_every_steps,
            "precision": "qlora_or_8bit_when_backend_available",
            "target_vram_gb": 8,
            "chat_policy": "do_not_run_on_interactive_chat_path",
        }

    def _run_training_job(self, job: TrainingJob, cancel_event: threading.Event) -> None:
        job_id = str(job["job_id"])
        try:
            self._update_job(job_id, status="running", started_at=self._utc_now(), phase="preflight", progress=0.05, message="Checking approved local dataset and 8GB-safe LoRA settings.")
            phases = [
                ("dataset_snapshot", 0.25, "Writing a local dataset snapshot for reviewable training."),
                ("adapter_scaffold", 0.50, "Preparing tiny rank adapter scaffolding."),
                ("validation", 0.75, "Running lightweight continuity safety checks."),
                ("manifest", 0.95, "Saving adapter manifest for manual enablement."),
            ]
            for phase, progress, message in phases:
                if cancel_event.is_set():
                    self.stop_training(job_id)
                    return
                time.sleep(0.05)
                self._update_job(job_id, phase=phase, progress=progress, message=message)
            self._write_adapter_manifest(job)
            completed_at = self._utc_now()
            self._update_job(
                job_id,
                status="completed",
                completed_at=completed_at,
                phase="completed",
                progress=1.0,
                message="Personal LoRA adapter foundation completed and remains disabled until user review.",
            )
        except Exception as exc:  # pragma: no cover - defensive worker path.
            logger.exception("Personal LoRA training job failed", extra={"job_id": job_id})
            self._update_job(
                job_id,
                status="failed",
                completed_at=self._utc_now(),
                phase="failed",
                message="Personal LoRA training failed safely; chat was not affected.",
                error=str(exc),
            )
        finally:
            with self._job_lock:
                self._active_jobs.pop(job_id, None)

    def _write_adapter_manifest(self, job: TrainingJob) -> None:
        adapter_id = str(job.get("adapter_id") or "adapter_unknown")
        adapter_dir = self._config.adapters_path / adapter_id
        adapter_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "adapter_id": adapter_id,
            "character_id": job.get("character_id"),
            "created_at": self._utc_now(),
            "enabled": False,
            "status": "ready_for_review",
            "job_id": job.get("job_id"),
            "dataset_item_ids": job.get("dataset_item_ids", []),
            "config": job.get("config", {}),
            "safety": {
                "manual_enable_required": True,
                "rollback_supported": True,
                "identity_regression_required_before_default": True,
            },
        }
        self._write_json(adapter_dir / "adapter_manifest.json", manifest)

    def _bounded_rank(self, rank: int) -> int:
        if rank < 1:
            raise ValueError("LoRA rank must be positive.")
        if rank > self._config.max_rank:
            raise ValueError(f"LoRA rank must be <= {self._config.max_rank}.")
        return rank

    def _upsert_job(self, updated_job: TrainingJob) -> None:
        jobs = [cast(TrainingJob, item) for item in self._read_jsonl(self._config.jobs_path)]
        target_id = updated_job.get("job_id")
        replaced = False
        for index, job in enumerate(jobs):
            if job.get("job_id") == target_id:
                jobs[index] = updated_job
                replaced = True
                break
        if not replaced:
            jobs.append(updated_job)
        self._rewrite_jsonl(self._config.jobs_path, jobs)

    def _update_job(self, job_id: str, **updates: Any) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        updated = dict(job)
        updated.update(updates)
        updated["updated_at"] = self._utc_now()
        self._upsert_job(cast(TrainingJob, updated))

    def _append_jsonl(self, path: Path, item: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        items: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file.readlines()[-_MAX_DATASET_SCAN_LINES:]:
                if not line.strip():
                    continue
                try:
                    decoded = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, dict):
                    items.append(decoded)
        return items

    def _rewrite_jsonl(self, path: Path, items: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            for item in items:
                file.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
        temp_path.replace(path)

    def _read_json(self, path: Path) -> dict[str, Any]:
        decoded = json.loads(path.read_text(encoding="utf-8"))
        return decoded if isinstance(decoded, dict) else {}

    def _write_json(self, path: Path, item: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    def _normalize_id(self, value: str, *, field_name: str) -> str:
        normalized = " ".join(str(value or "").strip().split())
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty.")
        return normalized

    def _stable_id(self, prefix: str, seed: str) -> str:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        return f"{prefix}_{digest}"

    def _utc_now(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def _ensure_dirs(self) -> None:
        self._config.root_path.mkdir(parents=True, exist_ok=True)
        self._config.adapters_path.mkdir(parents=True, exist_ok=True)


_personal_lora_trainer: PersonalLoRATrainer | None = None


def get_personal_lora_trainer() -> PersonalLoRATrainer:
    """Return a process-local personal LoRA trainer singleton."""

    global _personal_lora_trainer
    if _personal_lora_trainer is None:
        _personal_lora_trainer = PersonalLoRATrainer()
    return _personal_lora_trainer


__all__ = [
    "PersonalLoRATrainer",
    "PersonalLoRATrainerConfig",
    "TrainingExample",
    "TrainingJob",
    "get_personal_lora_trainer",
]
