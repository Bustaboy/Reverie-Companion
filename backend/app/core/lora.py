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
from dataclasses import dataclass, field
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
LoRAApplyStatus = Literal["not_ready", "pending_apply", "applied", "rejected"]


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
    require_approval_before_applying: bool
    auto_training_enabled: bool
    training_frequency_hours: int
    min_training_examples: int
    min_new_examples_for_auto_training: int
    min_memory_links_for_auto_training: int
    max_auto_jobs_per_day: int
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
    trigger_reason: str | None
    trigger_summary: str | None
    trigger_example_ids: list[str]
    learning_summary: list[str]
    apply_status: LoRAApplyStatus


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
    min_auto_training_examples: int = 3

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
            "require_approval_before_applying",
            "auto_training_enabled",
            "training_frequency_hours",
            "min_training_examples",
            "min_new_examples_for_auto_training",
            "min_memory_links_for_auto_training",
            "max_auto_jobs_per_day",
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

    def start_training(
        self,
        *,
        trigger_reason: str = "manual",
        trigger_summary: str | None = None,
    ) -> LoRATrainingJob:
        """Start a single low-priority personal LoRA job if controls allow it."""

        settings = self.get_settings()
        if not settings.get("training_opt_in", False):
            raise PersonalLoRAError("Personal LoRA training requires explicit opt-in.")
        examples = self._approved_training_examples(settings)
        if len(examples) < int(settings.get("min_training_examples", 1)):
            raise PersonalLoRAError(
                "Not enough approved personal LoRA examples are available."
            )

        with self._lock:
            current = self.get_current_job()
            if current and current.get("status") in {"queued", "running"}:
                return current
            self._stop_event.clear()
            selected_examples = examples[-self._config.max_examples_per_job :]
            learning_summary = self._learning_summary_for_examples(selected_examples)
            job = LoRATrainingJob(
                job_id=f"lora_job_{uuid4().hex[:12]}",
                status="queued",
                adapter_id=None,
                started_at=None,
                completed_at=None,
                stopped_at=None,
                example_count=len(selected_examples),
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
                    "backend": "unsloth_qlora_foundation_dry_run",
                    "training_frequency_hours": settings.get("training_frequency_hours"),
                    "require_approval_before_applying": settings.get(
                        "require_approval_before_applying"
                    ),
                },
                progress=0.0,
                message="Queued lightweight Unsloth QLoRA training in safe foundation mode.",
                error=None,
                trigger_reason=trigger_reason,
                trigger_summary=trigger_summary
                or self._trigger_summary_for_examples(selected_examples),
                trigger_example_ids=[
                    str(example.get("item_id")) for example in selected_examples
                ],
                learning_summary=learning_summary,
                apply_status="not_ready",
            )
            self._append_job(job)
            self._worker = threading.Thread(
                target=self._run_training_job,
                args=(job, selected_examples),
                name="personal-lora-trainer",
                daemon=True,
            )
            self._worker.start()
            return job

    def evaluate_auto_training(
        self, *, trigger_reason: str = "auto_growth_threshold"
    ) -> LoRATrainingJob | None:
        """Start automated training when opt-in settings and data thresholds allow it."""

        settings = self.get_settings()
        if not (
            settings.get("collection_opt_in", False)
            and settings.get("training_opt_in", False)
            and settings.get("auto_training_enabled", False)
        ):
            return None
        current = self.get_current_job()
        if current and current.get("status") in {"queued", "running"}:
            return current
        examples = self._approved_training_examples(settings)
        if len(examples) < int(settings.get("min_training_examples", 1)):
            return None
        last_completed = self._latest_completed_job()
        if last_completed is not None:
            if not self._frequency_elapsed(last_completed, settings):
                return None
            new_examples = self._examples_after_completed_job(examples, last_completed)
        else:
            new_examples = examples
        if len(new_examples) < int(
            settings.get("min_new_examples_for_auto_training", 1)
        ):
            return None
        memory_links = {
            memory_id
            for example in new_examples
            for memory_id in example.get("source_memory_ids", [])
        }
        if len(memory_links) < int(
            settings.get("min_memory_links_for_auto_training", 0)
        ):
            return None
        if self._auto_jobs_started_today() >= int(
            settings.get("max_auto_jobs_per_day", 1)
        ):
            return None
        return self.start_training(
            trigger_reason=trigger_reason,
            trigger_summary=self._trigger_summary_for_examples(new_examples),
        )

    def get_training_status(self) -> dict[str, Any]:
        """Return dashboard-friendly automated training and approval state."""

        settings = self.get_settings()
        jobs = self._read_jobs()
        current = jobs[-1] if jobs else None
        completed = next(
            (job for job in reversed(jobs) if job.get("status") == "completed"), None
        )
        examples = self._read_examples()
        approved_examples = self._approved_training_examples(settings)
        pending_adapter = self._pending_adapter_job(jobs)
        return {
            "status": current.get("status") if current else "idle",
            "message": (current or {}).get("message") or "LoRA training is idle.",
            "last_trained_at": (completed or {}).get("completed_at"),
            "next_scheduled_at": self._next_scheduled_at(
                completed, settings, approved_examples
            ),
            "triggered_by": (current or completed or {}).get("trigger_summary"),
            "trigger_reason": (current or completed or {}).get("trigger_reason"),
            "learning_feedback": (current or completed or {}).get(
                "learning_summary", []
            ),
            "auto_training_enabled": settings.get("auto_training_enabled", False),
            "require_approval_before_applying": settings.get(
                "require_approval_before_applying", True
            ),
            "min_training_examples": settings.get("min_training_examples"),
            "training_frequency_hours": settings.get("training_frequency_hours"),
            "approved_example_count": len(approved_examples),
            "pending_review_count": sum(
                1 for example in examples if example.get("status") == "pending_review"
            ),
            "pending_adapter_update": pending_adapter,
        }

    def approve_adapter_update(self, adapter_id: str) -> LoRATrainingJob:
        """Apply a completed adapter manifest after user approval."""

        return self._set_adapter_apply_status(adapter_id, "applied")

    def reject_adapter_update(self, adapter_id: str) -> LoRATrainingJob:
        """Reject a completed adapter manifest without deleting rollback history."""

        return self._set_adapter_apply_status(adapter_id, "rejected")

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
                    "requires_user_enable": bool(
                        job.get("settings", {}).get(
                            "require_approval_before_applying", True
                        )
                    ),
                    "rollback_supported": True,
                    "identity_regression_required_before_default_enable": True,
                    "qlora_profile": "Unsloth 4-bit QLoRA, rank <= 16, batch size 1",
                },
                "trigger_summary": job.get("trigger_summary"),
                "learning_summary": job.get("learning_summary", []),
                "settings": job.get("settings", {}),
            }
            adapter_dir = self.adapters_path / adapter_id
            adapter_dir.mkdir(parents=True, exist_ok=True)
            self._write_json(adapter_dir / "manifest.json", manifest)
            job["status"] = "completed"
            job["adapter_id"] = adapter_id
            job["completed_at"] = self._utc_now()
            job["progress"] = 1.0
            if job.get("settings", {}).get("require_approval_before_applying", True):
                job["apply_status"] = "pending_apply"
                job["message"] = (
                    "Personal LoRA job completed; the adapter is waiting for approval before applying."
                )
            else:
                job["apply_status"] = "applied"
                self.update_settings({"active_adapter_id": adapter_id})
                job["message"] = (
                    "Personal LoRA job completed and the new local adapter was applied automatically."
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


    def _approved_training_examples(
        self, settings: PersonalLoRASettings | None = None
    ) -> list[LoRATrainingExample]:
        settings = settings or self.get_settings()
        require_review = bool(settings.get("require_review_before_training", True))
        examples = []
        for example in self._read_examples():
            if example.get("status") != "approved":
                continue
            if require_review and example.get("approved_by_user") is not True:
                continue
            examples.append(example)
        return examples[-self._config.max_examples_per_job :]

    def _latest_completed_job(self) -> LoRATrainingJob | None:
        return next(
            (
                job
                for job in reversed(self._read_jobs())
                if job.get("status") == "completed"
            ),
            None,
        )

    def _examples_after_completed_job(
        self, examples: list[LoRATrainingExample], job: LoRATrainingJob
    ) -> list[LoRATrainingExample]:
        completed_at = self._parse_time(job.get("completed_at"))
        if completed_at is None:
            return examples
        return [
            example
            for example in examples
            if (self._parse_time(example.get("created_at")) or completed_at) > completed_at
        ]

    def _frequency_elapsed(
        self, job: LoRATrainingJob, settings: PersonalLoRASettings
    ) -> bool:
        completed_at = self._parse_time(job.get("completed_at"))
        if completed_at is None:
            return True
        elapsed_hours = (datetime.now(UTC) - completed_at).total_seconds() / 3600
        return elapsed_hours >= int(settings.get("training_frequency_hours", 24))

    def _auto_jobs_started_today(self) -> int:
        today = datetime.now(UTC).date()
        count = 0
        for job in self._read_jobs():
            if job.get("trigger_reason") != "auto_growth_threshold":
                continue
            started_at = self._parse_time(job.get("started_at"))
            if started_at and started_at.date() == today:
                count += 1
        return count

    def _next_scheduled_at(
        self,
        completed: LoRATrainingJob | None,
        settings: PersonalLoRASettings,
        approved_examples: list[LoRATrainingExample],
    ) -> str | None:
        if not settings.get("auto_training_enabled", False):
            return None
        if not settings.get("training_opt_in", False):
            return None
        if len(approved_examples) < int(settings.get("min_training_examples", 1)):
            return None
        if completed is None:
            return self._utc_now()
        completed_at = self._parse_time(completed.get("completed_at"))
        if completed_at is None:
            return self._utc_now()
        frequency_seconds = int(settings.get("training_frequency_hours", 24)) * 3600
        return datetime.fromtimestamp(
            completed_at.timestamp() + frequency_seconds, UTC
        ).isoformat(timespec="seconds")

    def _pending_adapter_job(
        self, jobs: list[LoRATrainingJob]
    ) -> LoRATrainingJob | None:
        return next(
            (
                job
                for job in reversed(jobs)
                if job.get("status") == "completed"
                and job.get("adapter_id")
                and job.get("apply_status") == "pending_apply"
            ),
            None,
        )

    def _set_adapter_apply_status(
        self, adapter_id: str, apply_status: LoRAApplyStatus
    ) -> LoRATrainingJob:
        if apply_status not in {"applied", "rejected"}:
            raise PersonalLoRAError("Adapter update status is not supported.")
        with self._lock:
            jobs = self._read_jobs()
            target = next(
                (
                    dict(job)
                    for job in reversed(jobs)
                    if job.get("adapter_id") == adapter_id
                    and job.get("status") == "completed"
                ),
                None,
            )
            if target is None:
                raise PersonalLoRAError(f"Adapter update {adapter_id} was not found.")
            target["apply_status"] = apply_status
            target["message"] = (
                "Personal LoRA adapter was approved and applied."
                if apply_status == "applied"
                else "Personal LoRA adapter was rejected and kept out of use."
            )
            if apply_status == "applied":
                self.update_settings({"active_adapter_id": adapter_id})
            elif self.get_settings().get("active_adapter_id") == adapter_id:
                self.update_settings({"active_adapter_id": None})
            self._append_job(cast(LoRATrainingJob, target))
            return cast(LoRATrainingJob, target)

    def _trigger_summary_for_examples(
        self, examples: list[LoRATrainingExample]
    ) -> str:
        if not examples:
            return "No new growth data is ready."
        journal_count = len({example.get("source_journal_id") for example in examples})
        memory_count = len(
            {
                memory_id
                for example in examples
                for memory_id in example.get("source_memory_ids", [])
            }
        )
        themes = []
        for example in examples:
            for theme in example.get("themes", []):
                if theme not in themes:
                    themes.append(str(theme))
        theme_text = ", ".join(themes[:3]) or "continuity"
        return (
            f"{len(examples)} approved examples from {journal_count} reflections "
            f"and {memory_count} linked memories; strongest signals: {theme_text}."
        )

    def _learning_summary_for_examples(
        self, examples: list[LoRATrainingExample]
    ) -> list[str]:
        feedback: list[str] = []
        theme_labels = {
            "trust": "Stronger emotional memory recall around trust",
            "reassurance": "Improved reassurance tone toward the user",
            "affection": "Warmer affectionate continuity",
            "boundaries": "Better boundary and comfort pacing",
            "playfulness": "More consistent playful voice",
            "routine": "Better recall of shared routines",
            "curiosity": "More attentive curiosity about user preferences",
        }
        seen_themes: set[str] = set()
        for example in examples:
            for theme in example.get("themes", []):
                theme = str(theme)
                if theme in seen_themes:
                    continue
                seen_themes.add(theme)
                if theme in theme_labels:
                    feedback.append(theme_labels[theme])
        for example in examples:
            purpose = str(example.get("purpose") or "")
            if purpose == "trust_and_reassurance_style":
                feedback.append("Improved tone toward user during reassurance moments")
            elif purpose == "comfort_and_boundary_continuity":
                feedback.append("Stronger comfort and boundary recall")
            elif purpose == "playful_voice_continuity":
                feedback.append("More stable playful banter style")
            if len(feedback) >= 4:
                break
        deduped: list[str] = []
        for item in feedback or ["More consistent character continuity from approved reflections"]:
            if item not in deduped:
                deduped.append(item)
        return deduped[:4]

    def _parse_time(self, value: object) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

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
        settings["require_approval_before_applying"] = bool(
            settings.get("require_approval_before_applying", True)
        )
        settings["auto_training_enabled"] = bool(
            settings.get("auto_training_enabled", False)
        )
        settings["training_frequency_hours"] = max(
            6, min(int(settings.get("training_frequency_hours", 24)), 168)
        )
        settings["min_training_examples"] = max(
            1,
            min(
                int(
                    settings.get(
                        "min_training_examples",
                        self._config.min_auto_training_examples,
                    )
                ),
                256,
            ),
        )
        settings["min_new_examples_for_auto_training"] = max(
            1, min(int(settings.get("min_new_examples_for_auto_training", 2)), 64)
        )
        settings["min_memory_links_for_auto_training"] = max(
            0, min(int(settings.get("min_memory_links_for_auto_training", 1)), 64)
        )
        settings["max_auto_jobs_per_day"] = max(
            1, min(int(settings.get("max_auto_jobs_per_day", 1)), 3)
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
            require_approval_before_applying=True,
            auto_training_enabled=False,
            training_frequency_hours=24,
            min_training_examples=self._config.min_auto_training_examples,
            min_new_examples_for_auto_training=2,
            min_memory_links_for_auto_training=1,
            max_auto_jobs_per_day=1,
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
