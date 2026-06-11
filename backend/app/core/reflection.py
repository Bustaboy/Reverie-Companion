"""Self-reflection and journaling primitives for companion growth.

This module is intentionally local-first and lightweight.  It does not add API
routes, does not require a second resident model, and stores journal artifacts as
JSON Lines so they can be inspected, backed up, deleted, or later transformed
into opt-in LoRA training datasets.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, TypedDict

from app.core.memory import (
    MemoryError,
    MemoryManager,
    MemorySearchResult,
    get_memory_manager,
)

logger = logging.getLogger(__name__)


class ReflectionTurn(TypedDict):
    """Normalized conversation turn used by the reflection loop."""

    role: str
    content: str
    index: int


class JournalEntry(TypedDict, total=False):
    """Serializable journal entry shape returned by ReflectionManager."""

    id: str
    schema_version: str
    created_at: str
    conversation_window: dict[str, int | str | None]
    source_turns: list[ReflectionTurn]
    linked_memory_ids: list[str]
    character_voice_summary: str
    structured_summary: dict[str, Any]
    emotional_valence: str
    emotional_intensity: float
    themes: list[str]
    confidence: float
    evidence_count: int
    privacy_tags: list[str]
    training_eligible: bool
    training_notes: str
    rollback_id: str
    memory_promoted: bool
    local_relevance_score: float


@dataclass(frozen=True)
class ReflectionManagerConfig:
    """Configuration for bounded, 8GB-friendly reflection work."""

    journal_path: Path = Path("./data/reflections/journal.jsonl")
    max_history_turns: int = 24
    max_turn_chars: int = 2_000
    max_saved_turns: int = 12
    max_recent_entries: int = 50
    max_relevant_reflections: int = 5
    memory_promotion_min_confidence: float = 0.55
    memory_promotion_min_evidence: int = 2
    local_relevance_min_score: float = 0.02
    user_id: str = "local_user"


@dataclass(frozen=True)
class _InsightSet:
    """Internal aggregate produced from recent conversation turns."""

    observations: list[str] = field(default_factory=list)
    growth_edges: list[str] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    boundaries: list[str] = field(default_factory=list)
    emotional_cues: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    emotional_valence: str = "neutral"
    emotional_intensity: float = 0.0
    confidence: float = 0.0
    evidence_count: int = 0


class ReflectionManager:
    """Generate, persist, and retrieve companion self-reflections.

    The manager treats journaling as a distinct growth layer above raw memory:
    reflections summarize what the companion believes it learned, retain
    provenance back to source turns and memories, and only promote compact,
    confidence-scored conclusions into MemoryManager when useful. This keeps
    future behavior grounded without letting a single conversation rewrite the
    character wholesale.
    """

    _POSITIVE_WORDS = {
        "happy",
        "glad",
        "excited",
        "safe",
        "comforted",
        "loved",
        "trust",
        "enjoy",
        "fun",
        "sweet",
        "beautiful",
        "good",
        "great",
        "better",
    }
    _NEGATIVE_WORDS = {
        "sad",
        "angry",
        "hurt",
        "afraid",
        "scared",
        "lonely",
        "anxious",
        "upset",
        "bad",
        "worse",
        "hate",
        "uncomfortable",
        "overwhelmed",
    }
    _STOPWORDS = {
        "about",
        "after",
        "again",
        "also",
        "because",
        "before",
        "being",
        "could",
        "really",
        "should",
        "their",
        "there",
        "these",
        "thing",
        "think",
        "those",
        "through",
        "today",
        "would",
        "with",
        "your",
        "youre",
        "have",
        "that",
        "this",
        "just",
        "like",
        "want",
        "feel",
        "from",
        "they",
        "them",
        "were",
        "been",
    }
    _PREFERENCE_PATTERNS = (
        re.compile(
            r"\b(?:i\s+)?(?:like|love|enjoy|prefer|want)\s+([^.!?]{3,120})", re.I
        ),
        re.compile(
            r"\b(?:my\s+favorite|favourite)\s+(?:is|are)\s+([^.!?]{3,120})", re.I
        ),
    )
    _BOUNDARY_PATTERNS = (
        re.compile(
            r"\b(?:i\s+)?(?:do\s+not|don't|dont|never)\s+(?:like|want|enjoy)\s+([^.!?]{3,120})",
            re.I,
        ),
        re.compile(
            r"\b(?:please\s+)?(?:stop|avoid|don't|dont)\s+([^.!?]{3,120})", re.I
        ),
        re.compile(r"\b(?:i'm|i am)\s+uncomfortable\s+with\s+([^.!?]{3,120})", re.I),
    )

    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        config: ReflectionManagerConfig | None = None,
    ) -> None:
        self._config = config or ReflectionManagerConfig()
        self._memory_manager = memory_manager or get_memory_manager()

    def trigger_reflection(self, conversation_history: Iterable[Any]) -> JournalEntry:
        """Reflect on recent conversation history, persist a journal entry, and return it.

        The reflection pass is deterministic and bounded: it inspects only the
        most recent configured turns, extracts small evidence-backed learning
        signals, links relevant memories when retrieval is available, and stores
        the journal locally. If the reflection is stable enough, a compact growth
        summary is also promoted into long-term memory.
        """

        turns = self._normalize_history(conversation_history)
        if not turns:
            raise ValueError(
                "conversation_history must contain at least one non-empty turn."
            )

        query = self._build_reflection_query(turns)
        relevant_memories = self._search_memory_safely(
            query, self._config.max_relevant_reflections
        )
        insights = self._generate_insights(turns, relevant_memories)
        entry = self._build_journal_entry(turns, insights, relevant_memories)
        saved_entry = self.save_journal_entry(entry)
        promoted = self._promote_reflection_to_memory(saved_entry)
        saved_entry["memory_promoted"] = promoted
        if promoted:
            self._rewrite_entry(saved_entry)
        return saved_entry

    def save_journal_entry(self, entry: JournalEntry | dict[str, Any]) -> JournalEntry:
        """Append a journal entry to local JSONL storage and return the saved entry."""

        normalized = self._normalize_entry(entry)
        self._config.journal_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._config.journal_path.open("a", encoding="utf-8") as journal_file:
                journal_file.write(
                    json.dumps(normalized, ensure_ascii=False, sort_keys=True)
                )
                journal_file.write("\n")
        except OSError as exc:
            logger.exception(
                "Failed to save reflection journal entry",
                extra={
                    "journal_path": str(self._config.journal_path),
                    "entry_id": normalized.get("id"),
                },
            )
            raise ReflectionStoreError(
                "Failed to save reflection journal entry."
            ) from exc

        logger.info(
            "Saved reflection journal entry",
            extra={
                "entry_id": normalized["id"],
                "themes": normalized.get("themes", []),
                "confidence": normalized.get("confidence"),
            },
        )
        return normalized

    def get_recent_journal_entries(self, limit: int = 5) -> list[JournalEntry]:
        """Return the newest journal entries, newest first."""

        safe_limit = self._safe_limit(limit, self._config.max_recent_entries)
        entries = self._read_journal_entries()
        return list(reversed(entries[-safe_limit:]))

    def get_relevant_reflections(
        self, query: str
    ) -> list[JournalEntry | MemorySearchResult]:
        """Return journal reflections relevant to a query, with memory fallback.

        Local JSONL overlap search is always attempted. MemoryManager retrieval
        is added when available so reflections promoted into vector memory can be
        found semantically without requiring new API routes.
        """

        normalized_query = self._normalize_text(
            query, field_name="query", max_chars=1_000
        )
        journal_matches = self._rank_journal_entries(normalized_query)
        memory_matches = self._search_memory_safely(
            normalized_query, self._config.max_relevant_reflections
        )
        reflection_memory_matches = [
            memory
            for memory in memory_matches
            if str(memory.get("metadata", {}).get("source")) == "reflection_journal"
            or str(memory.get("metadata", {}).get("memory_type")) == "reflection"
        ]
        return [
            *journal_matches[: self._config.max_relevant_reflections],
            *reflection_memory_matches,
        ]

    def _generate_insights(
        self, turns: list[ReflectionTurn], relevant_memories: list[MemorySearchResult]
    ) -> _InsightSet:
        user_texts = [turn["content"] for turn in turns if turn["role"] == "user"]
        assistant_texts = [
            turn["content"] for turn in turns if turn["role"] == "assistant"
        ]
        all_text = " ".join(turn["content"] for turn in turns)

        boundaries = self._extract_pattern_matches(user_texts, self._BOUNDARY_PATTERNS)
        preferences = [
            preference
            for preference in self._extract_pattern_matches(
                user_texts, self._PREFERENCE_PATTERNS
            )
            if preference not in boundaries
        ]
        themes = self._extract_themes(all_text)
        emotional_valence, emotional_intensity, emotional_cues = self._detect_emotion(
            all_text
        )
        unresolved_questions = self._extract_unresolved_questions(turns)

        observations = []
        if preferences:
            observations.append(
                f"The user showed preference signals around {self._human_join(preferences[:3])}."
            )
        if boundaries:
            observations.append(
                f"The user expressed boundary or avoidance signals around {self._human_join(boundaries[:3])}."
            )
        if emotional_cues:
            observations.append(
                f"The emotional tone leaned {emotional_valence} with cues such as {self._human_join(emotional_cues[:4])}."
            )
        if themes:
            observations.append(
                f"Recurring themes in this window were {self._human_join(themes[:5])}."
            )
        if relevant_memories:
            observations.append(
                f"This reflection connects to {len(relevant_memories)} prior local memory item(s), suggesting continuity rather than an isolated moment."
            )
        if not observations:
            observations.append(
                "The conversation added gentle continuity, but did not contain enough evidence for a major character change."
            )

        growth_edges = []
        if preferences:
            growth_edges.append(
                f"Remember and softly adapt to the user's interest in {self._human_join(preferences[:2])} without overgeneralizing."
            )
        if boundaries:
            growth_edges.append(
                f"Treat {self._human_join(boundaries[:2])} as a caution area until the user clarifies otherwise."
            )
        if emotional_valence != "neutral" and emotional_intensity >= 0.25:
            growth_edges.append(
                f"Carry forward the {emotional_valence} emotional association as context for future tone, not as a permanent fact."
            )
        if unresolved_questions:
            growth_edges.append(
                "Revisit unresolved questions naturally when they become relevant, rather than forcing closure immediately."
            )

        evidence_count = (
            len(preferences)
            + len(boundaries)
            + len(emotional_cues)
            + len(themes)
            + len(relevant_memories)
        )
        if user_texts and assistant_texts:
            evidence_count += 1
        confidence = self._score_confidence(
            evidence_count, len(turns), bool(relevant_memories)
        )

        return _InsightSet(
            observations=observations,
            growth_edges=growth_edges,
            preferences=preferences,
            boundaries=boundaries,
            emotional_cues=emotional_cues,
            unresolved_questions=unresolved_questions,
            themes=themes,
            emotional_valence=emotional_valence,
            emotional_intensity=emotional_intensity,
            confidence=confidence,
            evidence_count=evidence_count,
        )

    def _build_journal_entry(
        self,
        turns: list[ReflectionTurn],
        insights: _InsightSet,
        relevant_memories: list[MemorySearchResult],
    ) -> JournalEntry:
        timestamp = self._utc_now()
        source_turns = turns[-self._config.max_saved_turns :]
        entry_seed = "|".join([timestamp, *(turn["content"] for turn in source_turns)])
        entry_id = f"jrnl_{hashlib.sha256(entry_seed.encode('utf-8')).hexdigest()[:24]}"
        rollback_id = f"rollback_{entry_id}"
        summary = self._character_voice_summary(insights)
        return JournalEntry(
            id=entry_id,
            schema_version="reflection.v1",
            created_at=timestamp,
            conversation_window={
                "start_index": turns[0]["index"],
                "end_index": turns[-1]["index"],
                "turn_count": len(turns),
                "source": "conversation_history",
            },
            source_turns=source_turns,
            linked_memory_ids=[
                memory.get("id", "") for memory in relevant_memories if memory.get("id")
            ],
            character_voice_summary=summary,
            structured_summary={
                "observations": insights.observations,
                "growth_edges": insights.growth_edges,
                "preferences": insights.preferences,
                "boundaries": insights.boundaries,
                "emotional_cues": insights.emotional_cues,
                "unresolved_questions": insights.unresolved_questions,
                "relevant_memory_count": len(relevant_memories),
            },
            emotional_valence=insights.emotional_valence,
            emotional_intensity=insights.emotional_intensity,
            themes=insights.themes,
            confidence=insights.confidence,
            evidence_count=insights.evidence_count,
            privacy_tags=["local_only", "user_visible", "growth_artifact"],
            training_eligible=False,
            training_notes=(
                "Stored as a future LoRA candidate only after explicit user review/approval; "
                "raw turns and reflective interpretations remain separate."
            ),
            rollback_id=rollback_id,
            memory_promoted=False,
        )

    def _character_voice_summary(self, insights: _InsightSet) -> str:
        if insights.growth_edges:
            growth = insights.growth_edges[0]
        else:
            growth = "I should preserve this as context, but avoid treating it as a permanent change yet."
        theme_text = (
            self._human_join(insights.themes[:3])
            if insights.themes
            else "our recent exchange"
        )
        return (
            f"I reflected on {theme_text}. {insights.observations[0]} "
            f"What I want to carry forward: {growth}"
        )

    def _promote_reflection_to_memory(self, entry: JournalEntry) -> bool:
        confidence = float(entry.get("confidence", 0.0))
        evidence_count = int(entry.get("evidence_count", 0))
        growth_edges = entry.get("structured_summary", {}).get("growth_edges", [])
        if (
            confidence < self._config.memory_promotion_min_confidence
            or evidence_count < self._config.memory_promotion_min_evidence
            or not growth_edges
        ):
            return False

        memory_text = (
            "Reflection journal insight: "
            f"{entry.get('character_voice_summary', '')} "
            f"Themes: {self._human_join(entry.get('themes', [])[:5])}."
        )
        try:
            self._memory_manager.add_memory(
                memory_text,
                {
                    "source": "reflection_journal",
                    "memory_type": "reflection",
                    "journal_entry_id": entry.get("id"),
                    "rollback_id": entry.get("rollback_id"),
                    "confidence": confidence,
                    "evidence_count": evidence_count,
                    "training_eligible": entry.get("training_eligible", False),
                    "privacy_tags": entry.get("privacy_tags", []),
                    "user_id": self._config.user_id,
                },
            )
        except MemoryError as exc:
            logger.warning(
                "Reflection was journaled but not promoted to memory",
                extra={"entry_id": entry.get("id"), "error": str(exc)},
            )
            return False
        except (
            Exception
        ) as exc:  # pragma: no cover - defensive against storage backends.
            logger.warning(
                "Unexpected failure while promoting reflection to memory",
                extra={"entry_id": entry.get("id"), "error": str(exc)},
            )
            return False
        return True

    def _normalize_history(
        self, conversation_history: Iterable[Any]
    ) -> list[ReflectionTurn]:
        turns: list[ReflectionTurn] = []
        for index, raw_turn in enumerate(conversation_history):
            role = self._read_turn_value(raw_turn, "role") or "unknown"
            content = self._read_turn_value(
                raw_turn, "content"
            ) or self._read_turn_value(raw_turn, "message")
            if not isinstance(content, str) or not content.strip():
                continue
            normalized_role = str(role).strip().lower() or "unknown"
            turns.append(
                ReflectionTurn(
                    role=normalized_role,
                    content=self._normalize_text(
                        content, max_chars=self._config.max_turn_chars
                    ),
                    index=index,
                )
            )
        return turns[-self._config.max_history_turns :]

    def _normalize_entry(self, entry: JournalEntry | dict[str, Any]) -> JournalEntry:
        if not isinstance(entry, dict):
            raise ValueError("entry must be a dictionary-like journal entry.")
        now = self._utc_now()
        normalized = dict(entry)
        normalized.setdefault(
            "id",
            f"jrnl_{hashlib.sha256(json.dumps(normalized, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:24]}",
        )
        normalized.setdefault("schema_version", "reflection.v1")
        normalized.setdefault("created_at", now)
        normalized.setdefault("conversation_window", {"source": "manual"})
        normalized.setdefault("source_turns", [])
        normalized.setdefault("linked_memory_ids", [])
        normalized.setdefault(
            "character_voice_summary", "I recorded a quiet reflection for continuity."
        )
        normalized.setdefault("structured_summary", {})
        normalized.setdefault("emotional_valence", "neutral")
        normalized.setdefault("emotional_intensity", 0.0)
        normalized.setdefault("themes", [])
        normalized.setdefault("confidence", 0.0)
        normalized.setdefault("evidence_count", 0)
        normalized.setdefault(
            "privacy_tags", ["local_only", "user_visible", "growth_artifact"]
        )
        normalized.setdefault("training_eligible", False)
        normalized.setdefault(
            "training_notes", "Requires explicit user review before training use."
        )
        normalized.setdefault("rollback_id", f"rollback_{normalized['id']}")
        normalized.setdefault("memory_promoted", False)
        return JournalEntry(**normalized)

    def _read_journal_entries(self) -> list[JournalEntry]:
        if not self._config.journal_path.exists():
            return []
        entries: list[JournalEntry] = []
        try:
            with self._config.journal_path.open("r", encoding="utf-8") as journal_file:
                for line in journal_file:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        decoded = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed reflection journal line")
                        continue
                    if isinstance(decoded, dict):
                        entries.append(self._normalize_entry(decoded))
        except OSError as exc:
            logger.exception(
                "Failed to read reflection journal",
                extra={"journal_path": str(self._config.journal_path)},
            )
            raise ReflectionStoreError("Failed to read reflection journal.") from exc
        return entries

    def _rewrite_entry(self, updated_entry: JournalEntry) -> None:
        entries = self._read_journal_entries()
        replaced = False
        for index, entry in enumerate(entries):
            if entry.get("id") == updated_entry.get("id"):
                entries[index] = updated_entry
                replaced = True
                break
        if not replaced:
            entries.append(updated_entry)
        try:
            with self._config.journal_path.open("w", encoding="utf-8") as journal_file:
                for entry in entries:
                    journal_file.write(
                        json.dumps(entry, ensure_ascii=False, sort_keys=True)
                    )
                    journal_file.write("\n")
        except OSError as exc:
            logger.warning(
                "Failed to update reflection promotion status; journal entry remains usable",
                extra={"entry_id": updated_entry.get("id"), "error": str(exc)},
            )

    def _rank_journal_entries(self, query: str) -> list[JournalEntry]:
        query_terms = set(self._tokenize(query))
        if not query_terms:
            return []
        scored: list[tuple[float, JournalEntry]] = []
        for entry in self._read_journal_entries():
            searchable_text = " ".join(
                [
                    str(entry.get("character_voice_summary", "")),
                    " ".join(str(theme) for theme in entry.get("themes", [])),
                    json.dumps(entry.get("structured_summary", {}), ensure_ascii=False),
                ]
            )
            entry_terms = set(self._tokenize(searchable_text))
            if not entry_terms:
                continue
            score = len(query_terms & entry_terms) / len(query_terms | entry_terms)
            if score >= self._config.local_relevance_min_score:
                entry["local_relevance_score"] = round(score, 4)
                scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored]

    def _search_memory_safely(self, query: str, limit: int) -> list[MemorySearchResult]:
        if not query.strip():
            return []
        try:
            return self._memory_manager.search_memories(query, limit=limit)
        except (MemoryError, ValueError) as exc:
            logger.debug("Reflection memory lookup skipped", extra={"error": str(exc)})
            return []
        except Exception as exc:  # pragma: no cover - defensive against backend drift.
            logger.warning("Reflection memory lookup failed", extra={"error": str(exc)})
            return []

    def _extract_pattern_matches(
        self, texts: list[str], patterns: tuple[re.Pattern[str], ...]
    ) -> list[str]:
        matches: list[str] = []
        for text in texts:
            for pattern in patterns:
                for match in pattern.findall(text):
                    cleaned = self._clean_fragment(match)
                    if cleaned and cleaned not in matches:
                        matches.append(cleaned)
        return matches[:6]

    def _extract_themes(self, text: str) -> list[str]:
        counts = Counter(self._tokenize(text))
        return [word for word, _ in counts.most_common(8)]

    def _detect_emotion(self, text: str) -> tuple[str, float, list[str]]:
        tokens = self._tokenize(text)
        positive = [token for token in tokens if token in self._POSITIVE_WORDS]
        negative = [token for token in tokens if token in self._NEGATIVE_WORDS]
        total_hits = len(positive) + len(negative)
        if total_hits == 0:
            return "neutral", 0.0, []
        if len(positive) > len(negative):
            valence = "positive"
            cues = list(dict.fromkeys(positive))
        elif len(negative) > len(positive):
            valence = "negative"
            cues = list(dict.fromkeys(negative))
        else:
            valence = "mixed"
            cues = list(dict.fromkeys([*positive, *negative]))
        intensity = min(1.0, round(total_hits / max(len(tokens), 1) * 8, 3))
        return valence, intensity, cues[:8]

    def _extract_unresolved_questions(self, turns: list[ReflectionTurn]) -> list[str]:
        questions = [turn["content"] for turn in turns if "?" in turn["content"]]
        if not questions:
            return []
        if turns[-1]["role"] == "user" and "?" in turns[-1]["content"]:
            return [self._normalize_text(turns[-1]["content"], max_chars=240)]
        return [
            self._normalize_text(question, max_chars=240) for question in questions[-2:]
        ]

    def _build_reflection_query(self, turns: list[ReflectionTurn]) -> str:
        user_turns = [turn["content"] for turn in turns if turn["role"] == "user"]
        if user_turns:
            return self._normalize_text(" ".join(user_turns[-4:]), max_chars=1_500)
        return self._normalize_text(
            " ".join(turn["content"] for turn in turns[-4:]), max_chars=1_500
        )

    def _tokenize(self, text: str) -> list[str]:
        return [
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z']{2,}", text.lower())
            if token not in self._STOPWORDS
        ]

    def _score_confidence(
        self, evidence_count: int, turn_count: int, has_memory_links: bool
    ) -> float:
        base = min(0.7, evidence_count * 0.08)
        if turn_count >= 4:
            base += 0.1
        if has_memory_links:
            base += 0.15
        return round(min(base, 0.95), 3)

    def _read_turn_value(self, raw_turn: Any, key: str) -> Any:
        if isinstance(raw_turn, dict):
            return raw_turn.get(key)
        return getattr(raw_turn, key, None)

    def _normalize_text(
        self, text: str, *, field_name: str = "text", max_chars: int | None = None
    ) -> str:
        if not isinstance(text, str):
            raise ValueError(f"{field_name} must be a string.")
        normalized = " ".join(text.strip().split())
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty.")
        char_limit = max_chars or self._config.max_turn_chars
        if len(normalized) > char_limit:
            normalized = normalized[:char_limit].rstrip()
        return normalized

    def _clean_fragment(self, fragment: str) -> str:
        cleaned = self._normalize_text(fragment, max_chars=160).strip(" ,;:-")
        return cleaned.lower()

    def _safe_limit(self, limit: int, maximum: int) -> int:
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")
        return min(limit, maximum)

    def _human_join(self, values: list[str]) -> str:
        clean_values = [str(value) for value in values if str(value).strip()]
        if not clean_values:
            return "nothing specific yet"
        if len(clean_values) == 1:
            return clean_values[0]
        if len(clean_values) == 2:
            return f"{clean_values[0]} and {clean_values[1]}"
        return f"{', '.join(clean_values[:-1])}, and {clean_values[-1]}"

    def _utc_now(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")


class ReflectionError(Exception):
    """Base exception for reflection and journal failures."""


class ReflectionStoreError(ReflectionError):
    """Raised when journal storage cannot be read or written."""


_reflection_manager: ReflectionManager | None = None


def get_reflection_manager() -> ReflectionManager:
    """Return a process-local reflection manager singleton for future API wiring."""

    global _reflection_manager
    if _reflection_manager is None:
        _reflection_manager = ReflectionManager()
    return _reflection_manager


__all__ = [
    "JournalEntry",
    "ReflectionError",
    "ReflectionManager",
    "ReflectionManagerConfig",
    "ReflectionStoreError",
    "ReflectionTurn",
    "get_reflection_manager",
]
