# Creator Draft System

**Status:** M6-P08 foundation complete. This is a practical runtime note for future creator tasks, not a full user guide.

## What a draft is

A creator draft is an incomplete, editable character-construction artifact. It captures the M6-approved answers needed to preview and validate a future character without treating that work-in-progress as canonical character data.

Current draft data includes the basic creator foundation fields: draft/character IDs, display name, pronouns, adult baseline, species/type, relationship dynamic and starting phase, relationship pacing, romantic/NSFW pacing, default intimacy level, desired experience, core personality architecture, communication style, roleplay policy, character integrity controls, safeword/OOC controls, content boundaries, visual identity, lore-lite world/default scene settings, memory and growth preferences, tags, creator notes, and metadata.

Drafts are intentionally separated from finalized characters:

- Drafts live in the creator-draft persistence path and use `lifecycle_state: "draft"`.
- Drafts are versioned with a schema/migration seam.
- Draft metadata is preserved for future migration and step-specific UI state.
- Drafts can be validated and previewed without changing the selected active character.
- Deleting a draft deletes only creator work-in-progress, not a finalized character.

## What a finalized `CharacterBlueprint` is

A `CharacterBlueprint` is the canonical runtime character. Once saved through the character service, it becomes the durable object consumed by chat, selected-character state, prompt compilation, memory scoping, visual identity, relationship state, Moment Capture, gallery metadata, and later import/export.

The draft is therefore not a second character store. It is a staging area. The draft-to-blueprint mapper creates a minimally valid `CharacterBlueprint` for validation, preview, and first-portrait capture, but the blueprint is not canonical until a save/finalization flow writes it through the character service.

## Supported operations now

| Operation | Current behavior |
|---|---|
| Create | Persists a new draft with a generated draft ID when needed, timestamps, provenance, and validation output. |
| Load/list | Loads one draft or lists drafts ordered for creator resume flows. |
| Update | Applies partial draft patches, merges metadata, refreshes `updated_at`, and revalidates the resulting draft. |
| Validate | Maps the draft into a `CharacterBlueprint` and returns either the preview blueprint or validation errors. |
| Greeting preview | Generates a deterministic, non-persisted first-message preview from either an unsaved draft payload or a persisted draft ID. |
| Example dialogue previews | Generates deterministic, non-persisted example dialogues from either an unsaved draft payload or a persisted draft ID. |
| Delete | Removes a persisted draft without touching finalized character blueprints. |
| First portrait capture | Queues Moment Capture from either an unsaved draft payload or a persisted draft ID. |

## Supported identity fields

M6-P02 treats these identity fields as draft-supported and safe for the practical creator to expose with human-first wording:

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `display_name` | `CharacterIdentity.display_name` | Required text, 1-80 characters, whitespace-normalized, cannot be empty. |
| `pronouns` | `CharacterIdentity.pronouns` | Required text, 1-40 characters, whitespace-normalized, cannot be empty. |
| `species_or_type` | `CharacterIdentity.species_or_type` | Required text, 1-80 characters, whitespace-normalized, cannot be empty. |
| `adult_age_range` | `CharacterIdentity.adult_age_range` | Must be a supported adult age-range enum value. |
| `adult_only_confirmed` | `CharacterIdentity.adult_only_confirmed` | Must remain true for valid adult-only character creation; false fails blueprint validation. |

The draft validator also rejects underage or deliberately childlike presentation language in required creator text. This validation is intentionally narrow: it enforces the adult-only baseline without over-policing normal adult character designs such as cute, petite, stylized, youthful adult, tall, short, curvy, muscular, or plus-size adults.

`tags` and `creator_notes` also map through identity today, but they are support fields rather than the M6-P02 identity step. Tags are normalized and creator notes remain practical metadata/debug/import context, not a main premise promise.

## Supported premise and relationship fields

M6-P02 treats these premise/relationship fields as draft-supported. They define the starting frame for the relationship; they do not implement autonomous relationship evolution.

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `starting_relationship_phase` | `RelationshipState.starting_relationship_phase`, `current_relationship_phase`, and `phase` | Must be a supported `RelationshipPhase` enum value such as `strangers`, `newly_met`, `friends`, `close`, `romantic`, or `established_partners`. The mapper keeps all phase aliases synchronized for preview/runtime consistency. |
| `relationship_dynamic` | `RelationshipState.relationship_dynamic` | Required text, 1-240 characters, whitespace-normalized, underage/childlike-presentation checked. |
| `relationship_pacing` | `RelationshipState.relationship_pacing` | Must be a supported `RelationshipPacing` enum value: `slow_burn`, `natural`, `direct`, or `user_led`. |
| `romantic_pacing` | `RelationshipState.romantic_pacing` | Same pacing enum; controls the romantic pacing hint separately from the general relationship pace. |
| `nsfw_pacing` | `RelationshipState.nsfw_pacing` | Same pacing enum; should be exposed with clear adult-only wording and should not be confused with consent/safeword controls, which are documented in the M6-P04 roleplay policy section below. |
| `default_intimacy_level` | `RelationshipState.default_intimacy_level` | Must be a supported `DefaultIntimacyLevel` enum value: `sfw`, `flirtatious`, `romantic`, or `adult_roleplay`. |
| `user_desired_experience` | `RelationshipState.user_desired_experience` | Optional text up to 240 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. |

