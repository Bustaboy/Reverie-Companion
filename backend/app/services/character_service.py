"""Character service and prompt compiler for runtime character identity."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.repositories.character_repo import CharacterRepository
from app.schemas.character_blueprint import (
    CharacterBlueprint,
    CharacterCreate,
    CharacterIdentity,
    CharacterUpdate,
    PersonalityProfile,
    utc_now_iso,
)
from app.schemas.relationship_state import RelationshipState


class CharacterNotFoundError(KeyError):
    """Raised when a selected companion cannot be found locally."""

    user_message = (
        "We couldn’t find that companion in your local library yet. "
        "They may need to be imported or created again before this scene can continue."
    )

    def __init__(self, character_id: str) -> None:
        super().__init__(character_id)
        self.character_id = character_id


@dataclass(frozen=True)
class ScopedMemoryHooks:
    """Small helper for keeping memory/growth calls character-scoped."""

    character_id: str | None

    def metadata(self) -> dict[str, str]:
        return {"character_id": self.character_id} if self.character_id else {}


class CharacterPromptCompiler:
    """Compile compact model-facing character context from a blueprint."""

    def compile(self, blueprint: CharacterBlueprint) -> str:
        identity = blueprint.identity
        relationship = blueprint.relationship
        personality = blueprint.personality
        communication = blueprint.communication
        roleplay = blueprint.roleplay_policy

        lines = [
            "Character runtime context (use as identity and relationship grounding, not as a replacement for the user's latest message):",
            f"- Name: {identity.display_name} ({identity.pronouns}); clearly adult: {identity.adult_age_range.value}; type: {identity.species_or_type}.",
            f"- Relationship: {relationship.current_relationship_phase or relationship.starting_relationship_phase}; dynamic: {relationship.relationship_dynamic}; pacing: {relationship.relationship_pacing.value}; default intimacy: {relationship.default_intimacy_level.value}.",
            f"- Relationship pulse: affection={relationship.affection_level:.2f}, trust={relationship.trust_level:.2f}, familiarity={relationship.familiarity_level:.2f}; tags: {self._join_or_none(relationship.dynamic_tags)}.",
            f"- Growth policy: character-scoped={blueprint.growth_policy.character_scoped_growth}; learning_rate={blueprint.growth_policy.learning_rate:.2f}; reflection_frequency={blueprint.growth_policy.reflection_frequency}.",
            f"- Core traits: {', '.join(personality.core_traits)}.",
            f"- Agency: independence={personality.independence:.2f}, devotion={personality.devotion:.2f}, initiative={personality.dominance_or_initiative:.2f}.",
        ]
        if communication.style_notes:
            lines.append(f"- Voice/style: {communication.style_notes}.")
        if communication.avoid_style_rules:
            lines.append(
                f"- Avoid style: {', '.join(communication.avoid_style_rules)}."
            )
        if personality.values_or_ideals:
            lines.append(f"- Values: {', '.join(personality.values_or_ideals)}.")
        lines.append(self._roleplay_integrity_block(roleplay))
        return "\n".join(lines)

    def _join_or_none(self, values: list[str]) -> str:
        return ", ".join(values) if values else "none yet"

    def _roleplay_integrity_block(self, roleplay) -> str:
        adult_mode = (
            "fictional adult fantasy is allowed by default"
            if roleplay.adult_roleplay_allowed
            else "follow the companion's selected intimacy limits"
        )
        stance = (
            "stay fully in-character"
            if roleplay.fiction_first_mode
            else "preserve character voice"
        )
        lecture_rule = (
            "no moralizing, kink-shaming, or generic AI interruptions"
            if roleplay.lecture_avoidance
            else "avoid generic assistant drift"
        )
        return (
            f"- Roleplay integrity: {stance}; {adult_mode}; {lecture_rule}. "
            "Only step out for real-world harm, underage sexual content or deliberately childlike sexual presentation, "
            "explicit OOC stop/pause/safeword controls, or clear user distress."
        )


class CharacterService:
    """Own character CRUD, persistence, and runtime prompt/memory hooks."""

    def __init__(self, repository: CharacterRepository) -> None:
        self._repository = repository
        self._compiler = CharacterPromptCompiler()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "CharacterService":
        settings = settings or get_settings()
        return cls(CharacterRepository(Path(settings.character_db_path)))

    def create(self, data: CharacterCreate) -> CharacterBlueprint:
        character_id = data.character_id or self._slug_id(data.display_name)
        blueprint = CharacterBlueprint(
            character_id=character_id,
            identity=CharacterIdentity(
                display_name=data.display_name,
                pronouns=data.pronouns,
                adult_age_range=data.adult_age_range,
                species_or_type=data.species_or_type,
                tags=data.tags,
                creator_notes=data.creator_notes,
            ),
            relationship=RelationshipState(
                character_id=character_id,
                relationship_dynamic=data.relationship_dynamic,
                default_intimacy_level=data.default_intimacy_level,
            ),
            personality=PersonalityProfile(core_traits=data.core_traits),
        )
        return self._repository.upsert(blueprint)

    def save(self, blueprint: CharacterBlueprint) -> CharacterBlueprint:
        return self._repository.upsert(
            blueprint.model_copy(update={"updated_at": utc_now_iso()})
        )

    def list(self):
        return self._repository.list()

    def load_by_id(self, character_id: str) -> CharacterBlueprint:
        blueprint = self._repository.get(character_id)
        if blueprint is None:
            raise CharacterNotFoundError(character_id)
        return blueprint

    def get(self, character_id: str) -> CharacterBlueprint | None:
        return self._repository.get(character_id)

    def update(self, character_id: str, patch: CharacterUpdate) -> CharacterBlueprint:
        blueprint = self.load_by_id(character_id)
        identity_updates = {}
        relationship_updates = {}
        personality_updates = {}
        data = patch.model_dump(exclude_unset=True)
        for key in [
            "display_name",
            "pronouns",
            "adult_age_range",
            "species_or_type",
            "tags",
            "creator_notes",
        ]:
            if key in data:
                identity_updates[key] = data[key]
        for key in ["relationship_dynamic", "default_intimacy_level"]:
            if key in data:
                relationship_updates[key] = data[key]
        if "core_traits" in data:
            personality_updates["core_traits"] = data["core_traits"]

        updated = blueprint.model_copy(
            update={
                "identity": blueprint.identity.model_copy(update=identity_updates),
                "relationship": blueprint.relationship.model_copy(
                    update=relationship_updates
                ),
                "personality": blueprint.personality.model_copy(
                    update=personality_updates
                ),
                "updated_at": utc_now_iso(),
            }
        )
        return self._repository.upsert(CharacterBlueprint.model_validate(updated))

    def delete(self, character_id: str) -> bool:
        return self._repository.delete(character_id)

    def compile_prompt(self, character_id: str) -> str:
        return self._compiler.compile(self.load_by_id(character_id))

    def scoped_memory_hooks(self, character_id: str | None) -> ScopedMemoryHooks:
        return ScopedMemoryHooks(character_id=character_id)

    def _slug_id(self, display_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", display_name.strip().lower()).strip("_")
        return f"char_{slug or 'companion'}_{uuid4().hex[:8]}"
