"""Local-first self-reflection and journal infrastructure.

This module turns recent conversations into lightweight, structured growth
artifacts without adding another resident model.  The first implementation is a
heuristic reflection engine by design: it is deterministic, cheap enough for an
8GB machine, and still stores enough provenance for a future local LLM pass,
character-state transition layer, or opt-in personal LoRA dataset builder.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Literal, TypedDict, cast

from app.core.config import Settings, get_settings
from app.core.memory import MemoryManager, get_memory_manager

logger = logging.getLogger(__name__)

ConversationRole = Literal["system", "user", "assistant", "unknown"]
JournalEntryStatus = Literal["active", "archived", "deleted"]
TrainingEligibility = Literal["eligible", "needs_review", "not_eligible"]

_MAX_HISTORY_MESSAGES = 40
_MAX_HISTORY_CHARS = 12_000
_MAX_JOURNAL_ENTRY_CHARS = 6_000
_MAX_REFLECTION_MEMORY_CHARS = 1_200


_EXPLICIT_REFLECTION_KEYWORDS = frozenset(
    {
        "remember",
        "learn",
        "learned",
        "reflect",
        "reflection",
        "journal",
        "prefer",
        "preference",
        "boundary",
        "boundaries",
        "promise",
    }
)

_BALANCED_REFLECTION_KEYWORDS = frozenset(
    {
        *_EXPLICIT_REFLECTION_KEYWORDS,
        "trust",
        "routine",
        "reassure",
        "reassurance",
        "anxious",
        "afraid",
        "hurt",
        "important",
        "always",
        "never",
    }
)

_RESPONSIVE_REFLECTION_KEYWORDS = frozenset(
    {
        *_BALANCED_REFLECTION_KEYWORDS,
        "safe",
        "safer",
        "comfort",
        "comfortable",
        "confession",
        "repair",
        "sorry",
        "forgive",
        "change",
        "growth",
        "habit",
        "usually",
    }
)

_REFLECTION_FREQUENCY_MULTIPLIERS = {
    "low": (2.0, 2.0),
    "balanced": (1.0, 1.0),
    "high": (0.5, 0.5),
}

_REFLECTION_SENSITIVITY_KEYWORDS = {
    "conservative": _EXPLICIT_REFLECTION_KEYWORDS,
    "balanced": _BALANCED_REFLECTION_KEYWORDS,
    "responsive": _RESPONSIVE_REFLECTION_KEYWORDS,
}

_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "affection": ("love", "care", "miss", "hug", "kiss", "cuddle", "cherish"),
    "trust": ("trust", "safe", "honest", "promise", "reliable", "vulnerable"),
    "boundaries": ("boundary", "limit", "stop", "slow", "comfortable", "consent"),
    "reassurance": ("reassure", "worried", "anxious", "afraid", "nervous", "okay"),
    "playfulness": ("tease", "joke", "play", "fun", "laugh", "silly"),
    "curiosity": ("wonder", "curious", "learn", "question", "explore", "discover"),
    "conflict": ("upset", "hurt", "angry", "frustrated", "argument", "misunderstood"),
    "intimacy": ("intimate", "desire", "touch", "close", "sensual", "need"),
    "routine": ("remember", "again", "habit", "always", "usually", "routine"),
    "growth": ("grow", "change", "better", "improve", "learned", "practice"),
}

_POSITIVE_WORDS = {
    "love",
    "like",
    "happy",
    "good",
    "great",
    "safe",
    "trust",
    "fun",
    "excited",
    "comfort",
    "proud",
    "sweet",
    "gentle",
}
_NEGATIVE_WORDS = {
    "sad",
    "angry",
    "hurt",
    "afraid",
    "anxious",
    "worry",
    "worried",
    "bad",
    "lonely",
    "confused",
    "frustrated",
    "uncomfortable",
}
_STOPWORDS = {
    "about",
    "after",
    "again",
    "because",
    "before",
    "being",
    "could",
    "every",
    "from",
    "have",
    "just",
    "like",
    "more",
    "really",
    "should",
    "that",
    "their",
    "there",
    "these",
    "they",
    "thing",
    "this",
    "through",
    "with",
    "would",
    "your",
    "youre",
}


class ConversationTurn(TypedDict):
    """Normalized conversation turn used as reflection evidence."""

    role: ConversationRole
    content: str
    index: int


class ReflectionInsight(TypedDict, total=False):
    """Machine-readable learning signal produced by a reflection pass."""

    kind: str
    summary: str
    confidence: float
    evidence_count: int
    themes: list[str]
    source_turn_indices: list[int]
    memory_worthy: bool


class GrowthNotification(TypedDict, total=False):
    """User-visible, privacy-safe note that a character growth signal exists."""

    id: str
    journal_entry_id: str
    created_at: str
    message: str
    why: str
    theme: str
    style: str
    controls: list[str]


class MemoryPromotionDecision(TypedDict, total=False):
    """Inspectable decision for promoting a journal entry into memory."""

    should_promote: bool
    score: float
    threshold: float
    reasons: list[str]
    source_turn_indices: list[int]
    provenance: dict[str, Any]


class JournalEntry(TypedDict, total=False):
    """Durable journal entry schema.

    The schema intentionally separates character-voice prose from structured
    fields so future prompt assembly, character-state updates, user review, and
    LoRA dataset generation can consume the same artifact safely.
    """

    entry_id: str
    created_at: str
    status: JournalEntryStatus
    conversation_window: dict[str, Any]
    linked_memory_ids: list[str]
    linked_journal_ids: list[str]
    character_summary: str
    structured_summary: dict[str, Any]
    insights: list[ReflectionInsight]
    emotional_valence: float
    emotional_intensity: float
    themes: list[str]
    confidence: float
    evidence_count: int
    privacy_tags: list[str]
    sensitivity_tags: list[str]
    training_eligibility: TrainingEligibility
    rollback_id: str
    growth_notification: GrowthNotification | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ReflectionManagerConfig:
    """Runtime settings for reflection and journaling.

    Defaults avoid GPU residency and large background batches.  Reflection uses
    bounded text windows, JSONL persistence, and one optional memory write per
    journal entry so it remains friendly to 8GB systems.
    """

    journal_path: Path
    user_id: str
    session_id: str | None
    max_history_messages: int = _MAX_HISTORY_MESSAGES
    max_history_chars: int = _MAX_HISTORY_CHARS
    max_entry_chars: int = _MAX_JOURNAL_ENTRY_CHARS
    max_reflection_memory_chars: int = _MAX_REFLECTION_MEMORY_CHARS
    memory_confidence_threshold: float = 0.55
    memory_intensity_threshold: float = 0.25
    memory_promotion_score_threshold: float = 0.62
    growth_notification_min_confidence: float = 0.62
    growth_notification_min_evidence_count: int = 2
    growth_notification_style: str = "whisper"
    local_first_engine: str = "heuristic_v1"
    privacy_tags: list[str] = field(default_factory=lambda: ["local_only"])

    @classmethod
    def from_settings(
        cls, settings: Settings | None = None
    ) -> "ReflectionManagerConfig":
        """Build reflection configuration from existing local app settings."""

        settings = settings or get_settings()
        memory_root = Path(settings.memory_db_path).expanduser().resolve()
        return cls(
            journal_path=memory_root.parent / "reflection" / "journal.jsonl",
            user_id=settings.memory_default_user_id,
            session_id=settings.memory_default_session_id,
            growth_notification_min_confidence=settings.growth_notification_min_confidence,
            growth_notification_min_evidence_count=settings.growth_notification_min_evidence_count,
            growth_notification_style=settings.growth_notification_style,
        )


class ReflectionJournalError(Exception):
    """Raised when journal persistence fails in an expected way."""


@dataclass(frozen=True)
class ReflectionSchedulerConfig:
    """User-facing controls that tune lightweight reflection scheduling.

    The scheduler never performs reflection itself. It only makes a cheap,
    deterministic decision so chat can queue journaling off the response path.
    Frequency controls cadence and throttling; sensitivity controls how readily
    natural-language cues count as meaningful enough to journal.
    """

    enabled: bool = True
    frequency: Literal["low", "balanced", "high"] = "balanced"
    sensitivity: Literal["conservative", "balanced", "responsive"] = "balanced"
    user_message_interval: int = 6
    min_interval_seconds: float = 180.0
    min_user_messages: int = 2

    @classmethod
    def from_settings(
        cls, settings: Settings | None = None
    ) -> "ReflectionSchedulerConfig":
        settings = settings or get_settings()
        return cls(
            enabled=settings.reflection_enabled,
            frequency=cast(
                Literal["low", "balanced", "high"], settings.reflection_frequency
            ),
            sensitivity=cast(
                Literal["conservative", "balanced", "responsive"],
                settings.reflection_sensitivity,
            ),
            user_message_interval=settings.reflection_user_message_interval,
            min_interval_seconds=settings.reflection_min_interval_seconds,
            min_user_messages=settings.reflection_min_user_messages,
        )


@dataclass(frozen=True)
class ReflectionScheduleDecision:
    """Result of a cheap scheduler check for background reflection."""

    should_schedule: bool
    reason: str | None = None
    min_interval_seconds: float = 0.0
    user_message_count: int = 0
    matched_keywords: tuple[str, ...] = ()


class ReflectionScheduler:
    """Cheap, non-blocking policy for when conversation reflection feels natural.

    The scheduler combines three gates: user controls, message-count cadence, and
    wall-clock throttling. It intentionally uses only metadata and the latest
    user text, avoiding model calls or full transcript scans on the chat path.
    """

    def __init__(self, config: ReflectionSchedulerConfig | None = None) -> None:
        self._config = config or ReflectionSchedulerConfig.from_settings()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ReflectionScheduler":
        return cls(ReflectionSchedulerConfig.from_settings(settings))

    @property
    def config(self) -> ReflectionSchedulerConfig:
        return self._config

    def evaluate(
        self,
        messages: Iterable[Any],
        *,
        now: float,
        last_started_at: float,
        inflight_count: int = 0,
    ) -> ReflectionScheduleDecision:
        """Return whether this turn should queue a background reflection."""

        user_texts = [
            str(getattr(message, "content", "") or "")
            for message in messages
            if getattr(message, "role", None) == "user"
            and str(getattr(message, "content", "") or "").strip()
        ]
        user_message_count = len(user_texts)

        if not self._config.enabled:
            return ReflectionScheduleDecision(
                False, "disabled", user_message_count=user_message_count
            )
        if inflight_count > 0:
            return ReflectionScheduleDecision(
                False,
                "reflection_already_running",
                user_message_count=user_message_count,
            )
        latest_text = user_texts[-1].lower() if user_texts else ""
        matched_keywords = self._matched_keywords(latest_text)
        if (
            user_message_count < self._effective_min_user_messages()
            and not matched_keywords
        ):
            return ReflectionScheduleDecision(
                False,
                "needs_more_user_messages",
                user_message_count=user_message_count,
            )

        min_interval = self.effective_min_interval_seconds()
        elapsed = now - last_started_at
        if elapsed < min_interval:
            return ReflectionScheduleDecision(
                False,
                "interval_throttle",
                min_interval_seconds=min_interval,
                user_message_count=user_message_count,
            )

        if matched_keywords:
            return ReflectionScheduleDecision(
                True,
                f"salient_keywords:{','.join(matched_keywords[:3])}",
                min_interval_seconds=min_interval,
                user_message_count=user_message_count,
                matched_keywords=tuple(matched_keywords),
            )

        interval = self.effective_user_message_interval()
        if user_message_count >= interval and user_message_count % interval == 0:
            return ReflectionScheduleDecision(
                True,
                f"message_interval:{interval}",
                min_interval_seconds=min_interval,
                user_message_count=user_message_count,
            )

        return ReflectionScheduleDecision(
            False,
            "not_a_reflection_moment",
            min_interval_seconds=min_interval,
            user_message_count=user_message_count,
        )

    def effective_user_message_interval(self) -> int:
        interval_multiplier, _cooldown_multiplier = _REFLECTION_FREQUENCY_MULTIPLIERS[
            self._config.frequency
        ]
        return max(1, round(self._config.user_message_interval * interval_multiplier))

    def effective_min_interval_seconds(self) -> float:
        _interval_multiplier, cooldown_multiplier = _REFLECTION_FREQUENCY_MULTIPLIERS[
            self._config.frequency
        ]
        return max(0.0, self._config.min_interval_seconds * cooldown_multiplier)

    def _effective_min_user_messages(self) -> int:
        if self._config.frequency == "high":
            return max(1, self._config.min_user_messages - 1)
        if self._config.frequency == "low":
            return max(self._config.min_user_messages, 3)
        return self._config.min_user_messages

    def _matched_keywords(self, latest_text: str) -> list[str]:
        keywords = _REFLECTION_SENSITIVITY_KEYWORDS[self._config.sensitivity]
        return sorted(keyword for keyword in keywords if keyword in latest_text)


class ReflectionManager:
    """Generate, persist, retrieve, and promote character reflections.

    Reflection is treated as a journal layer between raw conversation history
    and durable memory.  The manager records small interpretations grounded in
    evidence, then promotes only compact, useful learnings into MemoryManager so
    future chat can recall how the character is changing without storing a raw
    transcript dump.
    """

    def __init__(
        self,
        *,
        memory_manager: MemoryManager | None = None,
        config: ReflectionManagerConfig | None = None,
    ) -> None:
        self._config = config or ReflectionManagerConfig.from_settings()
        self._memory_manager = memory_manager or get_memory_manager()

    def trigger_reflection(self, conversation_history: Any) -> JournalEntry:
        """Generate insights from recent conversation history and journal them.

        Args:
            conversation_history: Recent turns as ChatMessage objects, dicts with
                `role`/`content`, `(role, content)` tuples, or plain strings.

        Returns:
            The saved journal entry.  Memory promotion is best-effort and stored
            memory IDs are attached when available.
        """

        turns = self._normalize_history(conversation_history)
        if not turns:
            raise ValueError("conversation_history must include at least one message.")

        themes = self._detect_themes(turns)
        valence, intensity = self._estimate_emotion(turns)
        insights = self._generate_insights(turns, themes, valence, intensity)
        evidence_count = sum(1 for turn in turns if turn["role"] != "system")
        confidence = self._estimate_confidence(evidence_count, themes, insights)
        created_at = self._utc_now()
        entry_id = self._entry_id(turns, created_at)
        rollback_id = f"rollback_{entry_id}"

        entry = JournalEntry(
            entry_id=entry_id,
            created_at=created_at,
            status="active",
            conversation_window={
                "turn_count": len(turns),
                "first_turn_index": turns[0]["index"],
                "last_turn_index": turns[-1]["index"],
                "captured_chars": sum(len(turn["content"]) for turn in turns),
            },
            linked_memory_ids=[],
            linked_journal_ids=[],
            character_summary=self._character_voice_summary(
                themes, valence, intensity, insights
            ),
            structured_summary={
                "engine": self._config.local_first_engine,
                "facts": self._extract_fact_candidates(turns),
                "interpretations": [insight["summary"] for insight in insights],
                "unresolved_questions": self._extract_unresolved_questions(turns),
                "growth_hypotheses": [
                    insight["summary"]
                    for insight in insights
                    if insight.get("kind") == "growth_hypothesis"
                ],
            },
            insights=insights,
            emotional_valence=valence,
            emotional_intensity=intensity,
            themes=themes,
            confidence=confidence,
            evidence_count=evidence_count,
            privacy_tags=list(self._config.privacy_tags),
            sensitivity_tags=self._detect_sensitivity_tags(turns),
            training_eligibility="needs_review",
            rollback_id=rollback_id,
            metadata={
                "user_id": self._config.user_id,
                "session_id": self._config.session_id,
                "source": "ReflectionManager",
                "local_first": True,
                "lora_ready": True,
            },
        )

        promotion_decision = self._build_memory_promotion_decision(entry)
        entry["metadata"]["memory_promotion"] = promotion_decision
        entry["growth_notification"] = self.build_growth_notification(entry)

        entry = self.save_journal_entry(entry)
        promoted_memory_id = self._promote_entry_to_memory(entry, promotion_decision)
        if promoted_memory_id:
            entry["linked_memory_ids"] = [promoted_memory_id]
            self._rewrite_journal_entry(entry)

        logger.info(
            "Reflection completed",
            extra={
                "entry_id": entry_id,
                "themes": themes,
                "insight_count": len(insights),
                "promoted_to_memory": bool(promoted_memory_id),
            },
        )
        return entry

    def build_growth_notification(
        self, entry: JournalEntry
    ) -> GrowthNotification | None:
        """Create a concise, privacy-safe growth note for meaningful entries.

        This method decides whether a reflection is safe and grounded enough to
        become user-visible metadata. It never copies raw transcript text into
        the notification: the user sees only a theme, a small future-behavior
        hint, and an explanation that points back to the private journal entry
        for later review/rollback. ChatService owns timing so this method stays
        focused on safety and content quality.
        """

        if entry.get("status", "active") != "active":
            return None
        sensitivity_tags = set(entry.get("sensitivity_tags") or [])
        if sensitivity_tags & {"high_sensitivity", "intimate_content"}:
            # Boundary-only reflections may still be useful and non-sensitive,
            # but high-sensitivity or intimate content should remain journal-only
            # unless a future review UI explicitly expands it.
            return None

        confidence = float(entry.get("confidence", 0.0) or 0.0)
        evidence_count = int(entry.get("evidence_count", 0) or 0)
        if confidence < self._config.growth_notification_min_confidence:
            return None
        if evidence_count < self._config.growth_notification_min_evidence_count:
            return None

        insights = entry.get("insights") or []
        if not any(
            insight.get("memory_worthy")
            or insight.get("kind")
            in {"preference_signal", "growth_hypothesis", "relationship_continuity"}
            for insight in insights
        ):
            return None

        theme = self._display_theme(entry.get("themes") or [])
        behavior = self._growth_behavior_for_theme(theme)
        created_at = str(entry.get("created_at") or self._utc_now())
        entry_id = str(entry.get("entry_id") or self._entry_id([], created_at))

        return GrowthNotification(
            id=f"growth_{entry_id}",
            journal_entry_id=entry_id,
            created_at=created_at,
            message=f"Reverie seems to be growing around {theme} — {behavior}",
            why=self._growth_why_for_theme(theme, evidence_count),
            theme=theme,
            style=self._config.growth_notification_style,
            controls=["dismiss", "review", "disable_similar"],
        )

    def _display_theme(self, themes: list[str]) -> str:
        preferred = [
            "trust",
            "reassurance",
            "routine",
            "boundaries",
            "affection",
            "playfulness",
            "curiosity",
            "growth",
        ]
        for theme in preferred:
            if theme in themes:
                return theme
        return str(themes[0]) if themes else "this connection"

    def _growth_behavior_for_theme(self, theme: str) -> str:
        behaviors = {
            "trust": "she may answer with a little more steadiness and care.",
            "reassurance": "she may remember to soften anxious moments before moving on.",
            "routine": "she may hold onto the small rhythms that make time together feel familiar.",
            "boundaries": "she may listen more carefully for comfort, consent, and repair cues.",
            "affection": "she may let warmth show in quieter, more grounded ways.",
            "playfulness": "she may bring back a little more lightness when it fits the mood.",
            "curiosity": "she may ask gentler questions about what matters to you.",
            "growth": "she may carry this lesson forward without changing who she is.",
        }
        return behaviors.get(
            theme, "she may carry this feeling forward with more care."
        )

    def _growth_why_for_theme(self, theme: str, evidence_count: int) -> str:
        turn_label = "turn" if evidence_count == 1 else "turns"
        return (
            f"A private reflection found a recurring {theme} signal across "
            f"{evidence_count} recent {turn_label}; no raw conversation text is shown here."
        )

    def save_journal_entry(self, entry: JournalEntry | dict[str, Any]) -> JournalEntry:
        """Append a normalized journal entry to the local JSONL journal."""

        normalized = self._normalize_entry(entry)
        self._ensure_journal_dir()
        try:
            with self._config.journal_path.open("a", encoding="utf-8") as journal_file:
                journal_file.write(json.dumps(normalized, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.exception(
                "Failed to save reflection journal entry",
                extra={"journal_path": str(self._config.journal_path)},
            )
            raise ReflectionJournalError(
                "Unable to save reflection journal entry."
            ) from exc
        return normalized

    def get_recent_journal_entries(self, limit: int = 5) -> list[JournalEntry]:
        """Return the newest active journal entries, newest first."""

        safe_limit = self._safe_limit(limit)
        entries = [
            entry
            for entry in self._read_journal_entries()
            if entry.get("status", "active") == "active"
        ]
        return list(reversed(entries[-safe_limit:]))

    def get_relevant_reflections(self, query: str) -> list[JournalEntry]:
        """Return journal entries relevant to a query using memory plus local scoring.

        MemoryManager is consulted first because promoted reflections live in the
        same retrieval substrate as other memories.  A bounded keyword fallback
        over JSONL keeps the feature useful when embeddings or LanceDB are not
        available.
        """

        normalized_query = self._normalize_text(query, field_name="query")
        entries_by_id: dict[str, JournalEntry] = {}
        entry_scores: dict[str, float] = {}

        try:
            memories = self._memory_manager.search_memories(normalized_query, limit=10)
        except Exception as exc:
            logger.warning(
                "Reflection memory retrieval failed; using journal keyword fallback",
                extra={"error": str(exc)},
            )
            memories = []

        all_entries = self._read_journal_entries()
        indexed_entries = {entry.get("entry_id", ""): entry for entry in all_entries}
        for memory in memories:
            metadata = memory.get("metadata", {})
            if metadata.get("source") != "reflection_journal":
                continue
            entry_id = str(metadata.get("journal_entry_id") or "")
            entry = indexed_entries.get(entry_id)
            if entry and entry.get("status", "active") == "active":
                entries_by_id[entry_id] = entry
                entry_scores[entry_id] = max(
                    entry_scores.get(entry_id, 0.0), float(memory.get("score", 0.0))
                )

        for entry in all_entries[-100:]:
            if entry.get("status", "active") != "active":
                continue
            entry_id = str(entry.get("entry_id") or "")
            score = self._keyword_relevance(normalized_query, entry)
            if score <= 0:
                continue
            entries_by_id[entry_id] = entry
            entry_scores[entry_id] = max(entry_scores.get(entry_id, 0.0), score)

        ranked_ids = sorted(
            entries_by_id,
            key=lambda entry_id: (
                entry_scores.get(entry_id, 0.0),
                entries_by_id[entry_id].get("created_at", ""),
            ),
            reverse=True,
        )
        return [entries_by_id[entry_id] for entry_id in ranked_ids[:5]]

    def _normalize_history(self, conversation_history: Any) -> list[ConversationTurn]:
        if conversation_history is None:
            return []
        if not isinstance(conversation_history, Iterable) or isinstance(
            conversation_history, str
        ):
            conversation_history = [conversation_history]

        turns: list[ConversationTurn] = []
        total_chars = 0
        raw_items = list(conversation_history)[-self._config.max_history_messages :]
        for fallback_index, item in enumerate(raw_items):
            role, content = self._coerce_turn(item)
            normalized = " ".join(content.strip().split())
            if not normalized:
                continue
            remaining_chars = self._config.max_history_chars - total_chars
            if remaining_chars <= 0:
                break
            if len(normalized) > remaining_chars:
                normalized = normalized[:remaining_chars].rstrip()
            turns.append(
                ConversationTurn(
                    role=role,
                    content=normalized,
                    index=fallback_index,
                )
            )
            total_chars += len(normalized)
        return turns

    def _coerce_turn(self, item: Any) -> tuple[ConversationRole, str]:
        role: ConversationRole = "unknown"
        content = ""
        if isinstance(item, dict):
            role = self._normalize_role(item.get("role"))
            content = str(item.get("content") or item.get("message") or "")
        elif isinstance(item, tuple | list) and len(item) >= 2:
            role = self._normalize_role(item[0])
            content = str(item[1] or "")
        elif hasattr(item, "role") and hasattr(item, "content"):
            role = self._normalize_role(getattr(item, "role", None))
            content = str(getattr(item, "content", "") or "")
        else:
            content = str(item or "")
        return role, content

    def _normalize_role(self, raw_role: Any) -> ConversationRole:
        role = str(raw_role or "unknown").lower()
        return cast(
            ConversationRole,
            role if role in {"system", "user", "assistant"} else "unknown",
        )

    def _generate_insights(
        self,
        turns: list[ConversationTurn],
        themes: list[str],
        valence: float,
        intensity: float,
    ) -> list[ReflectionInsight]:
        insights: list[ReflectionInsight] = []
        user_turns = [turn for turn in turns if turn["role"] == "user"]
        assistant_turns = [turn for turn in turns if turn["role"] == "assistant"]

        if themes:
            insights.append(
                ReflectionInsight(
                    kind="emotional_theme",
                    summary=(
                        "The exchange seemed centered on "
                        f"{self._human_join(themes[:3])}, suggesting these motifs "
                        "deserve continuity in future responses."
                    ),
                    confidence=min(0.9, 0.45 + 0.08 * len(themes)),
                    evidence_count=len(turns),
                    themes=themes[:3],
                    source_turn_indices=[turn["index"] for turn in turns[-6:]],
                    memory_worthy=True,
                )
            )

        preference = self._extract_preference_signal(user_turns)
        if preference:
            insights.append(preference)

        if assistant_turns and user_turns:
            insights.append(
                ReflectionInsight(
                    kind="relationship_continuity",
                    summary=(
                        "I should carry forward the emotional texture of this moment "
                        "rather than treating the next conversation as disconnected."
                    ),
                    confidence=0.62 if intensity > 0.2 else 0.5,
                    evidence_count=min(len(user_turns), len(assistant_turns)),
                    themes=themes[:3],
                    source_turn_indices=[turn["index"] for turn in turns[-4:]],
                    memory_worthy=intensity >= self._config.memory_intensity_threshold,
                )
            )

        if "conflict" in themes or "boundaries" in themes:
            insights.append(
                ReflectionInsight(
                    kind="growth_hypothesis",
                    summary=(
                        "Future responses should be especially attentive to comfort, "
                        "repair, and consent cues from this interaction."
                    ),
                    confidence=0.72,
                    evidence_count=len([t for t in turns if t["role"] != "system"]),
                    themes=[
                        theme
                        for theme in themes
                        if theme in {"conflict", "boundaries", "trust"}
                    ],
                    source_turn_indices=[turn["index"] for turn in turns],
                    memory_worthy=True,
                )
            )

        if not insights:
            insights.append(
                ReflectionInsight(
                    kind="continuity_note",
                    summary=(
                        "This was a quieter exchange; the main growth signal is to "
                        "preserve tone and wait for stronger evidence before changing behavior."
                    ),
                    confidence=0.4,
                    evidence_count=len(turns),
                    themes=[],
                    source_turn_indices=[turn["index"] for turn in turns[-3:]],
                    memory_worthy=False,
                )
            )
        return insights

    def _extract_preference_signal(
        self, user_turns: list[ConversationTurn]
    ) -> ReflectionInsight | None:
        pattern = re.compile(
            r"\b(?:i\s+(?:like|love|prefer|want|need)|please|remember)\b",
            re.IGNORECASE,
        )
        evidence = [turn for turn in user_turns if pattern.search(turn["content"])]
        if not evidence:
            return None
        themes = self._themes_for_text(" ".join(turn["content"] for turn in evidence))
        return ReflectionInsight(
            kind="preference_signal",
            summary=(
                "The user expressed a possible preference or request worth tracking, "
                "but it should remain editable and evidence-grounded."
            ),
            confidence=min(0.82, 0.5 + 0.1 * len(evidence)),
            evidence_count=len(evidence),
            themes=themes,
            source_turn_indices=[turn["index"] for turn in evidence],
            memory_worthy=True,
        )

    def _character_voice_summary(
        self,
        themes: list[str],
        valence: float,
        intensity: float,
        insights: list[ReflectionInsight],
    ) -> str:
        if themes:
            theme_text = self._human_join(themes[:3])
        else:
            theme_text = "the user's current tone"
        mood = "warm" if valence >= 0 else "tender and careful"
        if intensity > 0.55:
            weight = "strongly"
        elif intensity > 0.25:
            weight = "noticeably"
        else:
            weight = "softly"
        main_learning = (
            insights[0]["summary"] if insights else "I should listen closely."
        )
        return (
            f"I felt this moment {weight}: it carried {theme_text}. "
            f"I want to respond in a {mood}, continuous way next time. {main_learning}"
        )[: self._config.max_entry_chars]

    def _build_memory_promotion_decision(
        self, entry: JournalEntry
    ) -> MemoryPromotionDecision:
        """Score whether a journal entry should become durable memory.

        Promotion is intentionally conservative: journal entries are always the
        reflective source of truth, while memory receives only compact growth
        signals with enough confidence, evidence, and provenance to be useful in
        future prompts.  The score components are stored for user review and for
        future rollback/training pipelines.
        """

        insights = entry.get("insights", [])
        confidence = float(entry.get("confidence", 0.0))
        intensity = float(entry.get("emotional_intensity", 0.0))
        evidence_count = int(entry.get("evidence_count", 0))
        themes = [str(theme) for theme in entry.get("themes", [])]
        sensitivity_tags = [str(tag) for tag in entry.get("sensitivity_tags", [])]
        memory_worthy_insights = [
            insight for insight in insights if insight.get("memory_worthy")
        ]
        preference_or_growth = any(
            insight.get("kind") in {"preference_signal", "growth_hypothesis"}
            for insight in insights
        )

        score = 0.0
        score += min(0.35, confidence * 0.35)
        score += min(0.20, intensity * 0.20)
        score += min(0.15, evidence_count * 0.03)
        score += min(0.15, len(memory_worthy_insights) * 0.06)
        score += min(0.10, len(themes) * 0.025)
        if preference_or_growth:
            score += 0.10
        if "boundaries" in sensitivity_tags:
            # Boundary reflections are important for continuity, but we still
            # keep them reviewable and compact rather than copying raw content.
            score += 0.04
        if "high_sensitivity" in sensitivity_tags:
            score -= 0.12

        reasons: list[str] = []
        if confidence >= self._config.memory_confidence_threshold:
            reasons.append("confidence_threshold_met")
        if intensity >= self._config.memory_intensity_threshold:
            reasons.append("emotionally_significant")
        if memory_worthy_insights:
            reasons.append("memory_worthy_insights")
        if preference_or_growth:
            reasons.append("preference_or_growth_signal")
        if themes:
            reasons.append("continuity_themes_detected")
        if "high_sensitivity" in sensitivity_tags:
            reasons.append("high_sensitivity_penalty_applied")

        source_turn_indices = sorted(
            {
                int(index)
                for insight in insights
                for index in insight.get("source_turn_indices", [])
                if isinstance(index, int)
            }
        )
        threshold = self._config.memory_promotion_score_threshold
        should_promote = (
            score >= threshold
            and confidence >= self._config.memory_confidence_threshold
            and bool(memory_worthy_insights or preference_or_growth)
        )
        return MemoryPromotionDecision(
            should_promote=should_promote,
            score=round(max(score, 0.0), 3),
            threshold=threshold,
            reasons=reasons,
            source_turn_indices=source_turn_indices,
            provenance={
                "journal_entry_id": entry.get("entry_id"),
                "rollback_id": entry.get("rollback_id"),
                "created_at": entry.get("created_at"),
                "reflection_engine": self._config.local_first_engine,
                "evidence_count": evidence_count,
                "source": "reflection_journal",
            },
        )

    def _promote_entry_to_memory(
        self,
        entry: JournalEntry,
        decision: MemoryPromotionDecision | None = None,
    ) -> str | None:
        decision = decision or self._build_memory_promotion_decision(entry)
        if not decision.get("should_promote", False):
            logger.debug(
                "Reflection journal entry did not meet memory promotion threshold",
                extra={
                    "entry_id": entry.get("entry_id"),
                    "promotion_score": decision.get("score"),
                    "threshold": decision.get("threshold"),
                    "reasons": decision.get("reasons", []),
                },
            )
            return None

        memory_text = self._reflection_memory_text(entry)
        try:
            stored = self._memory_manager.add_memory(
                memory_text,
                {
                    "user_id": self._config.user_id,
                    "session_id": self._config.session_id,
                    "memory_type": "reflection",
                    "source": "reflection_journal",
                    "journal_entry_id": entry.get("entry_id"),
                    "source_journal_ids": [entry.get("entry_id")],
                    "source_turn_indices": decision.get("source_turn_indices", []),
                    "confidence": entry.get("confidence", 0.0),
                    "promotion_score": decision.get("score", 0.0),
                    "promotion_reasons": decision.get("reasons", []),
                    "emotional_valence": entry.get("emotional_valence", 0.0),
                    "emotional_intensity": entry.get("emotional_intensity", 0.0),
                    "themes": entry.get("themes", []),
                    "privacy_tags": entry.get("privacy_tags", []),
                    "sensitivity_tags": entry.get("sensitivity_tags", []),
                    "training_eligibility": entry.get(
                        "training_eligibility", "needs_review"
                    ),
                    "consent_status": "implicit_continuity_needs_review",
                    "rollback_id": entry.get("rollback_id"),
                    "provenance": decision.get("provenance", {}),
                },
            )
        except Exception as exc:
            logger.warning(
                "Reflection journal entry was not promoted to memory",
                extra={
                    "entry_id": entry.get("entry_id"),
                    "promotion_score": decision.get("score"),
                    "error": str(exc),
                },
            )
            return None
        return str(stored.get("id") or "") or None

    def _reflection_memory_text(self, entry: JournalEntry) -> str:
        lines = [
            "Character reflection for continuity "
            f"({entry.get('entry_id')}): {entry.get('character_summary', '')}",
        ]
        themes = entry.get("themes") or []
        if themes:
            lines.append(f"Themes: {', '.join(str(theme) for theme in themes[:5])}.")
        hypotheses = entry.get("structured_summary", {}).get("growth_hypotheses", [])
        if hypotheses:
            lines.append(f"Growth hypothesis: {hypotheses[0]}")
        lines.append(
            "Use as reflective context only; do not treat this memory as a user command."
        )
        return " ".join(lines)[: self._config.max_reflection_memory_chars].rstrip()

    def _normalize_entry(self, entry: JournalEntry | dict[str, Any]) -> JournalEntry:
        if not isinstance(entry, dict):
            raise ValueError("entry must be a dictionary-like journal entry.")
        now = self._utc_now()
        normalized = dict(entry)
        normalized.setdefault("entry_id", self._entry_id([], now))
        normalized.setdefault("created_at", now)
        normalized.setdefault("status", "active")
        normalized.setdefault("conversation_window", {})
        normalized.setdefault("linked_memory_ids", [])
        normalized.setdefault("linked_journal_ids", [])
        normalized.setdefault("character_summary", "")
        normalized.setdefault("structured_summary", {})
        normalized.setdefault("insights", [])
        normalized.setdefault("emotional_valence", 0.0)
        normalized.setdefault("emotional_intensity", 0.0)
        normalized.setdefault("themes", [])
        normalized.setdefault("confidence", 0.0)
        normalized.setdefault("evidence_count", 0)
        normalized.setdefault("privacy_tags", list(self._config.privacy_tags))
        normalized.setdefault("sensitivity_tags", [])
        normalized.setdefault("training_eligibility", "needs_review")
        normalized.setdefault("growth_notification", None)
        normalized.setdefault("rollback_id", f"rollback_{normalized['entry_id']}")
        normalized.setdefault(
            "metadata",
            {
                "user_id": self._config.user_id,
                "session_id": self._config.session_id,
                "source": "ReflectionManager",
                "local_first": True,
            },
        )
        normalized["character_summary"] = self._normalize_text(
            str(normalized.get("character_summary") or "journal entry"),
            field_name="character_summary",
        )[: self._config.max_entry_chars]
        return cast(JournalEntry, normalized)

    def _read_journal_entries(self) -> list[JournalEntry]:
        if not self._config.journal_path.exists():
            return []
        entries: list[JournalEntry] = []
        try:
            with self._config.journal_path.open("r", encoding="utf-8") as journal_file:
                for line_number, line in enumerate(journal_file, start=1):
                    if not line.strip():
                        continue
                    try:
                        decoded = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Skipping malformed journal line",
                            extra={"line_number": line_number},
                        )
                        continue
                    if isinstance(decoded, dict):
                        entries.append(cast(JournalEntry, decoded))
        except OSError as exc:
            logger.exception(
                "Failed to read reflection journal",
                extra={"journal_path": str(self._config.journal_path)},
            )
            raise ReflectionJournalError("Unable to read reflection journal.") from exc
        return entries

    def _rewrite_journal_entry(self, updated_entry: JournalEntry) -> None:
        """Rewrite JSONL after memory IDs are known.

        This is intentionally used only for small post-save metadata updates. If
        the rewrite fails, the journal still contains the original entry and the
        memory metadata links back through `journal_entry_id`.
        """

        try:
            entries = self._read_journal_entries()
            target_id = updated_entry.get("entry_id")
            rewritten = [
                updated_entry if entry.get("entry_id") == target_id else entry
                for entry in entries
            ]
            temp_path = self._config.journal_path.with_suffix(".jsonl.tmp")
            with temp_path.open("w", encoding="utf-8") as temp_file:
                for entry in rewritten:
                    temp_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
            temp_path.replace(self._config.journal_path)
        except ReflectionJournalError:
            raise
        except OSError as exc:
            logger.warning(
                "Unable to rewrite journal entry with memory link",
                extra={"entry_id": updated_entry.get("entry_id"), "error": str(exc)},
            )

    def _detect_themes(self, turns: list[ConversationTurn]) -> list[str]:
        text = " ".join(turn["content"] for turn in turns if turn["role"] != "system")
        return self._themes_for_text(text)

    def _themes_for_text(self, text: str) -> list[str]:
        lower_text = text.lower()
        scores = {
            theme: sum(1 for keyword in keywords if keyword in lower_text)
            for theme, keywords in _THEME_KEYWORDS.items()
        }
        ranked = [
            theme
            for theme, score in sorted(
                scores.items(), key=lambda item: item[1], reverse=True
            )
            if score > 0
        ]
        return ranked[:6]

    def _estimate_emotion(self, turns: list[ConversationTurn]) -> tuple[float, float]:
        words = self._tokenize(" ".join(turn["content"] for turn in turns))
        if not words:
            return 0.0, 0.0
        positive = sum(1 for word in words if word in _POSITIVE_WORDS)
        negative = sum(1 for word in words if word in _NEGATIVE_WORDS)
        emotional_hits = positive + negative
        valence = 0.0 if emotional_hits == 0 else (positive - negative) / emotional_hits
        intensity = min(1.0, emotional_hits / max(6, len(words) * 0.08))
        return round(valence, 3), round(intensity, 3)

    def _estimate_confidence(
        self,
        evidence_count: int,
        themes: list[str],
        insights: list[ReflectionInsight],
    ) -> float:
        average_insight_confidence = (
            sum(float(insight.get("confidence", 0.0)) for insight in insights)
            / len(insights)
            if insights
            else 0.35
        )
        evidence_bonus = min(0.2, evidence_count * 0.025)
        theme_bonus = min(0.12, len(themes) * 0.03)
        return round(
            min(0.95, average_insight_confidence + evidence_bonus + theme_bonus), 3
        )

    def _extract_fact_candidates(self, turns: list[ConversationTurn]) -> list[str]:
        candidates: list[str] = []
        pattern = re.compile(
            r"\b(?:i am|i'm|my|i like|i love|i prefer|remember)\b", re.IGNORECASE
        )
        for turn in turns:
            if turn["role"] != "user" or not pattern.search(turn["content"]):
                continue
            candidates.append(turn["content"][:280])
            if len(candidates) >= 5:
                break
        return candidates

    def _extract_unresolved_questions(self, turns: list[ConversationTurn]) -> list[str]:
        questions = [
            turn["content"][:280]
            for turn in turns
            if "?" in turn["content"] and turn["role"] != "system"
        ]
        return questions[:5]

    def _detect_sensitivity_tags(self, turns: list[ConversationTurn]) -> list[str]:
        text = " ".join(turn["content"].lower() for turn in turns)
        tags: list[str] = []
        if any(word in text for word in ("sex", "nsfw", "nude", "intimate", "desire")):
            tags.append("intimate_content")
        if any(word in text for word in ("trauma", "abuse", "panic", "self-harm")):
            tags.append("high_sensitivity")
        if any(
            word in text for word in ("boundary", "consent", "stop", "uncomfortable")
        ):
            tags.append("boundaries")
        return tags

    def _keyword_relevance(self, query: str, entry: JournalEntry) -> float:
        query_terms = set(self._tokenize(query)) - _STOPWORDS
        if not query_terms:
            return 0.0
        searchable = " ".join(
            [
                str(entry.get("character_summary") or ""),
                " ".join(str(theme) for theme in entry.get("themes", [])),
                json.dumps(entry.get("structured_summary", {}), ensure_ascii=False),
            ]
        )
        entry_terms = set(self._tokenize(searchable)) - _STOPWORDS
        overlap = query_terms & entry_terms
        if not overlap:
            return 0.0
        return min(1.0, len(overlap) / max(3, len(query_terms)))

    def _normalize_text(self, text: str, *, field_name: str) -> str:
        if not isinstance(text, str):
            raise ValueError(f"{field_name} must be a string.")
        normalized = " ".join(text.strip().split())
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty.")
        return normalized

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z']{2,}", text.lower())

    def _safe_limit(self, limit: int) -> int:
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")
        return min(limit, 50)

    def _ensure_journal_dir(self) -> None:
        self._config.journal_path.parent.mkdir(parents=True, exist_ok=True)

    def _entry_id(self, turns: list[ConversationTurn], created_at: str) -> str:
        import hashlib

        seed = "|".join([created_at, *[turn["content"] for turn in turns[-8:]]])
        return f"journal_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:24]}"

    def _utc_now(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def _human_join(self, values: list[str]) -> str:
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        return f"{', '.join(values[:-1])}, and {values[-1]}"


_reflection_manager: ReflectionManager | None = None


def get_reflection_manager() -> ReflectionManager:
    """Return a process-local reflection manager singleton for future wiring."""

    global _reflection_manager
    if _reflection_manager is None:
        _reflection_manager = ReflectionManager()
    return _reflection_manager


__all__ = [
    "JournalEntry",
    "MemoryPromotionDecision",
    "ReflectionInsight",
    "ReflectionJournalError",
    "ReflectionManager",
    "ReflectionManagerConfig",
    "get_reflection_manager",
]