`companion_mode` is not a dedicated draft field yet. A future UI may present companion-mode cards, but those cards must map honestly into the supported relationship fields above, and optionally into personality/communication fields. Do not add a parallel premise store just to preserve a label.

## Supported personality fields

M6-P03 treats these personality fields as draft-supported. They are compact behavior anchors for prompt compilation and preview, not a full autonomous goals/planning engine.

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `core_traits` | `PersonalityProfile.core_traits` | Required list with 1-8 unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. |
| `independence` | `PersonalityProfile.independence` and `CharacterIntegrityPolicy.independence` | Float from 0.0 to 1.0. Higher values should imply more in-character backbone, initiative, and willingness to disagree. |
| `devotion` | `PersonalityProfile.devotion` | Float from 0.0 to 1.0. Use as an affection/loyalty anchor, not as a promise of dependency or constant agreement. |
| `dominance_or_initiative` | `PersonalityProfile.dominance_or_initiative` | Float from 0.0 to 1.0. Use for assertiveness/initiative and pair UI copy with boundary-aware examples. |
| `values_or_ideals` | `PersonalityProfile.values_or_ideals` | Optional list of unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. |
| `flaws` | `PersonalityProfile.flaws` | Optional list of unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. |
| `fears` | `PersonalityProfile.fears` | Optional list of unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. |
| `vulnerabilities` | `PersonalityProfile.vulnerabilities` | Optional list of unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. |

Practical UI should translate these into human-first controls. For example, presets such as warm, bold, playful, tender, shy slow-burn, or teasing can populate `core_traits`, the three float weights, and optional depth lists. Do not expose Big Five controls, active goals, wants/needs planning, or clinical labels in the normal M6 creator.

## Supported communication fields

M6-P03 treats these communication fields as draft-supported. They shape voice-of-character guidance for chat and previews.

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `communication_style` | `CommunicationProfile.style_notes` | Optional text up to 240 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. |
| `avoid_style` | `CommunicationProfile.avoid_style_rules` | Optional list with up to 8 unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. |
| `initiative_in_conversation` | `CommunicationProfile.initiative_in_conversation` | Float from 0.0 to 1.0. Higher values should imply more proactive conversational steering; it is a prompt/preview signal, not a scheduler or autonomous message system. |

`avoid_style` is negative behavior guidance, not a safety refusal list. Good entries are practical anti-examples such as “generic assistant tone,” “therapy-bot phrasing,” “constant agreement,” or “lecturing about fictional adult romance.” Avoid-style rules should help the companion sound less like a generic assistant while preserving the character's chosen personality.

## Supported roleplay policy, integrity, and boundary fields

