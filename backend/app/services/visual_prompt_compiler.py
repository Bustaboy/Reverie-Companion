"""Visual prompt compiler for Moment Capture image prompt bundles.

This compiler is intentionally deterministic and lightweight. It consumes the
selected character's ``VisualIdentityProfile`` plus compact scene/user intent
metadata and returns bounded positive/negative prompt text. It does not submit
image jobs and it never writes canon.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.character_blueprint import CharacterBlueprint
from app.schemas.visual_identity import VisualIdentityProfile


class VisualPromptBundle(BaseModel):
    """Prompt data passed to image generation adapters."""

    positive_prompt: str = Field(..., min_length=1, max_length=2_200)
    negative_prompt: str = Field(..., min_length=1, max_length=1_200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualPromptCompiler:
    """Compile bounded visual prompts from the visual identity source of truth."""

    MAX_FIELD_CHARS = 180
    MAX_LIST_ITEMS = 6
    MAX_POSITIVE_CHARS = 2_200
    MAX_NEGATIVE_CHARS = 1_200
    _SCENE_MUTABLE_WORDS = {
        "outfit",
        "clothes",
        "clothing",
        "dress",
        "shirt",
        "pose",
        "expression",
        "smile",
        "lighting",
        "background",
        "location",
        "camera",
        "angle",
        "makeup",
    }
    _USER_FACE_TERMS = ("show my face", "user face", "viewer face", "my face visible")

    def compile(
        self,
        *,
        visual_identity: VisualIdentityProfile | None = None,
        character: CharacterBlueprint | None = None,
        character_id: str | None = None,
        scene_state: dict[str, Any] | None = None,
        capture_intent: str = "capture this moment",
        relationship_context: str | None = None,
        emotional_tone: str | None = None,
    ) -> VisualPromptBundle:
        """Return a prompt bundle without mutating character canon or queueing jobs."""

        if character is not None:
            visual_identity = visual_identity or character.visual_identity
            character_id = character_id or character.character_id
            relationship_context = (
                relationship_context or character.relationship.prompt_summary()
            )
        if visual_identity is None:
            visual_identity = VisualIdentityProfile()

        scene_state = scene_state or {}
        anchors = self._identity_anchors(visual_identity)
        rejected = self._clean_list(visual_identity.rejected_traits)
        wrong = self._clean_list(
            self._list_from_mapping(
                scene_state,
                "wrong_appearance",
                "wrong_traits",
                "user_confirmed_wrong_appearance",
            )
        )
        scene_mutable = self._scene_mutable_traits(visual_identity, scene_state)

        positive_sections = [
            self._section(
                "Adult-only identity baseline",
                [
                    f"clearly adult {visual_identity.adult_only_policy.adult_age_range} character",
                    self._clip(visual_identity.adult_only_policy.adult_baseline_note),
                    "adult proportions and adult presence without forcing one body type or style",
                ],
            ),
            self._section("Identity anchors", anchors),
            self._section(
                "Current appearance canon", self._appearance_lines(visual_identity)
            ),
            self._section("Scene-mutable details", scene_mutable),
            self._section(
                "Tone",
                self._tone_lines(relationship_context, emotional_tone, capture_intent),
            ),
            self._section("User capture instruction", [capture_intent]),
            "high quality character illustration, consistent face and body identity, coherent lighting",
        ]
        negative_sections = [
            self._section("Rejected visual traits", rejected),
            self._section("User-confirmed wrong appearance", wrong),
            self._section(
                "Identity drift prevention",
                [
                    "different person",
                    "changed face",
                    "wrong eye color",
                    "wrong skin tone",
                    "unintended species/body baseline change",
                    "lost permanent marks or signature anchors",
                ],
            ),
            self._section(
                "Adult presentation exclusions",
                [
                    "underage presentation",
                    "childlike proportions",
                    "minor-coded appearance",
                    "preteen or teen look",
                    "deliberately childlike sexual presentation",
                ],
            ),
        ]
        if not self._explicit_user_face_requested(capture_intent, scene_state):
            negative_sections.append(
                self._section(
                    "User face visibility",
                    [
                        "user face visible",
                        "viewer face visible",
                        "front-facing user portrait",
                        "detailed face of the user",
                    ],
                )
            )

        positive = self._bound(
            self._join_sections(positive_sections), self.MAX_POSITIVE_CHARS
        )
        negative = self._bound(
            self._join_sections(negative_sections), self.MAX_NEGATIVE_CHARS
        )
        scene_state_summary = self._scene_summary(scene_state)
        canonical = {
            "positive_prompt": positive,
            "negative_prompt": negative,
            "character_id": character_id,
            "scene_state_summary": scene_state_summary,
            "identity_anchors_used": anchors,
            "rejected_traits_excluded": rejected,
            "wrong_appearance_excluded": wrong,
        }
        prompt_hash = self._prompt_hash(canonical)
        return VisualPromptBundle(
            positive_prompt=positive,
            negative_prompt=negative,
            metadata={
                "prompt_hash": prompt_hash,
                "identity_anchors_used": anchors,
                "rejected_traits_excluded": rejected,
                "wrong_appearance_excluded": wrong,
                "character_id": character_id,
                "scene_state_summary": scene_state_summary,
            },
        )

    def _identity_anchors(self, profile: VisualIdentityProfile) -> list[str]:
        anchors = []
        for anchor in self._clean_list(profile.identity_anchors):
            lowered = anchor.casefold()
            if any(word in lowered for word in self._SCENE_MUTABLE_WORDS):
                continue
            anchors.append(anchor)
        return anchors[: self.MAX_LIST_ITEMS]

    def _appearance_lines(self, profile: VisualIdentityProfile) -> list[str]:
        lines: list[str] = []
        if profile.current_appearance:
            lines.append(profile.current_appearance)
        lines.extend(
            trait.prompt_fragment()
            for trait in profile.evolving_traits[: self.MAX_LIST_ITEMS]
        )
        return self._clean_list(lines)

    def _scene_mutable_traits(
        self, profile: VisualIdentityProfile, scene_state: dict[str, Any]
    ) -> list[str]:
        values = list(profile.scene_mutable_traits)
        values.extend(
            self._list_from_mapping(
                scene_state,
                "outfit",
                "pose",
                "expression",
                "lighting",
                "location",
                "camera",
                "props",
            )
        )
        return self._clean_list(values)

    def _tone_lines(
        self, relationship: str | None, emotion: str | None, intent: str
    ) -> list[str]:
        if (
            not any(
                term in intent.casefold()
                for term in (
                    "romantic",
                    "tender",
                    "close",
                    "kiss",
                    "intimate",
                    "emotional",
                )
            )
            and not emotion
        ):
            return []
        return self._clean_list([relationship or "", emotion or ""])

    def _section(self, title: str, values: list[str]) -> str:
        cleaned = self._clean_list(values)
        if not cleaned:
            return ""
        return f"{title}: " + "; ".join(cleaned) + "."

    def _join_sections(self, sections: list[str]) -> str:
        return "\n".join(section for section in sections if section.strip())

    def _clean_list(self, values: list[Any]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for value in values[: self.MAX_LIST_ITEMS * 2]:
            text = self._clip(str(value))
            if not text:
                continue
            key = text.casefold()
            if key not in seen:
                seen.add(key)
                cleaned.append(text)
        return cleaned[: self.MAX_LIST_ITEMS]

    def _list_from_mapping(self, mapping: dict[str, Any], *keys: str) -> list[str]:
        values: list[str] = []
        for key in keys:
            raw = mapping.get(key)
            if isinstance(raw, list):
                values.extend(str(item) for item in raw)
            elif isinstance(raw, str):
                values.append(raw)
        return values

    def _scene_summary(self, scene_state: dict[str, Any]) -> str:
        summary_keys = (
            "location",
            "mood",
            "emotion",
            "pose",
            "outfit",
            "lighting",
            "camera",
        )
        pieces = [
            f"{key}={scene_state[key]}" for key in summary_keys if scene_state.get(key)
        ]
        return self._clip("; ".join(pieces), 320) or "none"

    def _prompt_hash(self, canonical: dict[str, Any]) -> str:
        """Return a stable SHA256 trace hash for the prompt and key metadata."""

        canonical_json = json.dumps(
            canonical,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]

    def _explicit_user_face_requested(
        self, intent: str, scene_state: dict[str, Any]
    ) -> bool:
        if scene_state.get("allow_user_face_visibility") is True:
            return True
        text = intent.casefold()
        return any(term in text for term in self._USER_FACE_TERMS)

    def _clip(self, value: str, chars: int | None = None) -> str:
        value = re.sub(r"\s+", " ", value).strip()
        limit = chars or self.MAX_FIELD_CHARS
        return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"

    def _bound(self, value: str, chars: int) -> str:
        return value if len(value) <= chars else value[: chars - 1].rstrip() + "…"
