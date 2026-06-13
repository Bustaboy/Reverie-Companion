"""Visual prompt compiler for Moment Capture.

Builds compact, reviewable positive/negative image prompt bundles from the
selected character's VisualIdentityProfile plus temporary scene/capture context.
It does not submit generation jobs, write canon, or expose raw blueprint JSON.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.character_blueprint import CharacterBlueprint
from app.schemas.visual_identity import VisualIdentityProfile


class VisualPromptBundle(BaseModel):
    """Bounded prompt data passed to image-generation orchestration."""

    positive_prompt: str = Field(..., min_length=1, max_length=2_400)
    negative_prompt: str = Field(..., min_length=1, max_length=1_200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualPromptCompiler:
    """Compile character visual canon and scene state into image prompts.

    The compiler mirrors CharacterPromptCompiler's contract: deterministic,
    bounded, strongly typed, subordinate to callers, and built from selected
    schema fields rather than private notes or raw CharacterBlueprint dumps.
    """

    MAX_FIELD_CHARS = 180
    MAX_SECTION_CHARS = 420
    MAX_POSITIVE_CHARS = 2_400
    MAX_NEGATIVE_CHARS = 1_200
    MAX_LIST_ITEMS = 6

    BASE_QUALITY = (
        "high quality character illustration, consistent character design, "
        "emotionally coherent visual novel moment, polished lighting, tasteful composition"
    )
    IDENTITY_DRIFT_NEGATIVE = (
        "different person, identity drift, changed facial structure, inconsistent canonical hair, "
        "inconsistent canonical eyes, off-model character, duplicate character identity"
    )
    ADULT_NEGATIVE = (
        "underage presentation, childlike face, child body proportions, teen appearance, "
        "schoolchild styling, deliberately childlike sexual presentation"
    )
    USER_FACE_NEGATIVE = "user face visible, viewer face visible, detailed face of the user, front-facing user portrait"

    def compile_bundle(
        self,
        blueprint: CharacterBlueprint | None = None,
        *,
        visual_identity: VisualIdentityProfile | None = None,
        scene_state: dict[str, Any] | None = None,
        user_capture_instruction: str,
        wrong_appearance_traits: list[str] | None = None,
        include_user_face: bool = False,
    ) -> VisualPromptBundle:
        """Return a deterministic visual prompt bundle for Moment Capture."""

        if blueprint is None and visual_identity is None:
            raise ValueError(
                "A CharacterBlueprint or VisualIdentityProfile is required."
            )
        profile = visual_identity or blueprint.visual_identity  # type: ignore[union-attr]
        scene_state = scene_state or {}
        character_id = blueprint.character_id if blueprint else None

        anchors = self._clean_list(profile.identity_anchors)
        rejected = self._clean_list(profile.rejected_traits)
        wrong = self._clean_list(
            wrong_appearance_traits
            or self._list_from_scene(
                scene_state, "wrong_appearance", "confirmed_wrong_appearance"
            )
        )
        scene_mutable = self._clean_list(
            profile.scene_mutable_traits + self._scene_mutable_traits(scene_state)
        )

        positive_sections = [
            self._section("Adult identity baseline", [self._adult_baseline(profile)]),
            self._section("Selected character", self._character_lines(blueprint)),
            self._section(
                "Identity anchors",
                anchors or ["Preserve established recognizable character identity."],
            ),
            self._section("Appearance canon", self._appearance_lines(profile)),
            self._section("Scene-mutable presentation", scene_mutable),
            self._section(
                "Emotional / relationship tone",
                self._tone_lines(blueprint, scene_state, user_capture_instruction),
            ),
            self._section("User capture instruction", [user_capture_instruction]),
            self.BASE_QUALITY,
        ]
        positive = self._bound(
            "\n".join(s for s in positive_sections if s), self.MAX_POSITIVE_CHARS
        )
        positive = self._remove_forbidden_positive_terms(positive, rejected + wrong)

        negative_sections = [
            self._section("Rejected visual traits", rejected),
            self._section("User-confirmed wrong appearance", wrong),
            self._section("Identity drift prevention", [self.IDENTITY_DRIFT_NEGATIVE]),
            self._section("Adult-only presentation exclusions", [self.ADULT_NEGATIVE]),
        ]
        if not include_user_face:
            negative_sections.append(
                self._section("User face visibility", [self.USER_FACE_NEGATIVE])
            )
        negative = self._bound(
            "\n".join(s for s in negative_sections if s), self.MAX_NEGATIVE_CHARS
        )

        scene_summary = self._scene_summary(scene_state)
        hash_payload = {
            "positive_prompt": positive,
            "negative_prompt": negative,
            "character_id": character_id,
            "scene_state_summary": scene_summary,
            "identity_anchors_used": anchors,
            "rejected_traits_excluded": rejected,
            "wrong_appearance_excluded": wrong,
        }
        prompt_hash = hashlib.sha256(
            json.dumps(hash_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]

        return VisualPromptBundle(
            positive_prompt=positive,
            negative_prompt=negative,
            metadata={
                "prompt_hash": prompt_hash,
                "identity_anchors_used": anchors,
                "rejected_traits_excluded": rejected,
                "wrong_appearance_excluded": wrong,
                "character_id": character_id,
                "scene_state_summary": scene_summary,
            },
        )

    def _adult_baseline(self, profile: VisualIdentityProfile) -> str:
        policy = profile.adult_only_policy
        return f"clearly adult {policy.adult_age_range}; adult presentation without underage or deliberately childlike styling"

    def _character_lines(self, blueprint: CharacterBlueprint | None) -> list[str]:
        if not blueprint:
            return []
        identity = blueprint.identity
        return [
            f"{identity.display_name} as the selected main character",
            f"pronouns {identity.pronouns}",
            f"species/type {identity.species_or_type}",
        ]

    def _appearance_lines(self, profile: VisualIdentityProfile) -> list[str]:
        lines = []
        if profile.current_appearance:
            lines.append(f"current appearance: {profile.current_appearance}")
        lines.extend(
            trait.prompt_fragment()
            for trait in profile.evolving_traits[: self.MAX_LIST_ITEMS]
        )
        return lines

    def _tone_lines(
        self,
        blueprint: CharacterBlueprint | None,
        scene: dict[str, Any],
        instruction: str,
    ) -> list[str]:
        keys = ("mood", "emotion", "relationship_tone", "scene_mood", "atmosphere")
        lines = [
            self._clip(str(scene[k])) for k in keys if isinstance(scene.get(k), str)
        ]
        if blueprint and any(
            word in instruction.casefold()
            for word in ("kiss", "embrace", "together", "date", "intimate", "romantic")
        ):
            lines.append(blueprint.relationship.prompt_summary())
        return lines[: self.MAX_LIST_ITEMS]

    def _scene_mutable_traits(self, scene: dict[str, Any]) -> list[str]:
        traits: list[str] = []
        for key in (
            "outfit",
            "pose",
            "expression",
            "lighting",
            "camera",
            "setting",
            "background",
            "props",
        ):
            value = scene.get(key)
            if isinstance(value, str):
                traits.append(f"{key}: {value}")
            elif isinstance(value, list):
                traits.extend(
                    f"{key}: {item}" for item in value if isinstance(item, str)
                )
        traits.extend(
            self._list_from_scene(scene, "scene_mutable_traits", "temporary_traits")
        )
        return traits

    def _list_from_scene(self, scene: dict[str, Any], *keys: str) -> list[str]:
        found: list[str] = []
        for key in keys:
            value = scene.get(key)
            if isinstance(value, list):
                found.extend(str(item) for item in value)
            elif isinstance(value, str):
                found.append(value)
        return found

    def _scene_summary(self, scene: dict[str, Any]) -> str:
        parts = []
        for key in (
            "setting",
            "background",
            "mood",
            "emotion",
            "pose",
            "expression",
            "lighting",
        ):
            if isinstance(scene.get(key), str):
                parts.append(f"{key}={self._clip(str(scene[key]), 80)}")
        return self._clip("; ".join(parts) or "no explicit scene state", 360)

    def _section(self, title: str, lines: list[str]) -> str:
        cleaned = self._clean_list(lines)
        if not cleaned:
            return ""
        body = "; ".join(cleaned[: self.MAX_LIST_ITEMS])
        return self._bound(f"{title}: {body}.", self.MAX_SECTION_CHARS)

    def _clean_list(self, values: list[str]) -> list[str]:
        out: list[str] = []
        for value in values[: self.MAX_LIST_ITEMS * 2]:
            item = self._clip(value)
            if item and item not in out:
                out.append(item)
        return out[: self.MAX_LIST_ITEMS]

    def _remove_forbidden_positive_terms(
        self, prompt: str, forbidden: list[str]
    ) -> str:
        for term in forbidden:
            if term and term.casefold() in prompt.casefold():
                prompt = prompt.replace(term, "[excluded rejected visual trait]")
        return prompt

    def _clip(self, value: str, chars: int | None = None) -> str:
        normalized = " ".join(str(value).strip().split())
        limit = chars or self.MAX_FIELD_CHARS
        return (
            normalized
            if len(normalized) <= limit
            else normalized[: limit - 1].rstrip() + "…"
        )

    def _bound(self, block: str, chars: int) -> str:
        return block if len(block) <= chars else block[: chars - 1].rstrip() + "…"