M6-P04 treats these roleplay policy and boundary fields as draft-supported. They are practical controls for roleplay posture, character backbone, and meta stop/pause behavior; they are not a new moralizing refusal system and they do not replace the adult-only baseline.

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `integrity.in_character_pushback` | `CharacterIntegrityPolicy.in_character_pushback` | Required text, 1-240 characters, whitespace-normalized, adult-baseline checked. Use this to describe how the companion challenges, teases, negotiates, or resists while staying in character. |
| `integrity.disagreement_style` | `CharacterIntegrityPolicy.disagreement_style` | Required text, 1-240 characters, whitespace-normalized, adult-baseline checked. Use this to keep disagreement embodied in the character voice instead of assistant-style correction. |
| `roleplay.fiction_first_mode` | `RoleplayPolicy.fiction_first_mode` and `CharacterIntegrityPolicy.fiction_first_mode` | Boolean; defaults to true. When true, fictional adult roleplay should remain in-character unless a reality boundary, hard limit, or OOC stop/pause control is triggered. |
| `meta.safeword_policy.safeword` | `MetaConsentAndSafewordPolicy.safeword` | Required text, 1-40 characters, whitespace-normalized, adult-baseline checked. Defaults to `red`. |
| `meta.safeword_policy.ooc_marker` | `MetaConsentAndSafewordPolicy.ooc_marker` | Required text, 1-20 characters, whitespace-normalized, adult-baseline checked. Defaults to `[OOC]`. |
| `meta.safeword_policy.pause_commands` | `MetaConsentAndSafewordPolicy.pause_commands` | Required list with 1-8 unique, whitespace-normalized commands; each command is capped at 40 characters and adult-baseline checked. Defaults include `pause`, `stop`, `safeword`, and `red`. |
| `meta.safeword_policy.fade_to_black_preference` | `MetaConsentAndSafewordPolicy.fade_to_black_preference` | Must be one of `ask`, `allow`, `prefer`, or `never`. |
| `meta.safeword_policy.policy_note` | `RoleplayPolicy.safeword_policy` | Required text, 1-240 characters, whitespace-normalized, adult-baseline checked. This is the prompt-facing summary of how to respect OOC stop, pause, safeword, or clear distress. |
| `content_boundaries.hard_limits` | `CharacterBlueprint.metadata.content_boundaries.hard_limits` | Optional list of unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. Use for topics or actions the roleplay should not enter. |
| `content_boundaries.soft_limits` | `CharacterBlueprint.metadata.content_boundaries.soft_limits` | Optional list of unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. Use for topics that require extra care, slower pacing, or explicit checking. |
| `content_boundaries.preferred_intensity` | `CharacterBlueprint.metadata.content_boundaries.preferred_intensity` | Optional text up to 80 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. |
| `content_boundaries.aftercare_style` | `CharacterBlueprint.metadata.content_boundaries.aftercare_style` | Optional text up to 240 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. |

Practical UI should explain these controls in human-first language: how she pushes back, what counts as a pause/OOC signal, what should be avoided, what should be handled gently, and whether fade-to-black should be offered. The user should not need to understand internal names such as `CharacterIntegrityPolicy` or `MetaConsentAndSafewordPolicy` to configure them.

Boundary lists are lightweight draft metadata today. They can be shown in summaries, validation output, and blueprint previews, and they can inform prompt construction through the mapped blueprint metadata. They are not yet a full memory receipt system, trust dashboard, or advanced scene-control engine.

## Supported visual identity fields

M6-P05 treats these visual identity fields as draft-supported. The practical rule is simple: stable anchors describe what should not drift, evolving traits describe canon self-expression that can change through confirmation or story, and scene-mutable traits describe only the current image/scene presentation.

### Stable identity anchors

Stable anchors map into `VisualIdentityProfile.identity_anchors`. They are included in visual prompt summaries and should be preserved across first-portrait validation, Moment Capture, and later saved character use.

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `visual.eye_color` | Adds `eye color: {value}` to `VisualIdentityProfile.identity_anchors` | Optional text up to 80 characters; blank values normalize to null; nonblank values are whitespace-normalized and adult-baseline checked. Must not contain scene-level outfit, pose, or expression language. |
| `visual.skin_tone` | Adds `skin tone: {value}` to `VisualIdentityProfile.identity_anchors` | Optional text up to 120 characters; blank values normalize to null; nonblank values are whitespace-normalized and adult-baseline checked. Must stay stable-identity focused. |
| `visual.face_structure` | Adds `face structure: {value}` to `VisualIdentityProfile.identity_anchors` | Optional text up to 160 characters; blank values normalize to null; nonblank values are whitespace-normalized and adult-baseline checked. Must not describe temporary expressions or poses. |
| `visual.body_baseline` | Adds `body baseline: {value}` to `VisualIdentityProfile.identity_anchors` | Optional text up to 160 characters; blank values normalize to null; nonblank values are whitespace-normalized and adult-baseline checked. The adult-only baseline still applies; do not use underage or deliberately childlike presentation language. |
| `visual.species_features` | Adds one `species features: {value}` anchor per entry | Optional list of unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. Use for stable horns, ears, tail, wings, android features, or similar permanent/species-defining features. |
| `visual.permanent_marks` | Adds one `permanent marks: {value}` anchor per entry | Optional list of unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. Use for scars, birthmarks, permanent tattoos, or similar non-temporary marks. |

### Evolving traits

Evolving traits map into `VisualIdentityProfile.evolving_traits` as `VisualTrait` records with `provenance: "creator_draft_visual_identity"`. They are prompt-consumed visual canon, but unlike anchors they are allowed to change through reviewable story, gallery, or user-confirmed visual updates.

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `visual.hair` | Adds or replaces evolving trait `hair` | Optional text up to 160 characters; blank values normalize to null; nonblank values are whitespace-normalized and adult-baseline checked. Use for current hair color/style as one practical description. |
| `visual.accessories` | Adds one evolving trait named `accessory` per entry | Optional list of unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. Use for signature jewelry, glasses, hair ornaments, cyberware accents, or similar reusable look details. |
| `visual.fashion_identity` | Adds or replaces evolving trait `fashion_identity` | Optional text up to 160 characters; blank values normalize to null; nonblank values are whitespace-normalized and adult-baseline checked. Use for her recognizable style language, not the exact outfit in a single scene. |

