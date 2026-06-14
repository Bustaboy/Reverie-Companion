# Creator Draft System

**Status:** M6-P02 foundation complete. This is a practical runtime note for future creator tasks, not a full user guide.

## What a draft is

A creator draft is an incomplete, editable character-construction artifact. It captures the M6-approved answers needed to preview and validate a future character without treating that work-in-progress as canonical character data.

Current draft data includes the basic creator foundation fields: draft/character IDs, display name, pronouns, adult baseline, species/type, relationship dynamic and starting phase, relationship pacing, romantic/NSFW pacing, default intimacy level, desired experience, core traits, communication style, visual identity, tags, creator notes, and metadata.

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
| `nsfw_pacing` | `RelationshipState.nsfw_pacing` | Same pacing enum; should be exposed with clear adult-only wording and should not be confused with consent/safeword controls, which remain M6-P04 scope. |
| `default_intimacy_level` | `RelationshipState.default_intimacy_level` | Must be a supported `DefaultIntimacyLevel` enum value: `sfw`, `flirtatious`, `romantic`, or `adult_roleplay`. |
| `user_desired_experience` | `RelationshipState.user_desired_experience` | Optional text up to 240 characters; blank values normalize to null and nonblank values are whitespace-normalized and adult-baseline checked. |

`companion_mode` is not a dedicated draft field yet. A future UI may present companion-mode cards, but those cards must map honestly into the supported relationship fields above, and optionally later into personality/communication fields when those steps are implemented. Do not add a parallel premise store just to preserve a label.

## Draft validation and mapping

Draft validation is intentionally blueprint-based. The service converts draft fields into runtime structures, then lets the normal schema validation reject invalid runtime output. Current mappings include:

- identity fields into `CharacterIdentity`
- relationship premise fields into `RelationshipState`
- core traits into `PersonalityProfile`
- communication style into `CommunicationProfile`
- visual identity into `VisualIdentityProfile`
- creator provenance into blueprint metadata

For M6-P02 specifically, the mapper copies `display_name`, `pronouns`, `adult_age_range`, `species_or_type`, `tags`, `creator_notes`, and `adult_only_confirmed` into `CharacterIdentity`. It copies `starting_relationship_phase`, `relationship_dynamic`, `relationship_pacing`, `romantic_pacing`, `nsfw_pacing`, `default_intimacy_level`, and `user_desired_experience` into `RelationshipState`.

This keeps future UI steps honest: if a creator field cannot map into runtime data, it should remain preview-only, store-only, or deferred in the capability matrix.

## Practical UI implications for future work

- The identity step may ask for the companion's name, pronouns, adult age/presentation baseline, and species/type.
- The premise step may ask how the relationship begins, what the bond should feel like, how quickly romance/adult roleplay should move, and what default intimacy level the user wants.
- These fields can appear in draft summaries and blueprint previews before final save.
- Pacing and default intimacy are starting-frame hints for chat/prompt behavior, not a substitute for roleplay boundaries, safewords, OOC commands, or full consent controls.
- Nickname/short name, occupation/role, genre frame, perspective mode, and durable user role in story should only be exposed according to the capability matrix status for those fields; they are not part of the M6-P02 draft-supported contract.

## Moment Capture integration

Creator drafts can trigger first-portrait Moment Capture before the character is finalized. The draft flow builds a temporary blueprint from the draft, passes the blueprint's visual identity and relationship state into the existing Moment Capture service, and marks the capture as draft-derived evidence.

Draft capture metadata uses the `draft_` prefix consistently, including the draft ID, source context (`chat` or `visual_novel`), capture intent, provenance, evidence-only status, rollback note, and the explicit rule that canonical mutation is not allowed while the character is still a draft.

This means first portraits can use the same M5 capture, gallery, feedback, review, and rollback patterns without creating a parallel visual canon store. Approved portrait/canon behavior still belongs to later creator save/review tasks; draft captures are evidence for validation until finalization.

## Current limits and next-task guidance

- There is no full practical creator UI yet; the foundation is backend/runtime-facing.
- Drafts are not backend-synced beyond local app persistence.
- Draft finalization into a durable saved character remains a later M6 review/save flow.
- Dialogue/greeting previews, import/export, memory/growth preference wiring, and richer field-impact evals remain later M6 work.
- Personality, visuals, lore/default scene, roleplay policy, memory/growth preferences, and import/export should not be documented here as completed M6-P02 behavior.
- Future creator tasks should extend the draft shape only when the capability matrix says the field is M6-ready, M6-preview-only, or M6-store-only with honest user-facing copy.
