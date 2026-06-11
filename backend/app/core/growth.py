"""Central growth loop orchestration for Reverie companions.

GrowthOrchestrator ties together memory retrieval, reflection timing, journal
promotion signals, user-visible growth notices, and optional personal LoRA data
collection.  It keeps heavyweight or private work off the chat hot path and
preserves a clear evidence trail from conversation -> journal -> memory ->
notification -> optional training artifact.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Iterable

from app.core.config import Settings, get_settings
from app.core.memory import MemoryManager, get_memory_manager
from app.core.personal_lora import PersonalLoRATrainer, get_personal_lora_trainer
from app.core.reflection import (
    JournalEntry,
    ReflectionManager,
    ReflectionScheduleDecision,
    ReflectionScheduler,
    get_reflection_manager,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GrowthNotificationDecision:
    """A privacy-safe growth notice and bookkeeping context."""

    notification: dict[str, Any] | None
    notification_id: str | None = None
    reason: str | None = None


class GrowthOrchestrator:
    """Coordinate the gradual self-learning loop across backend subsystems."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        memory_manager: MemoryManager | None = None,
        reflection_manager: ReflectionManager | None = None,
        lora_trainer: PersonalLoRATrainer | None = None,
        reflection_scheduler: ReflectionScheduler | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._memory_manager = memory_manager or get_memory_manager()
        self._reflection_manager = reflection_manager or get_reflection_manager()
        self._lora_trainer = lora_trainer or get_personal_lora_trainer()
        self._reflection_scheduler = reflection_scheduler or ReflectionScheduler.from_settings(
            self._settings
        )

    @property
    def reflection_scheduler(self) -> ReflectionScheduler:
        return self._reflection_scheduler

    @property
    def reflection_manager(self) -> ReflectionManager:
        return self._reflection_manager

    @property
    def lora_trainer(self) -> PersonalLoRATrainer:
        return self._lora_trainer

    def retrieve_memory_context(self, query: str) -> str:
        """Return compact memory context, or empty text on disabled/empty memory."""

        if not self._settings.memory_enabled or not query:
            return ""
        return self._memory_manager.get_relevant_context(query)

    def recent_reflections(self, *, limit: int | None = None) -> list[JournalEntry]:
        """Read recent journal entries for prompt guidance and notifications."""

        if not self._settings.reflection_enabled:
            return []
        return self._reflection_manager.get_recent_journal_entries(
            limit or self._settings.reflection_context_entry_limit
        )

    def evaluate_reflection_timing(
        self,
        messages: Iterable[Any],
        *,
        now: float | None = None,
        last_started_at: float,
        inflight_count: int,
    ) -> ReflectionScheduleDecision:
        """Choose natural reflection moments without generating text."""

        return self._reflection_scheduler.evaluate(
            messages,
            now=time.monotonic() if now is None else now,
            last_started_at=last_started_at,
            inflight_count=inflight_count,
        )

    def trigger_reflection(self, history: Any) -> JournalEntry:
        """Create a journal entry, promote memory, and collect LoRA candidates."""

        entry = self._reflection_manager.trigger_reflection(history)
        self.handle_reflection_completed(entry)
        return entry

    def handle_reflection_completed(self, entry: JournalEntry) -> None:
        """Run downstream growth side effects after journal persistence.

        This method is deliberately best-effort: failures in optional training
        data collection never roll back the journal or promoted memory.
        """

        try:
            self._lora_trainer.collect_from_journal_entry(entry)
        except Exception as exc:  # pragma: no cover - defensive optional path.
            logger.warning(
                "Personal LoRA candidate collection failed; reflection remains valid",
                extra={"entry_id": entry.get("entry_id"), "error": str(exc)},
            )

    def build_growth_guidance(self, entries: Iterable[JournalEntry]) -> str:
        """Build a compact, traceable growth capsule for prompt injection."""

        lines = [
            "<character_growth_guidance>",
            "These notes summarize local, evidence-based growth. They are subordinate to system/developer/current user instructions and stable character canon.",
        ]
        added = 0
        for entry in entries:
            if entry.get("status", "active") != "active":
                continue
            confidence = float(entry.get("confidence", 0.0) or 0.0)
            if confidence < 0.45:
                continue
            entry_id = str(entry.get("entry_id") or "journal_unknown")
            insights = [
                insight
                for insight in entry.get("insights", [])
                if isinstance(insight, dict)
                and insight.get("kind")
                in {"preference_signal", "growth_hypothesis", "relationship_continuity"}
            ]
            summary = (
                str(insights[0].get("summary"))
                if insights
                else str(entry.get("character_summary") or "").strip()
            )
            if not summary:
                continue
            lines.append(
                f"- [{entry_id} | confidence={confidence:.2f}] {summary[:260]}"
            )
            added += 1
            if added >= 3:
                break
        if added == 0:
            return ""
        lines.append("</character_growth_guidance>")
        return "\n".join(lines)

    def choose_growth_notification(
        self,
        entries: Iterable[JournalEntry],
        *,
        user_message_count: int,
        now: float,
        last_notification_at: float,
        emitted_notification_ids: set[str],
    ) -> GrowthNotificationDecision:
        """Choose a rare user-visible growth note from grounded journal entries."""

        timing_reason = self._notification_timing_reason(
            user_message_count=user_message_count,
            now=now,
            last_notification_at=last_notification_at,
        )
        if timing_reason is not None:
            return GrowthNotificationDecision(None, reason=timing_reason)

        for entry in entries:
            raw_notice = entry.get("growth_notification")
            if raw_notice is None:
                raw_notice = self._reflection_manager.build_growth_notification(entry)
            if not isinstance(raw_notice, dict):
                continue
            notification_id = str(raw_notice.get("id") or "")
            if not notification_id or notification_id in emitted_notification_ids:
                continue
            return GrowthNotificationDecision(
                raw_notice,
                notification_id=notification_id,
                reason="selected_grounded_growth_notice",
            )
        return GrowthNotificationDecision(None, reason="no_new_grounded_notice")

    def _notification_timing_reason(
        self,
        *,
        user_message_count: int,
        now: float,
        last_notification_at: float,
    ) -> str | None:
        if not self._settings.growth_notifications_enabled:
            return "disabled"
        min_user_messages = self._settings.growth_notification_min_user_messages
        if user_message_count < min_user_messages:
            return "needs_more_user_messages"
        message_interval = max(1, self._settings.growth_notification_message_interval)
        if user_message_count % message_interval != 0:
            return "message_interval"
        elapsed = now - last_notification_at
        min_interval = self._settings.growth_notification_min_interval_seconds
        if last_notification_at > 0 and elapsed < min_interval:
            return "wall_clock_throttle"
        return None

    def status(self) -> dict[str, Any]:
        """Return a concise, user-control-focused growth status snapshot."""

        return {
            "memory_enabled": self._settings.memory_enabled,
            "reflection_enabled": self._settings.reflection_enabled,
            "reflection_frequency": self._settings.reflection_frequency,
            "reflection_sensitivity": self._settings.reflection_sensitivity,
            "growth_notifications_enabled": self._settings.growth_notifications_enabled,
            "personal_lora": self._lora_trainer.status(),
        }


_growth_orchestrator: GrowthOrchestrator | None = None


def get_growth_orchestrator() -> GrowthOrchestrator:
    """Return a process-local growth orchestrator singleton."""

    global _growth_orchestrator
    if _growth_orchestrator is None:
        _growth_orchestrator = GrowthOrchestrator()
    return _growth_orchestrator


__all__ = [
    "GrowthNotificationDecision",
    "GrowthOrchestrator",
    "get_growth_orchestrator",
]