Examples of future-friendly evolving traits include hair, accessories, fashion identity, reusable makeup style, cyberware/fantasy embellishments, or other appearance details that can become canon only through explicit confirmation/review. Do not treat them as autonomous visual growth controls; they are stored prompt/capture inputs today.

### Scene-mutable traits

Scene-mutable traits map into `VisualIdentityProfile.scene_mutable_traits`. They can influence first-portrait or Moment Capture prompts, but they should not overwrite stable identity.

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `visual.outfit` | Adds `outfit: {value}` to `VisualIdentityProfile.scene_mutable_traits` | Optional text up to 160 characters; blank values normalize to null; nonblank values are whitespace-normalized and adult-baseline checked. |
| `visual.pose` | Adds `pose: {value}` to `VisualIdentityProfile.scene_mutable_traits` | Optional text up to 160 characters; blank values normalize to null; nonblank values are whitespace-normalized and adult-baseline checked. |
| `visual.expression` | Adds `expression: {value}` to `VisualIdentityProfile.scene_mutable_traits` | Optional text up to 160 characters; blank values normalize to null; nonblank values are whitespace-normalized and adult-baseline checked. |

Use scene-mutable traits for what the current capture should show: outfit, pose, and expression. Do not put these details into `eye_color`, `skin_tone`, `face_structure`, or `body_baseline`; the draft model rejects obvious anchor/scene mixing for those stable fields.

### Rejected visual traits

`visual.rejected_visual_traits` maps into `VisualIdentityProfile.rejected_traits`. It is an optional list of unique, whitespace-normalized entries capped at 80 characters each and adult-baseline checked. Use it for appearance drift or unwanted generated details such as the wrong eye color, wrong skin tone, wrong body baseline, incorrect species feature, unwanted style, or other traits the visual prompt should avoid.

Rejected traits are not a positive-description bucket. They feed negative guidance through the visual prompt/capture stack and should be phrased as concise things to avoid, not as replacement instructions.

### Visual mapping summary

The draft mapper starts with the draft's existing `visual_identity` profile, then applies the creator-facing `visual` fields on top of it:

- stable anchor fields append labeled strings to `identity_anchors`, de-duplicated and bounded to the profile list limit;
- `hair`, `accessories`, and `fashion_identity` become provenance-tracked evolving traits;
- `outfit`, `pose`, and `expression` append labeled strings to `scene_mutable_traits`;
- `rejected_visual_traits` append to `rejected_traits`;
- the resulting profile receives a refreshed `updated_at` timestamp and remains a normal `VisualIdentityProfile` for prompt summaries, draft validation, and Moment Capture.

This separation is the important contract for UI copy: anchors answer “what should never drift?”, evolving traits answer “what is part of her current/canon style but may change with review?”, and scene traits answer “what should this moment look like?”


## Supported world and default scene fields

M6-P06 treats these world/default scene fields as draft-supported. They are lore-lite starting context for prompt scene hints and first-portrait/Moment Capture defaults, not a full lorebook, world simulation, or retrieval-ranked canon store.

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `world_scene.default_setting` | `CharacterBlueprint.metadata.world_scene.default_setting` and `metadata.scene_hints.setting`; used as the default draft Moment Capture `SceneState.location` when no explicit chat/VN scene is supplied. | Optional text up to 240 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. Use compact location/setting language such as “rainy moonlit atelier above the old city.” |
| `world_scene.scenario` | `CharacterBlueprint.metadata.world_scene.scenario` and `metadata.scene_hints.scenario`; appears in prompt scene hints and seeds draft Moment Capture `SceneState.emotional_tone`. | Optional text up to 500 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. Use it for the opening situation, not for a long backstory dump. |
| `world_scene.world_genre` / creator-facing `genre_frame` | `CharacterBlueprint.metadata.world_scene.world_genre` and `metadata.scene_hints.world_genre`; shown as compact genre context in prompt scene hints. | Optional text up to 120 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. UI may call this “genre frame,” but the draft field is `world_genre`. |
| `world_scene.user_role_in_story` | `RelationshipState.user_role_in_story`; consumed by the relationship prompt context as the user's in-story role. | Optional text up to 240 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. Use for the user's role in the relationship/story, not as a second character identity. |
| `world_scene.time_of_day` | `CharacterBlueprint.metadata.world_scene.time_of_day`, `metadata.scene_hints.time_of_day`, and draft Moment Capture `SceneState.time_of_day`. | Optional text up to 80 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. |
| `world_scene.mood` | `CharacterBlueprint.metadata.world_scene.mood`, `metadata.scene_hints.mood`, and draft Moment Capture `SceneState.mood`; falls back to relationship dynamic when absent. | Optional text up to 240 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. |
| `world_scene.key_objects` | `CharacterBlueprint.metadata.world_scene.key_objects` and `metadata.scene_hints.props`; used as draft Moment Capture `SceneState.key_objects`. | Optional list with up to 8 unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. Use for scene props or symbolic objects, not hidden lore entries. |
| `world_scene.background_details` | `CharacterBlueprint.metadata.world_scene.background_details` and `metadata.scene_hints.background_details`; used as draft Moment Capture `SceneState.background_details`. | Optional list with up to 8 unique, whitespace-normalized entries; each entry is capped at 80 characters and adult-baseline checked. Use for visible environmental details such as lighting, weather, windows, furniture, or stage texture. |

