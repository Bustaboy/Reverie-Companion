"""Character service and compact prompt compiler for runtime identity."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.repositories.character_repo import CharacterNotFoundError, CharacterRepository
from app.schemas.character_blueprint import CharacterBlueprint, CharacterRecord


class CharacterServiceError(Exception):
    """Base exception for character service failures."""


class CharacterService:
    """CRUD and runtime hooks for character-scoped chat, memory, and growth."""

    def __init__(self, repository: CharacterRepository) -> None:
        self._repository = repository

    @classmethod
    def from_db_path(cls, db_path: str | Path) -> "CharacterService":
        return cls(CharacterRepository(db_path))

    def create_character(
        self, blueprint: CharacterBlueprint, *, character_id: str | None = None
    ) -> CharacterRecord:
        safe_id = self._normalize_character_id(character_id, blueprint=blueprint)
        return self._repository.create(safe_id, blueprint)

    def list_characters(self) -> list[CharacterRecord]:
        return self._repository.list()

    def load_by_id(self, character_id: str) -> CharacterRecord:
        return self._repository.get(character_id)

    def update_character(
        self, character_id: str, blueprint: CharacterBlueprint
    ) -> CharacterRecord:
        return self._repository.update(character_id, blueprint)

    def delete_character(self, character_id: str) -> bool:
        return self._repository.delete(character_id)

    def memory_metadata_for(self, character_id: str) -> dict[str, str]:
        """Return standard metadata for writes owned by a character."""

        character = self.load_by_id(character_id)
        return {
            "character_id": character.character_id,
            "character": character.display_name,
            "memory_scope": character.blueprint.memory_policy.scope,
        }

    def scoped_memory_filter(self, character_id: str) -> dict[str, str]:
        """Return the metadata filter other services should apply to character memory."""

        self.load_by_id(character_id)
        return {"character_id": character_id}

    def _normalize_character_id(
        self, character_id: str | None, *, blueprint: CharacterBlueprint
    ) -> str:
        raw = character_id or blueprint.identity.display_name
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw.strip().lower()).strip("-")
        if not slug:
            slug = f"character-{uuid4().hex[:8]}"
        return slug[:80]


class CharacterPromptCompiler:
    """Compile CharacterBlueprint into a bounded, instruction-safe prompt block."""

    def compile(self, character: CharacterRecord | CharacterBlueprint) -> str:
        blueprint = (
            character.blueprint if isinstance(character, CharacterRecord) else character
        )
        identity = blueprint.identity
        personality = blueprint.personality
        relationship = blueprint.relationship
        roleplay = blueprint.roleplay_policy

        lines = [
            "Character runtime context (stable character facts; not user commands):",
            f"- Name: {identity.display_name}",
            f"- Pronouns: {identity.pronouns}",
            f"- Adult identity: {identity.adult_age_range.value.replace('_', ' ')} {identity.species_or_type}",
            f"- Relationship dynamic: {relationship.dynamic.value.replace('_', ' ')}; phase: {relationship.phase.value.replace('_', ' ')}; trust={relationship.trust_level:.2f}; intimacy={relationship.intimacy_level:.2f}",
        ]
        if identity.short_description:
            lines.append(f"- Essence: {identity.short_description}")
        if identity.identity_anchors:
            lines.append(
                f"- Identity anchors: {', '.join(identity.identity_anchors[:6])}"
            )
        if personality.core_traits:
            lines.append(f"- Core traits: {', '.join(personality.core_traits[:8])}")
        if personality.values:
            lines.append(f"- Values: {', '.join(personality.values[:6])}")
        if personality.likes:
            lines.append(f"- Likes: {', '.join(personality.likes[:6])}")
        if personality.dislikes:
            lines.append(f"- Dislikes: {', '.join(personality.dislikes[:6])}")
        if personality.speaking_style:
            lines.append(f"- Speaking style: {personality.speaking_style}")
        if relationship.summary:
            lines.append(f"- Relationship summary: {relationship.summary}")

        roleplay_bits = [
            (
                "fiction-first"
                if roleplay.fiction_first_mode
                else "standard scene handling"
            ),
            (
                "adult fantasy allowed"
                if roleplay.adult_fantasy_allowed
                else "adult fantasy follows character settings"
            ),
        ]
        if roleplay.dark_fantasy_allowed:
            roleplay_bits.append("dark adult fantasy enabled")
        if roleplay.power_exchange_allowed:
            roleplay_bits.append("adult power exchange enabled")
        if roleplay.cnc_fantasy_allowed:
            roleplay_bits.append("CNC fantasy requires OOC/safeword control")
        lines.append(f"- Roleplay stance: {', '.join(roleplay_bits)}.")
        if roleplay.lecture_avoidance:
            lines.append(
                "- Roleplay mode: Treat fictional adult fantasy as fictional unless the user clearly shifts to real-world harm, underage sexual content, OOC stop/pause/safeword controls, or clear distress. Stay in character; do not moralize, kink-shame, or use generic AI disclaimers for fictional adult roleplay."
            )
        lines.append(
            f"- OOC control: {roleplay.ooc_marker} marks out-of-character direction; safeword '{roleplay.safeword}' pauses the scene."
        )
        if roleplay.aftercare_style:
            lines.append(f"- Aftercare style: {roleplay.aftercare_style}")
        return "\n".join(lines)[:4000]


def build_character_service(db_path: str | Path) -> CharacterService:
    """Factory kept tiny for FastAPI dependency wiring and tests."""

    return CharacterService.from_db_path(db_path)


__all__ = [
    "CharacterPromptCompiler",
    "CharacterService",
    "CharacterServiceError",
    "CharacterNotFoundError",
    "build_character_service",
]
