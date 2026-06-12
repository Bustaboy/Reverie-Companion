"""Personal LoRA training foundation for local-first character growth.

This module deliberately implements the smallest safe backend substrate for
future personal adapters: local JSON persistence, explicit opt-in, review gates,
and a cancellable low-priority background job.  It does not perform heavyweight
fine-tuning yet; instead it prepares auditable dataset records and records a
training plan that a later trainer backend can execute without changing the
control surface.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict, cast
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.core.reflection import JournalEntry

logger = logging.getLogger(__name__)

LoRAExampleStatus = Literal["pending_review", "approved", "rejected", "deleted"]
LoRATrainingStatus = Literal[
    "idle", "queued", "running", "cancelled", "completed", "failed"
]


class PersonalLoRAError(Exception):
    """Raised when local personal LoRA persistence or controls fail."""


class PersonalLoRASettings(TypedDict, total=False):
    """Inspectable user controls for personal LoRA collection and training."""

    collection_opt_in: bool
    training_opt_in: bool
    rank: int
    max_steps: int
    learning_rate: float
    batch_size: int
    gradient_accumulation_steps: int
    max_sequence_length: int
    target_vram_gb: int
    pause_during_chat: bool
    require_review_before_training: bool
    active_adapter_id: str | None
    rollback_adapter_id: str | None
    updated_at: str


class LoRATrainingExample(TypedDict, total=False):
    """Reviewable local dataset item linked to reflection provenance."""

    item_id: str
    source_journal_id: str
    source_memory_ids: list[str]
    source_turn_indices: list[int]
    purpose: str
    text: str
    themes: list[str]
    confidence: float
    evidence_count: int
    approved_by_user: bool
    status: LoRAExampleStatus
    consent_flags: list[str]
    privacy_tags: list[str]
    sensitivity_tags: list[str]
    created_at: str
    updated_at: str
    rollback_id: str


class LoRATrainingJob(TypedDict, total=False):
    """Small background training-plan/job record."""

    job_id: str
    status: LoRATrainingStatus
    adapter_id: str | None
    started_at: str | None
    completed_at: str | None
    stopped_at: str | None
    example_count: int
    rank: int
    settings: dict[str, Any]
    progress: float
    message: str
    error: str | None


@dataclass(frozen=True)
class PersonalLoRATrainerConfig:
    """Conservative defaults for 8GB-friendly adapter preparation.

    Resource budget:
      feature: personal LoRA foundation
      interactive_required: false
      primary_gpu_models: []
      peak_vram_mb_estimate: 0 for this foundation; future trainer target <= 1800
      steady_vram_mb_estimate: 0 while idle
      cpu_ram_mb_estimate: <100 for JSONL/state work
      concurrency_limit: 1
      fallbacks: pending dataset remains usable if training is unavailable
      cleanup: stop event cancels background job before enabling adapters
    """

    root_path: Path
    default_rank: int = 8
    max_rank: int = 16
    min_confidence: float = 0.68
    min_evidence_count: int = 2
    max_example_chars: int = 1_600
    max_examples_per_job: int = 128
    dry_run_step_delay_seconds: float = 0.02

    @classmethod
    def from_settings(
        cls, settings: Settings | None = None
    ) -> "PersonalLoRATrainerConfig":
        settings = settings or get_settings()
        root = Path(settings.personal_lora_data_path).expanduser().resolve()
        return cls(
            root_path=root,
            default_rank=settings.personal_lora_rank,
            max_rank=settings.personal_lora_max_rank,
            min_confidence=settings.personal_lora_min_confidence,
            min_evidence_count=settings.personal_lora_min_evidence_count,
            max_example_chars=settings.personal_lora_max_example_chars,
            max_examples_per_job=settings.personal_lora_max_examples_per_job,
        )


class PersonalLoRATrainer:
    """Local, opt-in personal adapter dataset and job controller.

    The class is intentionally backend-only and lightweight. It can collect
    high-quality reflection/journal artifacts as pending examples, approve or
    reject them, and run a cancellable background training placeholder that
    serializes an adapter manifest. Future PEFT/QLoRA execution can replace the
    dry-run worker while preserving opt-in, review, rollback, and status APIs.
    """

    def __init__(self, config: PersonalLoRATrainerConfig | None = None) -> None:
        self._config = config or PersonalLoRATrainerConfig.from_settings()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._ensure_dirs()

    @property
    def settings_path(self) -> Path:
        return self._config.root_path / "settings.json"

    @property
    def examples_path(self) -> Path:
        return self._config.root_path / "training_examples.jsonl"

    @property
    def jobs_path(self) -> Path:
        return self._config.root_path / "jobs.jsonl"

    @property
    def adapters_path(self) -> Path:
        return self._config.root_path / "adapters"

    def get_settings(self) -> PersonalLoRASettings:
        """Return current user controls, creating safe defaults if absent."""

        with self._lock:
            if not self.settings_path.exists():
                settings = self._default_settings()
                self._write_json(self.settings_path, settings)
                return settings
            try:
                decoded = json.loads(self.settings_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PersonalLoRAError(
                    "Unable to read personal LoRA settings."
                ) from exc
            return self._normalize_settings(decoded)

    def update_settings(self, updates: dict[str, Any]) -> PersonalLoRASettings:
        """Update opt-in and conservative training controls."""

        allowed = {
            "collection_opt_in",
            "training_opt_in",
            "rank",
            "max_steps",
            "learning_rate",
            "batch_size",
            "gradient_accumulation_steps",
            "max_sequence_length",
            "pause_during_chat",
            "require_review_before_training",
            "active_adapter_id",
            "rollback_adapter_id",
        }
        with self._lock:
            settings = dict(self.get_settings())
            for key, value in updates.items():
                if key not in allowed:
                    continue
                settings[key] = value
            settings = self._normalize_settings(settings)
            settings["updated_at"] = self._utc_now()
            self._write_json(self.settings_path, settings)
            return settings

    def collect_from_journal_entry(
        self, entry: JournalEntry | dict[str, Any], *, approved_by_user: bool = False
    ) -> LoRATrainingExample | None:
        """Create a pending/approved training example from a high-quality entry.

        Collection is gated by user opt-in and by quality/safety checks. Automatic
        collection creates reviewable pending examples only; examples are not used
        for training until approved unless the caller passes an explicit approval
        flag from a future review UI or API.
        """

        settings = self.get_settings()
        if not settings.get("collection_opt_in", False):
            return None
        if not self._entry_is_collectable(entry):
            return None

        text = self._training_text_for_entry(entry)
        if not text:
            return None

        item_id = self._example_id(entry, text)
        existing = self.get_example(item_id)
        if existing is not None:
            return existing

        now = self._utc_now()
        status: LoRAExampleStatus = "approved" if approved_by_user else "pending_review"
        example = LoRATrainingExample(
            item_id=item_id,
            source_journal_id=str(entry.get("entry_id") or ""),
            source_memory_ids=[
                str(value) for value in entry.get("linked_memory_ids", [])
            ],
            source_turn_indices=self._source_turn_indices(entry),
            purpose=self._purpose_for_entry(entry),
            text=text[: self._config.max_example_chars].rstrip(),
            themes=[str(theme) for theme in entry.get("themes", [])[:5]],
            confidence=float(entry.get("confidence", 0.0) or 0.0),
            evidence_count=int(entry.get("evidence_count", 0) or 0),
            approved_by_user=approved_by_user,
            status=status,
            consent_flags=["user_opted_in_to_collection"],
            privacy_tags=[str(tag) for tag in entry.get("privacy_tags", [])],
            sensitivity_tags=[str(tag) for tag in entry.get("sensitivity_tags", [])],
            created_at=now,
            updated_at=now,
            rollback_id=str(entry.get("rollback_id") or f"rollback_{item_id}"),
        )
        with self._lock:
            self._append_jsonl(self.examples_path, example)
        logger.info(
            "Collected personal LoRA training candidate",
            extra={
                "item_id": item_id,
                "status": status,
                "source_journal_id": example["source_journal_id"],
            },
        )
        return example

    def approve_example(self, item_id: str) -> LoRATrainingExample:
        """Mark a pending example as user-approved for future training."""

        return self._update_example_status(item_id, "approved", approved_by_user=True)

    def reject_example(self, item_id: str) -> LoRATrainingExample:
        """Reject an example so it is excluded from adapter jobs."""

        return self._update_example_status(item_id, "rejected", approved_by_user=False)

    def delete_example(self, item_id: str) -> LoRATrainingExample:
        """Tombstone an example for rollback/deletion without rewriting provenance."""

        return self._update_example_status(item_id, "deleted", approved_by_user=False)

    def list_examples(
        self, *, include_deleted: bool = False
    ) -> list[LoRATrainingExample]:
        """Return local dataset examples newest first."""

        examples = self._read_examples()
        if not include_deleted:
            examples = [
                example for example in examples if example.get("status") != "deleted"
            ]
        return list(reversed(examples))

    def get_example(self, item_id: str) -> LoRATrainingExample | None:
        for example in reversed(self._read_examples()):
            if example.get("item_id") == item_id:
                return example
        return None

    def start_training(self) -> LoRATrainingJob:
        """Start a single low-priority personal LoRA job if controls allow it."""

        settings = self.get_settings()
        if not settings.get("training_opt_in", False):
            raise PersonalLoRAError("Personal LoRA training requires explicit opt-in.")
        examples = [
            example
            for example in self._read_examples()
            if example.get("status") == "approved"
            and example.get("approved_by_user") is True
        ][-self._config.max_examples_per_job :]
        if not examples:
            raise PersonalLoRAError("No approved personal LoRA examples are available.")

        with self._lock:
            current = self.get_current_job()
            if current and current.get("status") in {"queued", "running"}:
                return current
            self._stop_event.clear()
            job = LoRATrainingJob(
                job_id=f"lora_job_{uuid4().hex[:12]}",
                status="queued",
                adapter_id=None,
                started_at=None,
                completed_at=None,
                stopped_at=None,
                example_count=len(examples),
                rank=int(settings.get("rank", self._config.default_rank)),
                settings={
                    "rank": settings.get("rank"),
                    "max_steps": settings.get("max_steps"),
                    "learning_rate": settings.get("learning_rate"),
                    "batch_size": settings.get("batch_size"),
                    "gradient_accumulation_steps": settings.get(
                        "gradient_accumulation_steps"
                    ),
                    "max_sequence_length": settings.get("max_sequence_length"),
                    "target_vram_gb": settings.get("target_vram_gb"),
                    "pause_during_chat": settings.get("pause_during_chat"),
                    "backend": "foundation_dry_run",
                },
                progress=0.0,
                message="Queued personal LoRA training in safe foundation mode.",
                error=None,
            )
            self._append_job(job)
            self._worker = threading.Thread(
                target=self._run_training_job,
                args=(job, examples),
                name="personal-lora-trainer",
                daemon=True,
            )
            self._worker.start()
            return job

    def stop_training(self) -> LoRATrainingJob | None:
        """Request cancellation of the active background training job."""

        self._stop_event.set()
        worker = self._worker
        if worker and worker.is_alive():
            worker.join(timeout=1.0)
        return self.get_current_job()

    def get_current_job(self) -> LoRATrainingJob | None:
        jobs = self._read_jobs()
        return jobs[-1] if jobs else None

    def _run_training_job(
        self, job: LoRATrainingJob, examples: list[LoRATrainingExample]
    ) -> None:
        job = dict(job)
        job["status"] = "running"
        job["started_at"] = self._utc_now()
        job["message"] = (
            "Preparing a conservative rank-"
            f"{job.get('rank')} personal LoRA manifest without blocking chat."
        )
        self._append_job(cast(LoRATrainingJob, job))
        steps = max(1, min(int(job.get("settings", {}).get("max_steps", 80)), 120))
        try:
            for step in range(steps):
                if self._stop_event.is_set():
                    job["status"] = "cancelled"
                    job["stopped_at"] = self._utc_now()
                    job["progress"] = round(step / steps, 3)
                    job["message"] = "Personal LoRA training was cancelled safely."
                    self._append_job(cast(LoRATrainingJob, job))
                    return
                time.sleep(self._config.dry_run_step_delay_seconds)
                if step % 10 == 0 or step == steps - 1:
                    job["progress"] = round((step + 1) / steps, 3)
                    self._append_job(cast(LoRATrainingJob, job))

            adapter_id = f"personal_lora_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            manifest = {
                "adapter_id": adapter_id,
                "created_at": self._utc_now(),
                "status": "ready_for_future_trainer",
                "rank": job.get("rank"),
                "example_count": len(examples),
                "source_example_ids": [example.get("item_id") for example in examples],
                "safety": {
                    "requires_user_enable": True,
                    "rollback_supported": True,
                    "identity_regression_required_before_default_enable": True,
                },
                "settings": job.get("settings", {}),
            }
            adapter_dir = self.adapters_path / adapter_id
            adapter_dir.mkdir(parents=True, exist_ok=True)
            self._write_json(adapter_dir / "manifest.json", manifest)
            job["status"] = "completed"
            job["adapter_id"] = adapter_id
            job["completed_at"] = self._utc_now()
            job["progress"] = 1.0
            job["message"] = (
                "Personal LoRA foundation job completed; adapter manifest is ready for review."
            )
            self._append_job(cast(LoRATrainingJob, job))
        except Exception as exc:  # pragma: no cover - defensive background safety.
            job["status"] = "failed"
            job["error"] = str(exc)
            job["message"] = "Personal LoRA training foundation job failed safely."
            self._append_job(cast(LoRATrainingJob, job))
            logger.warning(
                "Personal LoRA job failed",
                extra={"error": str(exc), "job_id": job.get("job_id")},
            )

    def _entry_is_collectable(self, entry: JournalEntry | dict[str, Any]) -> bool:
        if entry.get("status", "active") != "active":
            return False
        if float(entry.get("confidence", 0.0) or 0.0) < self._config.min_confidence:
            return False
        if int(entry.get("evidence_count", 0) or 0) < self._config.min_evidence_count:
            return False
        sensitivity_tags = set(str(tag) for tag in entry.get("sensitivity_tags", []))
        if (
            "high_sensitivity" in sensitivity_tags
            or "intimate_content" in sensitivity_tags
        ):
            return False
        insights = entry.get("insights") or []
        return any(
            isinstance(insight, dict)
            and (
                insight.get("memory_worthy")
                or insight.get("kind")
                in {"preference_signal", "growth_hypothesis", "relationship_continuity"}
            )
            for insight in insights
        )

    def _training_text_for_entry(self, entry: JournalEntry | dict[str, Any]) -> str:
        parts = [str(entry.get("character_summary") or "").strip()]
        for insight in entry.get("insights", [])[:3]:
            if isinstance(insight, dict) and str(insight.get("summary") or "").strip():
                parts.append(f"Practice note: {insight['summary']}")
        themes = [str(theme) for theme in entry.get("themes", [])[:5]]
        if themes:
            parts.append(f"Continuity themes: {', '.join(themes)}")
        text = "\n".join(part for part in parts if part).strip()
        return text[: self._config.max_example_chars].rstrip()

    def _purpose_for_entry(self, entry: JournalEntry | dict[str, Any]) -> str:
        themes = set(str(theme) for theme in entry.get("themes", []))
        if "boundaries" in themes:
            return "comfort_and_boundary_continuity"
        if "trust" in themes or "reassurance" in themes:
            return "trust_and_reassurance_style"
        if "playfulness" in themes:
            return "playful_voice_continuity"
        return "character_continuity_practice"

    def _source_turn_indices(self, entry: JournalEntry | dict[str, Any]) -> list[int]:
        indices: set[int] = set()
        for insight in entry.get("insights", []):
            if not isinstance(insight, dict):
                continue
            for index in insight.get("source_turn_indices", []):
                if isinstance(index, int):
                    indices.add(index)
        return sorted(indices)

    def _example_id(self, entry: JournalEntry | dict[str, Any], text: str) -> str:
        import hashlib

        seed = f"{entry.get('entry_id')}|{text}"
        return f"train_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:24]}"

    def _update_example_status(
        self, item_id: str, status: LoRAExampleStatus, *, approved_by_user: bool
    ) -> LoRATrainingExample:
        with self._lock:
            examples = self._read_examples()
            updated: LoRATrainingExample | None = None
            rewritten: list[LoRATrainingExample] = []
            for example in examples:
                if example.get("item_id") == item_id:
                    example = dict(example)
                    example["status"] = status
                    example["approved_by_user"] = approved_by_user
                    example["updated_at"] = self._utc_now()
                    updated = cast(LoRATrainingExample, example)
                rewritten.append(example)
            if updated is None:
                raise PersonalLoRAError(f"Training example {item_id} was not found.")
            self._rewrite_jsonl(self.examples_path, rewritten)
            return updated

    def _normalize_settings(self, raw: dict[str, Any]) -> PersonalLoRASettings:
        settings = dict(self._default_settings())
        settings.update(raw)
        rank = int(settings.get("rank", self._config.default_rank))
        settings["rank"] = max(8, min(rank, self._config.max_rank))
        settings["max_steps"] = max(10, min(int(settings.get("max_steps", 80)), 120))
        settings["learning_rate"] = max(
            0.00001, min(float(settings.get("learning_rate", 0.0001)), 0.0002)
        )
        settings["batch_size"] = 1
        settings["gradient_accumulation_steps"] = max(
            4, min(int(settings.get("gradient_accumulation_steps", 8)), 16)
        )
        settings["max_sequence_length"] = max(
            256, min(int(settings.get("max_sequence_length", 768)), 1024)
        )
        settings["target_vram_gb"] = 8
        settings["collection_opt_in"] = bool(settings.get("collection_opt_in", False))
        settings["training_opt_in"] = bool(settings.get("training_opt_in", False))
        settings["pause_during_chat"] = bool(settings.get("pause_during_chat", True))
        settings["require_review_before_training"] = bool(
            settings.get("require_review_before_training", True)
        )
        settings.setdefault("active_adapter_id", None)
        settings.setdefault("rollback_adapter_id", None)
        settings.setdefault("updated_at", self._utc_now())
        return cast(PersonalLoRASettings, settings)

    def _default_settings(self) -> PersonalLoRASettings:
        return PersonalLoRASettings(
            collection_opt_in=False,
            training_opt_in=False,
            rank=self._config.default_rank,
            max_steps=80,
            learning_rate=0.0001,
            batch_size=1,
            gradient_accumulation_steps=8,
            max_sequence_length=768,
            target_vram_gb=8,
            pause_during_chat=True,
            require_review_before_training=True,
            active_adapter_id=None,
            rollback_adapter_id=None,
            updated_at=self._utc_now(),
        )

    def _read_examples(self) -> list[LoRATrainingExample]:
        return [
            cast(LoRATrainingExample, item)
            for item in self._read_jsonl(self.examples_path)
        ]

    def _read_jobs(self) -> list[LoRATrainingJob]:
        return [
            cast(LoRATrainingJob, item) for item in self._read_jsonl(self.jobs_path)
        ]

    def _append_job(self, job: LoRATrainingJob) -> None:
        with self._lock:
            self._append_jsonl(self.jobs_path, job)

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as file:
                for line in file:
                    if not line.strip():
                        continue
                    decoded = json.loads(line)
                    if isinstance(decoded, dict):
                        rows.append(decoded)
        except (OSError, json.JSONDecodeError) as exc:
            raise PersonalLoRAError(f"Unable to read {path.name}.") from exc
        return rows

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        self._ensure_dirs()
        try:
            with path.open("a", encoding="utf-8") as file:
                file.write(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
                )
        except OSError as exc:
            raise PersonalLoRAError(f"Unable to write {path.name}.") from exc

    def _rewrite_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        self._ensure_dirs()
        temp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as file:
                for row in rows:
                    file.write(
                        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                    )
            temp_path.replace(path)
        except OSError as exc:
            raise PersonalLoRAError(f"Unable to rewrite {path.name}.") from exc

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        self._ensure_dirs()
        try:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError as exc:
            raise PersonalLoRAError(f"Unable to write {path.name}.") from exc

    def _ensure_dirs(self) -> None:
        self._config.root_path.mkdir(parents=True, exist_ok=True)
        self.adapters_path.mkdir(parents=True, exist_ok=True)

    def _utc_now(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")


_personal_lora_trainer: PersonalLoRATrainer | None = None


def get_personal_lora_trainer() -> PersonalLoRATrainer:
    """Return process-local personal LoRA trainer singleton."""

    global _personal_lora_trainer
    if _personal_lora_trainer is None:
        _personal_lora_trainer = PersonalLoRATrainer()
    return _personal_lora_trainer


__all__ = [
    "LoRATrainingExample",
    "LoRATrainingJob",
    "PersonalLoRAError",
    "PersonalLoRASettings",
    "PersonalLoRATrainer",
    "PersonalLoRATrainerConfig",
    "get_personal_lora_trainer",
]