The draft mapper stores the complete normalized `world_scene` object under `CharacterBlueprint.metadata.world_scene` for preview/finalization handoff, and stores a compact prompt-facing subset under `CharacterBlueprint.metadata.scene_hints`. The prompt compiler reads `scene_hints` in the “Visual / scene hints” section using the keys `setting`, `scenario`, `world_genre`, `time_of_day`, `mood`, `props`, and `background_details`.

When draft first-portrait capture needs a scene and the request does not provide explicit chat or Visual Novel scene state, the creator service builds a default `SceneState` from these hints: `setting` becomes `location`, `time_of_day` remains `time_of_day`, `mood` becomes `mood`, `scenario` becomes `emotional_tone`, `props` become `key_objects`, and `background_details` become `background_details`. Visual identity summaries still provide character appearance, so world/scene defaults should describe the environment and moment rather than restating stable appearance anchors.

Practical UI should ask this step in human language: “Where does your story usually begin?”, “What kind of world is this?”, “Who are you to her in the story?”, “What mood should the first scene carry?”, and “What objects or background details should the moment remember?” Keep copy clear that these are defaults. Current chat/VN scene state can override them for a specific capture.


## Supported memory and growth preference fields

M6-P07 treats memory and growth preferences as draft-supported baseline policy fields. They let the creator describe whether this companion should use long-term memory and how quickly the companion may reflect or grow, without promising the deeper M8/M9 trust dashboard, relationship timeline, autonomous personality rewrites, or training flows.

### Memory preferences

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `memory.memory_enabled` | `CharacterMemoryPolicy.memory_enabled` | Boolean. When `false`, the draft maps to a policy summary that says long-term memory is disabled for this draft. |
| `memory.memory_scope` | `CharacterMemoryPolicy.scope`; also sets `include_shared_memories` when the value is `character_plus_shared` and memory is enabled | Enum limited to `character_private` or `character_plus_shared`. Drafts cannot select unbounded `global` memory scope. |

`character_private` means draft previews and later saved character behavior should stay scoped to this companion. `character_plus_shared` allows shared memories to be included while still keeping the character's own memory policy explicit. If memory is disabled, shared-memory inclusion is disabled too, even if the scope field says `character_plus_shared`.

These fields are intentionally narrow. Current drafts do not expose remember-category, never-remember-category, memory-review-queue, memory-ranking, or receipt-dashboard controls as completed capabilities. Those remain future work unless a later task adds enforceable storage, preview, and validation.

### Growth preferences

| Draft field | Runtime mapping | Validation behavior |
|---|---|---|
| `growth.reflection_frequency` | `GrowthPolicy.reflection_frequency` | Enum using the current growth policy choices: `low`, `balanced`, or `high`. Invalid values are rejected during draft parsing/validation. |
| `growth.growth_pace` | `GrowthPolicy.growth_pace` | Enum using `slow`, `balanced`, or `responsive`. Invalid values are rejected during draft parsing/validation. |
| `growth.allowed_growth_domains` | `GrowthPolicy.allowed_growth_domains` | Optional list with at least one effective value. Entries are trimmed, lowercased, spaces/hyphens become underscores, duplicates are removed, each entry is capped at 80 characters, and the list is capped at 16 entries. Entries may contain only letters, numbers, spaces, hyphens, or underscores before normalization. |
| `growth.blocked_growth_domains` | `GrowthPolicy.blocked_growth_domains` | Same list normalization as allowed domains. The list must include `stable_identity_without_user_edit` and `underage_or_childlike_sexualization`. |
| `growth.major_change_requires_approval` | `GrowthPolicy.major_change_requires_approval` | Boolean. Defaults to `true`; when enabled, major visual/personality growth should continue to use available review gates instead of silently mutating stable canon. |

