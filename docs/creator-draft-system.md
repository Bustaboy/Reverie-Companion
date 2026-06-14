# Creator Draft System

**Status:** M6-P01 foundation complete. This is a practical runtime note for future creator tasks, not a full user guide.

## What a draft is

A creator draft is an incomplete, editable character-construction artifact. It captures the M6-approved answers needed to preview and validate a future character without treating that work-in-progress as canonical character data.

Current draft data includes the basic creator foundation fields: draft/character IDs, display name, pronouns, adult baseline, species/type, relationship dynamic and starting phase, default intimacy level, desired experience, core traits, communication style, visual identity, tags, creator notes, and metadata.

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

## Draft validation and mapping

Draft validation is intentionally blueprint-based. The service converts draft fields into runtime structures, then lets the normal schema validation reject invalid runtime output. Current mappings include:

- identity fields into `CharacterIdentity`
- relationship premise fields into `RelationshipState`
- core traits into `PersonalityProfile`
- communication style into `CommunicationProfile`
- visual identity into `VisualIdentityProfile`
- creator provenance into blueprint metadata

This keeps future UI steps honest: if a creator field cannot map into runtime data, it should remain preview-only, store-only, or deferred in the capability matrix.

## Moment Capture integration

Creator drafts can trigger first-portrait Moment Capture before the character is finalized. The draft flow builds a temporary blueprint from the draft, passes the blueprint's visual identity and relationship state into the existing Moment Capture service, and marks the capture as draft-derived evidence.

Draft capture metadata uses the `draft_` prefix consistently, including the draft ID, source context (`chat` or `visual_novel`), capture intent, provenance, evidence-only status, rollback note, and the explicit rule that canonical mutation is not allowed while the character is still a draft.

This means first portraits can use the same M5 capture, gallery, feedback, review, and rollback patterns without creating a parallel visual canon store. Approved portrait/canon behavior still belongs to later creator save/review tasks; draft captures are evidence for validation until finalization.

## Current limits and next-task guidance

- There is no full practical creator UI yet; the foundation is backend/runtime-facing.
- Drafts are not backend-synced beyond local app persistence.
- Draft finalization into a durable saved character remains a later M6 review/save flow.
- Dialogue/greeting previews, import/export, memory/growth preference wiring, and richer field-impact evals remain later M6 work.
- Future creator tasks should extend the draft shape only when the capability matrix says the field is M6-ready, M6-preview-only, or M6-store-only with honest user-facing copy.