The default allowed domains are `preferences`, `relationship`, `rituals`, and `communication_style`. The default blocked domains are `stable_identity_without_user_edit` and `underage_or_childlike_sexualization`. UI may add practical labels around those domains, but should preserve the safety meaning: normal preferences and relationship habits may evolve; stable identity and adult-safety boundaries do not drift automatically.

Safety validation rejects any domain that appears in both the allowed and blocked lists. It also rejects growth policies that omit either required blocked domain. This matters because draft growth preferences are not just descriptive text; they map into `GrowthPolicy` and can be consumed by reflection/growth orchestration and prompt summaries.

### Memory/growth mapping summary

During draft validation, the creator service converts memory and growth preferences into runtime policy objects before building the `CharacterBlueprint` preview:

- `memory.memory_enabled` and `memory.memory_scope` become `CharacterMemoryPolicy`;
- `memory.memory_scope == character_plus_shared` sets `include_shared_memories` only when memory is enabled;
- disabled memory adds a compact `memory_summary` stating that long-term memory is disabled for the draft;
- `growth.reflection_frequency`, `growth.growth_pace`, `growth.allowed_growth_domains`, `growth.blocked_growth_domains`, and `growth.major_change_requires_approval` become `GrowthPolicy`;
- `GrowthPolicy.character_id` uses the draft preview character ID, so validation remains character-scoped;
- list normalization and safety blocks happen before the blueprint preview is accepted.

Practical creator copy should frame this as “how much should she remember?” and “how cautiously should she grow?” rather than exposing every internal policy name by default. Advanced editors can show the exact fields because they now have concrete draft storage and blueprint mappings.


## Greeting and dialogue preview engine

M6-P08 adds a deterministic preview engine for creator drafts. Its purpose is practical evidence: before saving, the user and future creator UI can see how the draft's identity, relationship, personality, communication style, policies, world/scene defaults, visual identity, memory setting, and growth setting affect the companion's first-message and sample dialogue voice.

### Available preview types

| Preview type | What it returns | Intended use |
|---|---|---|
| Greeting / first message | One `greeting` string in a `DraftPreviewResponse` with `kind: "greeting"`. | Show the likely opening voice and first-message posture before final character creation. |
| Example dialogues | A list of `example_dialogues`, each with a scenario label and short User/character turns, in a `DraftPreviewResponse` with `kind: "example_dialogues"`. | Show how the draft responds across practical creator scenarios such as a bad day, light flirt/quiet romance, boundary handling, memory acknowledgement, and growth/approval language. |

Current previews are generated by the deterministic `deterministic_creator_preview_v1` engine. They are fast, bounded, testable examples rather than accepted canon text. A later UI may let users accept, edit, or replace preview text during review/save, but M6-P08 does not create durable alternate-greeting storage.

### How previews are generated

Preview generation follows the same staging rule as draft validation:

1. The service converts the `CharacterCreatorDraft` into a temporary `CharacterBlueprint` using the normal draft-to-blueprint mapper.
2. It compiles bounded prompt context with `CharacterPromptCompiler`, including visual summaries where relevant.
3. It builds deterministic preview text from the mapped blueprint rather than opening a chat session or calling a cloud-required model.
4. It returns the preview text, prompt context when requested, preview metadata, and a quality report.

Because the mapper is used first, previews respect all currently draft-supported fields and policies: identity/adult baseline, relationship phase/dynamic/pacing, default intimacy level, personality traits and sliders, communication style and avoid-style rules, character-integrity pushback, fiction-first mode, safeword/OOC policy, content boundaries, visual identity anchors/evolving/scene traits/rejected traits, world/default scene hints, memory scope, and growth preferences. Invalid drafts still fail through blueprint validation before preview output is trusted.

### Preview quality and consistency validation

Every preview response includes a `PreviewQualityReport`:

| Field | Meaning |
|---|---|
| `passed` | `true` when no error-severity issue was found. Warning-severity coverage gaps can still be reported for UI review. |
| `issues` | List of `PreviewQualityIssue` records with `code`, `message`, and `severity` (`warning` or `error`). |
| `covered_fields` | Field groups visibly reflected in the generated preview text. |

The quality validator checks for visible coverage of required field groups such as identity, personality, communication style, relationship, roleplay policy, world/scene hints, visual identity, memory, and growth. It also flags consistency problems, including avoid-style leakage, hard-limit leakage, and underage/childlike-presentation language.

Quality reports are not a replacement for final model evals. They are a deterministic guardrail that helps creator UI show honest warnings and helps tests reject decorative fields whose values do not appear to influence preview output.

### Preview API endpoints

The preview routes are intentionally separate for unsaved draft payloads and persisted draft IDs:

| Endpoint | Draft source | Behavior |
|---|---|---|
| `POST /api/characters/creator/greeting-preview` | Request body contains a full `draft`. | Generates a non-persisted greeting preview for an unsaved/in-progress draft. |
| `POST /api/characters/creator/example-dialogue-previews` | Request body contains a full `draft`. | Generates non-persisted example dialogue previews for an unsaved/in-progress draft. |
| `POST /api/characters/creator/drafts/{draft_id}/greeting-preview` | Loads an existing persisted draft by `draft_id`. | Generates a non-persisted greeting preview without modifying the draft or saving a character. |
| `POST /api/characters/creator/drafts/{draft_id}/example-dialogue-previews` | Loads an existing persisted draft by `draft_id`. | Generates non-persisted example dialogue previews without modifying the draft or saving a character. |

Unsaved preview requests use `DraftPreviewRequest`, which includes the `draft` and `include_prompt_context`. Persisted preview requests use `PersistedDraftPreviewRequest`, which includes `include_prompt_context`. Setting `include_prompt_context` to false keeps the response lighter by returning `"omitted"` in the prompt-context field.

### Preview output is separate from final character creation

Preview generation does not create a chat session, write memories, write reflection journal entries, create training candidates, approve visual canon, or save a finalized `CharacterBlueprint`. Preview response metadata explicitly marks storage as `not_persisted`.

This separation matters for product trust: previews are evidence and editing feedback while the companion is still a draft. The final character remains created only by a later review/save flow that writes through the character service. Until then, draft previews can be regenerated, compared, discarded, or used for validation without mutating canonical character state.

## Draft validation and mapping

Draft validation is intentionally blueprint-based. The service converts draft fields into runtime structures, then lets the normal schema validation reject invalid runtime output. Current mappings include:

- identity fields into `CharacterIdentity`
- relationship premise fields into `RelationshipState`
- personality fields into `PersonalityProfile`
- `independence` into both `PersonalityProfile.independence` and `CharacterIntegrityPolicy.independence`
- communication fields into `CommunicationProfile`
- `integrity.in_character_pushback` and `integrity.disagreement_style` into `CharacterIntegrityPolicy`
- `roleplay.fiction_first_mode` into both `RoleplayPolicy` and `CharacterIntegrityPolicy`
- `meta.safeword_policy` into `MetaConsentAndSafewordPolicy`, with its `policy_note` also summarized in `RoleplayPolicy.safeword_policy`
- `content_boundaries` into blueprint metadata for prompt/preview use
- creator-facing `visual` fields and any existing draft `visual_identity` profile into `VisualIdentityProfile`
- `world_scene.user_role_in_story` into `RelationshipState.user_role_in_story`
- `world_scene` into blueprint metadata, with compact `scene_hints` for prompt and Moment Capture defaults
- `memory` into `CharacterMemoryPolicy`
- `growth` into `GrowthPolicy`
- creator provenance into blueprint metadata

For identity and premise, the mapper copies `display_name`, `pronouns`, `adult_age_range`, `species_or_type`, `tags`, `creator_notes`, `adult_only_confirmed`, `starting_relationship_phase`, `relationship_dynamic`, `relationship_pacing`, `romantic_pacing`, `nsfw_pacing`, `default_intimacy_level`, and `user_desired_experience` into their runtime structures.

For personality and communication, the mapper copies `core_traits`, `independence`, `devotion`, `dominance_or_initiative`, `values_or_ideals`, `flaws`, `fears`, `vulnerabilities`, `communication_style`, `avoid_style`, and `initiative_in_conversation` into the corresponding runtime profiles.

For roleplay policy and boundaries, the mapper copies `integrity.in_character_pushback`, `integrity.disagreement_style`, `roleplay.fiction_first_mode`, `meta.safeword_policy.safeword`, `meta.safeword_policy.ooc_marker`, `meta.safeword_policy.pause_commands`, `meta.safeword_policy.fade_to_black_preference`, `meta.safeword_policy.policy_note`, and `content_boundaries` into the runtime policy objects or metadata described above. That means these fields can appear in draft summaries and blueprint previews today, as long as UI copy remains honest: fiction-first mode and in-character pushback are prompt policy signals, safeword/OOC fields are explicit meta-controls, and content boundaries are lightweight stored guidance rather than a complete scene-safety engine.

For visual identity, the mapper copies stable anchors, evolving traits, scene-mutable traits, and rejected visual traits into `VisualIdentityProfile` as described in the M6-P05 visual section above. That means first-portrait capture and visual prompt summaries can use the draft visual profile without turning the draft into canonical saved character data.

For world/default scene, the mapper copies `default_setting`, `scenario`, `world_genre`, `user_role_in_story`, `time_of_day`, `mood`, `key_objects`, and `background_details` into either `RelationshipState` or blueprint metadata as described in the M6-P06 section above. That means compiled prompts can include compact scene hints and draft Moment Capture can fall back to default scene state without creating a full lorebook.

For memory and growth preferences, the mapper copies `memory_enabled`, `memory_scope`, `reflection_frequency`, `growth_pace`, `allowed_growth_domains`, `blocked_growth_domains`, and `major_change_requires_approval` into the runtime policy objects described in the M6-P07 section above. That means draft summaries and blueprint previews can show baseline memory/growth behavior while staying honest that advanced receipts, long-session evals, and autonomous growth remain future work.

This keeps future UI steps honest: if a creator field cannot map into runtime data, it should remain preview-only, store-only, or deferred in the capability matrix.

## Practical UI implications for future work

- The identity step may ask for the companion's name, pronouns, adult age/presentation baseline, and species/type.
- The premise step may ask how the relationship begins, what the bond should feel like, how quickly romance/adult roleplay should move, and what default intimacy level the user wants.
- The personality step may offer presets and editable nuance that write to `core_traits`, `independence`, `devotion`, `dominance_or_initiative`, and optional depth lists.
- The communication step may ask how she talks, what she should avoid sounding like, and how proactive she should be in conversation.
- The roleplay policy step may ask how she pushes back in character, whether fictional adult roleplay should stay fiction-first, what safeword/OOC marker and pause commands to use, how fade-to-black should be handled, and what hard/soft boundaries should be summarized.
- The visual identity step may ask what should never drift about her look, what current style traits can evolve with confirmation, what outfit/pose/expression belongs only to this scene, and what generated traits should be rejected.
- The world/default scene step may ask for the default setting, opening scenario, genre frame, user role in story, default time of day, mood, key objects, and background details.
- These fields can appear in draft summaries and blueprint previews before final save.
- Pacing and default intimacy are starting-frame hints for chat/prompt behavior; roleplay boundaries, safewords, OOC commands, and fade-to-black preferences now live in the M6-P04 draft policy fields.
- Personality and communication fields are behavior anchors for compiled prompts and previews; they are not active planning, autonomous outreach, or guaranteed model behavior.
- Greeting and example dialogue preview controls can call the M6-P08 preview endpoints, but accepted/saved greeting text, alternate greeting storage, and editable dialogue libraries remain review/save or later workflow concerns.
- Nickname/short name, occupation/role beyond compact story-role text, perspective mode, humor-style subfields, pet names, catchphrases, speech quirks, dedicated art style, asset/reference attachment UI, and portrait approval UI should only be exposed according to the capability matrix status; they are not part of the M6-P08 draft-supported preview contract.

## Moment Capture integration

Creator drafts can trigger first-portrait Moment Capture before the character is finalized. The draft flow builds a temporary blueprint from the draft, passes the blueprint's visual identity, relationship state, and default scene hints into the existing Moment Capture service, and marks the capture as draft-derived evidence.

Draft capture metadata uses the `draft_` prefix consistently, including the draft ID, source context (`chat` or `visual_novel`), capture intent, provenance, evidence-only status, rollback note, and the explicit rule that canonical mutation is not allowed while the character is still a draft.

This means first portraits can use the same M5 capture, gallery, feedback, review, and rollback patterns without creating a parallel visual canon store. Approved portrait/canon behavior still belongs to later creator save/review tasks; draft captures are evidence for validation until finalization.

## Current limits and next-task guidance

- There is no full practical creator UI yet; the foundation is backend/runtime-facing.
- Drafts are not backend-synced beyond local app persistence.
- Draft finalization into a durable saved character remains a later M6 review/save flow.
- Import/export and richer field-impact evals remain later M6 work; greeting/dialogue previews are available now as deterministic, non-persisted draft previews.
- Full lorebooks/canon retrieval, remember/never-remember category controls, import/export, asset/reference attachment UI, and portrait approval UI should not be documented here as completed M6-P08 behavior.
- Future creator tasks should extend the draft shape only when the capability matrix says the field is M6-ready, M6-preview-only, or M6-store-only with honest user-facing copy.
