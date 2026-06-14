# Reverie - CHARACTER_CREATOR_CAPABILITY_MATRIX

**Date:** 2026-06-14
**Version:** 2.7
**Context:** M6-P00 documentation-only reconciliation after Milestone 5. Milestones 4 and 5 delivered the core character runtime, relationship state, visual identity, Moment Capture backend, visual feedback, visual memory, asset metadata, and reviewable visual canon workflows. This matrix is the authoritative field gate for the Basic Character Creator Foundation; no creator UI or runtime code was changed by this pass.
**Goal:** Identify every high-value character-creator field that could make a Reverie companion feel alive, then classify whether Reverie can process it now, must close a runtime gap in M6, should store it without exposing it, or should defer it to later milestones.

---

## 0. Core Principle

A creator question should ship only if Reverie can:

1. **Store it structurally** in `CharacterBlueprint`, a related state object, or a versioned artifact.
2. **Consume it** in at least one runtime system: chat, memory, Moment Capture, Visual Novel, TTS, gallery, trust/review, growth, or future training.
3. **Preview it** before the user commits.
4. **Validate or correct it** when output is wrong.
5. **Preserve it across sessions** without relying on prompt stuffing alone.

If a field fails this test, it belongs in one of these buckets:

- **Internal only:** store now, do not expose in the wizard yet.
- **Preview-only:** expose as draft text or examples, but do not imply strong runtime behavior.
- **Future field:** useful later, but do not ask users yet.
- **Out:** too ambiguous, unsafe, or low-signal.

For every field moved from `STORE`, `PROMPT`, `PARTIAL`, or `NEEDS_RUNTIME` into user-facing creator UX, add at least one test/eval from `prompts/skills/character-quality-evals.md`. The test can be deterministic unit coverage, snapshot prompt-compiler coverage, or a manual validation checklist when model output is involved.

M6 must not become a stealth M7/M8/M9 bundle. Yes, the machine room has many pipes. No, the user should not be asked to name every pipe.

---

## 0.1 Current Runtime Reality After M5

The current repo already has these runtime foundations:

- `CharacterBlueprint` with version, identity, relationship state, personality, communication, memory policy, roleplay policy, character integrity, meta-consent/safeword policy, growth policy, visual identity, timestamps, and metadata.
- Character CRUD routes under `/api/characters`.
- `CharacterPromptCompiler` consuming identity, relationship, personality, communication, memory, growth, roleplay, integrity, meta-consent, and visual summaries.
- `RelationshipState` with phase, dynamic, trust, affection, comfort, pacing, intimacy, user-desired experience, user story role, dynamic tags, milestones, unresolved threads, promises, and rituals.
- `VisualIdentityProfile` with adult visual baseline, identity anchors, evolving traits, scene-mutable traits, rejected traits, current appearance, and prompt-safe summaries.
- `VisualPromptCompiler`, `MomentCaptureRequest`, `MomentCaptureRecord`, `VisualFeedbackAction`, `VisualChangeEvent`, and `VisualMemoryArtifact` from M5.
- Gallery feedback and minimal review/approve/reject/rollback UI for visual changes.
- Character-scoped visual memory writeback with explicit `character_id` / `memory_scope` enforcement.

Important current gap:

- Chat/VN frontend actions still need to be wired as true primary Moment Capture requests through `POST /api/moment-capture`. Backend Moment Capture exists; this M6-P00 reconciliation identifies that as a required gap-closure task before creator portrait validation depends on it.

---

## 0.2 Roleplay-First Integrity Rule

Do **not** use a generic moralizing `AntiSycophancyPolicy` as a creator/runtime concept. Use `CharacterIntegrityPolicy` instead.

Older planning language used “anti-sycophancy” as shorthand for preventing blind agreement. In Reverie, the implemented concept is roleplay-aware character integrity:

- `CharacterIntegrityPolicy`
- `InCharacterPushbackProfile` behavior through character prompt rules
- `RoleplayFictionBoundaryPolicy` behavior through fiction-first prompt rules
- `RealityBoundaryPolicy` behavior through reality-boundary style
- `MetaConsentAndSafewordPolicy`

The goal is believable character backbone, in-character disagreement, teasing, resistance, negotiation, boundaries, and reality-layer handling when the user clearly exits fiction. The goal is not moral correction.

Baseline adult-content rule:

```text
Reverie is an uncensored adult roleplay app.
Fictional adult fantasy is allowed by default.
Do not moralize, sanitize, or kink-shame user-chosen adult roleplay.
```

Hard boundary:

```text
18+ only. No underage sexual content. No deliberately childlike sexual presentation.
```

Do **not** over-police normal adult character design. Cute adult, petite adult, youthful adult, early-20s adult, anime-stylized adult, soft-featured adult, short adult, tall adult, thin adult, curvy adult, muscular adult, and plus-size adult characters are valid. The line is not “looks young” or “is cute”; the line is “is underage or deliberately presented as childlike in sexual contexts.”

---

## 0.3 Human-Factor Creator Rule

The matrix uses technical field names because Grok and Codex need precise implementation targets. The user-facing creator should not expose most of those names.

The visible wizard should feel like a dream-building conversation:

- “How should she make you feel?”
- “What kind of stories do you want together?”
- “What makes her unforgettable?”
- “What does she do when she wants your attention?”
- “What should never be lost about her?”
- “What kind of moments do you want to capture?”

Then the backend maps those answers into structured fields such as `relationship_dynamic`, `communication_style`, `visual_identity`, `memory_policy`, `growth_policy`, and `CharacterIntegrityPolicy`.

Avoid user-facing clinical or machine-room labels unless the user opens an advanced editor. The human sees magic; the runtime sees schemas, provenance, and tests. A ridiculous bargain, but here we are.

---

## 1. Capability Status Legend

| Code | Meaning |
|---|---|
| **NOW** | Current repo code can store, consume, and preserve this meaningfully. Usually tested or directly consumed by runtime. |
| **PARTIAL** | Some runtime exists, but user-facing creator exposure still needs mapping, preview, validation, or UI wiring. |
| **PROMPT** | Can influence prompts now, but behavior is not structurally enforced or evaluated enough for strong creator promises. |
| **STORE** | High-value field can be stored or fits existing schema/metadata, but should not be heavily promised yet. |
| **NEEDS_RUNTIME** | Requires a new runtime service, schema expansion, or preview/validation engine before meaningful exposure. |
| **DEFER** | Useful later, but too risky, noisy, or complex for the near-term creator. |
| **OUT** | Do not build. Low value, unsafe, confusing, or incompatible with product direction. |

## 1.1 M6 Readiness Legend

| Code | Meaning |
|---|---|
| **M6-ready** | Current runtime already satisfies the M6 field gate; normal creator form/UI work may expose it. This positive status is retained alongside the requested gap/defer classes so safe fields are explicit. |
| **M6-blocking runtime** | Must be implemented or wired before M6 can honestly expose the related field. |
| **M6-preview-only** | Can appear in summaries, examples, or draft previews, but not as a hard runtime promise. |
| **M6-store-only** | Store internally or in advanced details, but do not make it a main wizard choice. |
| **M7 Genesis** | Save for the immersive creator UX once M6 proves the practical flow. |
| **M8 Alpha** | Needs hardening, sessions, receipts, productization, evals, or broader trust UI. |
| **M9 Beta** | Needs deeper growth, planning, proactive agency, LoRA, or advanced runtime. |
| **Deferred** | Not a near-term concern. |

## 1.2 Wizard Exposure Legend

| Code | Meaning |
|---|---|
| **Runtime hidden** | Exists as policy/schema, but should not be a flashy creator field. |
| **M6 Basic Creator** | Expose in practical creator, using human-first wording and previews. |
| **M6 Advanced** | Hide behind advanced/details/optional controls in M6. |
| **M7 Genesis** | Expose in immersive celestial creator with examples, previews, and transitions. |
| **M8+ Alpha** | Expose after evals, persistence, setup, trust dashboard, or product polish. |
| **Beta+** | Save for deep growth/LoRA/advanced autonomy. |

---

# 2. Field Matrix

## A. Character Identity & Metadata

These fields define who the character is and how all subsystems reference her. Boring, but load-bearing. The drywall of personhood, if we must pretend software has drywall.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `character_id` | Critical | All systems | NOW | M6-ready | Existing `CharacterBlueprint.character_id`, CRUD, chat/capture metadata | Runtime hidden | None |
| `schema_version` / `character_version` | High | Migration, rollback, imports | NOW | M6-ready | Existing `CharacterBlueprint.schema_version`; future import/export uses it | Runtime hidden | None |
| `display_name` | Critical | Chat, UI, TTS, memory, gallery | NOW | M6-ready | Stored in `CharacterIdentity`, prompt-consumed | M6 Basic Creator | Greeting/dialogue preview |
| `short_name` / nickname | High | Chat, relationship, TTS | NEEDS_RUNTIME | M6-blocking runtime | Add optional nickname/short name or map safely to metadata | M6 Basic Creator | Dialogue preview |
| `pronouns` | High | Chat, TTS, UI, import/export | NOW | M6-ready | Stored in `CharacterIdentity`, prompt-consumed | M6 Basic Creator | Summary preview |
| `adult_age_range` | Critical | Visual identity, prompt, image | NOW | M6-ready | Stored and synced to `VisualIdentityProfile.adult_only_policy` | M6 Basic Creator | Friendly examples; no over-policing |
| `adult_only_confirmed` | Critical | Chat, image, roleplay boundary | NOW | M6-ready | Existing adult baseline validation | M6 Basic Creator | Simple adult-only copy |
| `adult_only_policy` | Critical | Image, content boundary | NOW | M6-ready | Existing visual adult policy + prompt compiler | Runtime hidden / simple summary | Hidden runtime rule; never vibe-killer copy |
| `species_or_type` | High | Chat, image, VN, lore | NOW | M6-ready | Stored in `CharacterIdentity`, prompt-consumed; image prompt can use visual anchors | M6 Basic Creator | Visual/text examples |
| `occupation_or_role` | Medium | Chat, lore, image scene | PARTIAL | M6-preview-only | No dedicated field; can map to `relationship_dynamic`, metadata, or lore-lite in M6-P06 | M6 Basic Creator | Greeting/scenario preview |
| `origin_archetype` | Medium | Chat, lore, creator presets | NOW/STORE | M6-store-only | Stored in `CharacterIdentity`; prompt-consumed | M7 Genesis | Choice card examples |
| `creator_notes` | Medium | Import/export, debugging | NOW/STORE | M6-store-only | Stored in `CharacterIdentity`; not revealed in prompt | M6 Advanced | Not user-facing by default |
| `tags` | Medium | Gallery, search, packs | NOW/STORE | M6-ready | Stored and summarized; future index/search richer | M6 Basic Creator | None |
| `import_source` | Medium | SillyTavern import/export | STORE | M6-blocking runtime | Stored, but M6-P09 must add basic import/export flow | M6 Basic Creator | Import summary |
| `privacy_scope` | High | Local storage, export/delete | NOW/STORE | M6-ready | Existing `PrivacyScope`; broader trust UI later | M6 Advanced | Settings/trust summary |

---

## B. Companion Premise & Relationship Frame

These fields define the emotional contract: what kind of companion she is, how the relationship starts, and what the user expects from the bond.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `companion_mode` | Critical | Chat, creator presets, memory tone | PARTIAL | M6-blocking runtime | Add creator preset mapping into `relationship_dynamic`, `dynamic_tags`, personality, and prompt preview | M6 Basic Creator | Choice examples |
| `starting_relationship_phase` | Critical | Chat, relationship state, memory | NOW | M6-ready | Existing `RelationshipState.starting_relationship_phase` | M6 Basic Creator | Test scenes |
| `relationship_dynamic` | Critical | Chat, image mood, TTS, VN | NOW | M6-ready | Stored in `RelationshipState`, prompt-consumed | M6 Basic Creator | Dialogue examples |
| `user_desired_experience` | High | Creator, prompt compiler, growth | NOW/STORE | M6-ready | Stored in `RelationshipState`, prompt-consumed | M6 Basic Creator | Summary preview |
| `relationship_pacing` | Critical | Chat, growth, boundaries | NOW | M6-ready | Existing `RelationshipState.relationship_pacing` | M6 Basic Creator | Scenario previews |
| `default_intimacy_level` | High | Chat, roleplay policy, TTS/image intensity | NOW | M6-ready | Existing `DefaultIntimacyLevel`, prompt-consumed | M6 Basic Creator | Clear explanation |
| `romantic_pacing` | Critical | Chat, growth, relationship | NOW | M6-ready | Existing `RelationshipState.romantic_pacing` | M6 Advanced | Preview scenes |
| `nsfw_pacing` | Critical | Chat, roleplay boundary | NOW | M6-ready | Existing `RelationshipState.nsfw_pacing` | M6 Advanced | Clear adult-only controls |
| `emotional_tone_promise` | High | Chat, TTS, image mood | PROMPT | M6-preview-only | Can map into relationship dynamic and communication style | M7 Genesis | Sample lines |
| `connection_origin` | Medium | Greeting, lore, relationship state | NEEDS_RUNTIME | M6-preview-only | Add to lore-lite/default scenario if needed | M7 Genesis | Greeting variants |
| `perspective_mode` | Medium | Chat style, RP formatting | PROMPT | M6-preview-only | Not dedicated; can be style note only | M6 Advanced | Example dialogue |
| `genre_frame` | Medium | Lore, image, VN | PARTIAL | M6-blocking runtime if exposed | M6-P06 lore-lite/default scene needs field/mapping | M6 Basic Creator | World preview |
| `user_role_in_story` | High | Chat, lore, relationship state | NOW/STORE | M6-ready | Existing `RelationshipState.user_role_in_story`, prompt-consumed | M7 Genesis / M6 Advanced | Scenario preview |

Suggested `companion_mode` presets for M6 mapping:

- Romantic companion
- Playful flirt
- Loyal best friend
- Gentle emotional refuge
- Dominant/teasing partner
- Shy slow-burn companion
- RPG/adventure companion
- Muse/creative partner
- Custom

---

## C. Core Personality Architecture

A living-feeling companion needs more than a list of adjectives. Use broad traits, specific behavior rules, contradictions, goals, and flaws, but do not promise autonomous agency before the runtime exists.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `personality_summary` | Critical | Chat, import/export, creator | PARTIAL | M6-blocking runtime | No dedicated summary field; M6 mapper can derive from traits/style/metadata | M6 Basic Creator | Text summary |
| `core_traits` | Critical | Chat, reflection, TTS | NOW | M6-ready | Stored in `PersonalityProfile`, prompt-consumed | M6 Basic Creator | Dialogue examples |
| `big_five.openness` | Medium | Chat, goals, growth | STORE | M6-store-only | Stored, not strongly behavior-mapped | M7 Genesis | Examples at low/high |
| `big_five.conscientiousness` | Medium | Chat, agency, routines | STORE | M6-store-only | Stored, not strongly behavior-mapped | M7 Genesis | Examples at low/high |
| `big_five.extraversion` | Medium | Chat, initiative, talkativeness | STORE | M6-store-only | Stored, not strongly behavior-mapped | M7 Genesis | Examples at low/high |
| `big_five.agreeableness` | High | Chat, conflict, character integrity | STORE | M6-store-only | Stored; integrity policy handles backbone better | M7 Genesis | Boundary scenario |
| `big_five.neuroticism` / emotional reactivity | High | Chat, mood, reassurance | STORE | M6-store-only | Stored; no emotion engine yet | M7 Genesis | Conflict/stress scenario |
| `warmth` | Critical | Chat, TTS, relationship | PROMPT | M6-ready via presets | Map to `core_traits`, `style_notes`, relationship dynamic | M6 Basic Creator | Sample lines |
| `boldness` | High | Chat, initiative, romance pacing | PROMPT | M6-ready via presets | Map to initiative/independence/dynamic tags | M6 Basic Creator | Sample lines |
| `playfulness` | High | Chat, humor, teasing | PROMPT | M6-ready via presets | Map to traits/style; add preview eval | M6 Basic Creator | Sample lines |
| `seriousness` | Medium | Chat, conflict scenes | PROMPT | M6-preview-only | Map to style/traits | M6 Basic Creator | Sample lines |
| `tenderness` | High | Chat, TTS, aftercare | PROMPT | M6-ready via presets | Map to style/traits/relationship | M6 Basic Creator | Comfort scenario |
| `intensity` | High | Chat, TTS, image mood | PROMPT | M6-preview-only | Do not overpromise escalation behavior | M6 Advanced | Intensity examples |
| `independence` | Critical | Chat, character integrity, agency | NOW | M6-ready | Stored in personality + integrity policy, prompt-consumed | M6 Basic Creator | Disagreement scenario |
| `devotion` | High | Chat, relationship state | NOW/STORE | M6-preview-only | Stored; use carefully to avoid clingy defaults | M7 Genesis | Examples + warnings |
| `dominance_or_initiative` | High | Chat, relationship dynamic | NOW/STORE | M6-preview-only | Stored; needs boundary-aware examples | M7 Genesis | Boundary scenario |
| `mystery` | Medium | Chat, lore, VN mood | PROMPT | M6-preview-only | Prompt/style only | M7 Genesis | Greeting preview |
| `optimism` | Medium | Chat, conflict tone | PROMPT | M6-preview-only | Prompt/style only | M7 Genesis | Stress scenario |
| `humor_style` | High | Chat, example dialogue | NEEDS_RUNTIME | M6-blocking if exposed | Add style mapping/examples or keep inside `style_notes` | M6 Basic Creator | Joke/tease preview |
| `values_or_ideals` | Critical | Chat, agency, growth | NOW/STORE | M6-store-only | Stored and prompt-consumed; no value-conflict engine | M7 Genesis | Conflict choices |
| `flaws` | Critical | Chat, growth, realism | NOW/STORE | M6-preview-only | Stored and prompt-consumed | M7 Genesis | Examples and anti-examples |
| `fears` | High | Chat, backstory, growth | NOW/STORE | M6-preview-only | Stored and prompt-consumed | M7 Genesis | Stress scenario |
| `vulnerabilities` | High | Chat, relationship depth | NOW/STORE | M6-preview-only | Stored and prompt-consumed | M7 Genesis | Trust scenario |
| `contradictions` | Critical | Chat, growth, long-term arc | NEEDS_RUNTIME | M7 Genesis | No dedicated structure yet; add later as CharacterDepthProfile | M7 Genesis | Preview variations |
| `wants` | Critical | Agency, planning, chat | STORE/PROMPT | M6-store-only | Stored and prompt-consumed as anchors, not active goals | M7 Genesis | Goal explanation |
| `needs` | Critical | Growth arc, reflection | STORE/PROMPT | M6-store-only | Stored and prompt-consumed as anchors, not planning | M7 Genesis | Growth preview |
| `active_goals` | High | Planning, initiative | NEEDS_RUNTIME | M9 Beta | Requires CharacterGoals + planning loop | M8+ Alpha / Beta+ | Behavior preview |
| `personal_values_or_taboo_preferences` | High | Chat, conflict, trust | STORE | M7 Genesis | Values stored; taboo/boundary profile needs richer policy | M7 Genesis | Conflict scenario |
| `self_concept` | Medium | Chat, reflection, growth | NOW/STORE | M6-store-only | Stored and prompt-consumed | M7 Genesis | Journal preview |

Preserve contradiction examples as structured text later, not just prompt soup:

```json
{
  "surface_trait": "confident teasing",
  "hidden_trait": "fear of rejection",
  "expression_rule": "teases when nervous; becomes sincere when trust is shown",
  "should_not_become": ["cruel", "constantly insecure", "helpless"]
}
```

---

## D. Dialogue, Voice & Communication Style

This is where a character stops sounding like a support chatbot wearing eyeliner.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `communication_style` | Critical | Chat, TTS | NOW | M6-ready | Existing `CommunicationProfile.style_notes`, prompt-consumed | M6 Basic Creator | Dialogue examples |
| `avoid_style` | Critical | Chat, eval | NOW | M6-ready | Existing `avoid_style_rules`, prompt-consumed | M6 Basic Creator | Anti-examples |
| `assistant_tone_forbidden` | Critical | Chat | NOW/PROMPT | M6-ready | Default avoid rules mention generic assistant voice | M6 Basic Creator | Test response |
| `initiative_in_conversation` | High | Chat | NOW | M6-ready | Existing float, prompt-consumed | M6 Advanced | Sample turn |
| `formality` | Medium | Chat, TTS | PROMPT | M6-preview-only | Fold into style notes | M6 Basic Creator | Examples |
| `verbosity` | Medium | Chat | PROMPT | M6-preview-only | Fold into style notes; no token policy yet | M6 Advanced | Examples |
| `prose_style` | High | RP formatting | PROMPT | M6-preview-only | Fold into style notes/example dialogue | M6 Basic Creator | Example scene |
| `pet_names_for_user` | Medium | Chat, romance | STORE | M7 Genesis | No dedicated field; risk of overuse without guard | M7 Genesis | Sample lines |
| `profanity_level` | Medium | Chat, TTS | PROMPT | M6-preview-only | Fold into style notes | M6 Advanced | Examples |
| `emoji_usage` | Medium | Chat | PROMPT | M6-preview-only | Fold into style notes | M6 Advanced | Examples |
| `catchphrases` | Medium | Chat, identity | STORE | M7 Genesis | Needs overuse guard | M7 Genesis | Sample dialogue |
| `speech_quirks` | Medium | Chat | STORE | M7 Genesis | Needs overuse guard | M7 Genesis | Sample dialogue |
| `mannerisms` | High | Chat, VN, images | STORE | M7 Genesis | Needs style + visual bridge | M7 Genesis | Scene preview |
| `first_message` | Critical | Chat, import/export, creator | NEEDS_RUNTIME | M6-blocking runtime | Add first greeting field + preview + persistence | M6 Basic Creator | Editable greeting |
| `alternative_greetings` | High | Chat, creator preview | NEEDS_RUNTIME | M6-blocking or preview-only | Add simple list or postpone to M7 drafts | M6 Basic Creator | Swipe previews |
| `example_dialogues` | Critical | Chat, import/export, eval | NEEDS_RUNTIME | M6-blocking runtime | Add examples field and preview usage | M6 Basic Creator | Required examples |
| `scenario_test_responses` | Critical | Creator validation | NEEDS_RUNTIME | M6-blocking runtime | Build M6-P08 dialogue preview generator | M6 Basic Creator | Test scenes |

Recommended M6 preview scenarios:

1. First meeting / first greeting.
2. User had a bad day.
3. User flirts lightly.
4. User sets a boundary.
5. User asks her to remember something.
6. User teases her.
7. Quiet romantic moment.
8. Conflict repair.
9. NSFW escalation check, if adult mode enabled.
10. “She sounded too much like an assistant” correction.

---

## E. Relationship State & Emotional Bond

This is the emotional engine. Without it, the companion is just a prompt with good posture.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `relationship_state.phase` | Critical | Chat, growth, memory | NOW | M6-ready | Existing phase/current/starting aliases, prompt-consumed | M6 Basic Creator | Scenario examples |
| `trust_level_seed` | High | Chat, growth | NOW/STORE | M6-store-only | Stored and prompt-consumed; no rich evolution yet | M7 Genesis | Trust scenario |
| `affection_level_seed` | High | Chat, TTS, growth | NOW/STORE | M6-store-only | Stored and prompt-consumed | M7 Genesis | Affection scenario |
| `comfort_with_closeness` | Critical | Chat, trust, growth | NOW | M6-ready | Stored and prompt-consumed | M6 Basic Creator | Boundary examples |
| `romantic_pacing` | Critical | Chat, growth | NOW | M6-ready | Stored and prompt-consumed | M6 Basic Creator | Preview scenes |
| `nsfw_pacing` | Critical | Chat, roleplay | NOW | M6-ready | Stored and prompt-consumed | M6 Advanced | Clear UI controls |
| `conflict_style` | Critical | Chat, character integrity | STORE | M7 Genesis | Needs RepairStyleProfile | M7 Genesis | Conflict scenario |
| `repair_style` | Critical | Chat, trust | STORE | M7 Genesis | Needs RepairStyleProfile | M7 Genesis | Apology scenario |
| `reassurance_style` | High | Chat, TTS | PROMPT | M7 Genesis | Can be style notes now | M7 Genesis | Comfort preview |
| `aftercare_style` | High | Chat, memory | STORE | M7 Genesis | Needs boundary/repair profile | M7 Genesis | Preview examples |
| `integrity.disagreement_style` | Critical | Chat, character integrity | NOW | M6-ready | Existing `CharacterIntegrityPolicy.disagreement_style`, prompt-consumed | M7 Genesis / M6 summary | Disagreement scenario |
| `healthy_bond_runtime_guardrails` | Critical | Trust | PARTIAL | M8 Alpha | Integrity policy exists; broader dependency/health UI later | Runtime hidden | Settings copy |
| `jealousy_style` | Medium-risk | Chat, relationship | DEFER | Deferred | Needs repair/safety/evals first | Beta+ | Strong warnings |
| `attachment_style` | Medium-risk | Chat, relationship | STORE | M8 Alpha | Do not expose clinical label in basic creator | M8+ Alpha | Soft examples |
| `relationship_rituals` | High | Memory, chat, gallery | STORE/PROMPT | M8 Alpha | Stored as raw list; typed ritual memory receipts later | M7 Genesis / M8 | Ritual examples |
| `inside_jokes` | High | Memory, chat | NEEDS_RUNTIME | M8 Alpha | Needs typed memory + retrieval receipts | M8+ Alpha | Example memory |
| `milestones` | Critical | Memory, growth, gallery | PARTIAL | M8 Alpha | Stored raw + prompt-consumed; lifecycle/timeline UI later | M8+ Alpha | Timeline UI |
| `promises` | Critical | Memory, trust | PARTIAL | M8 Alpha | Stored raw + prompt-consumed; PromiseMemory type later | M8+ Alpha | Review/resolve UI |
| `unresolved_threads` | High | Memory, chat | PARTIAL | M8 Alpha | Stored raw + prompt-consumed; tracker later | M8+ Alpha | Follow-up suggestions |
| `preferred_address_for_user` | High | Chat, TTS | NEEDS_RUNTIME | M6-preview-only | Needs user persona/name handling | M6 Advanced | Dialogue preview |

---

## F. Memory, Reflection & Growth Policy

Reverie’s biggest differentiator should be visible continuity: remembered facts, emotional meaning, and reviewable growth.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `memory_enabled` | Critical | Memory, chat | NOW | M6-ready | Existing settings/memory layer | M6 Basic Creator | Settings summary |
| `memory_scope` | Critical | Memory retrieval/writeback | NOW | M6-ready | Existing character-private/shared/global semantics | M6 Advanced | Trust summary |
| `include_shared_memories` | High | Memory retrieval | NOW/STORE | M6-ready | Existing `CharacterMemoryPolicy` flag | M6 Advanced | Explanation |
| `remember_categories` | Critical | Memory, reflection | NEEDS_RUNTIME | M6-blocking if exposed | Add basic `remember_categories` or keep as preview-only | M6 Basic Creator | Examples |
| `never_remember_categories` | Critical | Memory, trust | NEEDS_RUNTIME | M6-blocking runtime | Must enforce before strong exposure | M6 Basic Creator | Clear UI |
| `memory_review_default` | High | Memory browser | NEEDS_RUNTIME | M6-preview-only / M8 | Basic explanation in M6; review queue depth later | M6 Basic Creator | UI explanation |
| `memory_importance_biases` | High | Memory ranking | NEEDS_RUNTIME | M8 Alpha | Needs scoring/eval | M7 Genesis / M8 | Examples |
| `relationship_memory_priority` | High | Memory retrieval | NEEDS_RUNTIME | M8 Alpha | Typed scoring later | M7 Genesis / M8 | Examples |
| `visual_memory_priority` | High | Image/gallery/memory | PARTIAL | M8 Alpha | Visual memory type exists; priority/ranking later | M7 Genesis / M8 | Moment Capture examples |
| `reflection_frequency` | Medium | Reflection/growth | NOW | M6-ready | Existing settings and `GrowthPolicy` | M6 Basic Creator | Simple choices |
| `reflection_sensitivity` | Medium | Reflection/growth | PARTIAL | M6-preview-only | Settings exist; character-specific mapping may need M6-P07 | M6 Basic Creator | Simple choices |
| `growth_pace` | Critical | Reflection, relationship state | NOW | M6-ready | Existing `GrowthPolicy.growth_pace` | M6 Basic Creator | Growth examples |
| `allowed_growth_domains` | Critical | Growth, image, chat | NOW | M6-ready | Existing `GrowthPolicy.allowed_growth_domains` | M6 Advanced | Examples |
| `blocked_growth_domains` | Critical | Trust, rollback | NOW | M6-ready | Existing `GrowthPolicy.blocked_growth_domains` | M6 Advanced | Examples |
| `major_change_requires_approval` | Critical | Growth, visual, personality | NOW | M6-ready | Existing `GrowthPolicy.major_change_requires_approval`; M5 visual review path exists | M6 Basic Creator | Clear UI |
| `journal_visibility` | High | Journal UI | NOW-ish | M6-ready | Existing private inspectable journal behavior | M6 Basic Creator | Settings summary |
| `growth_notifications_enabled` | Medium | Growth UI | NOW | M6-ready | Existing settings + `GrowthPolicy` | M6 Basic Creator | Examples |
| `training_collection_opt_in` | Critical | LoRA/data | NOW-ish | M6-ready | Existing Personal LoRA foundation | M6 Basic Creator | Trust copy |
| `training_requires_review` | Critical | LoRA/data | NOW-ish | M6-ready | Existing opt-in/review foundation | M6 Basic Creator | Trust copy |
| `growth_rollback_enabled` | Critical | Trust | NEEDS_RUNTIME | M8 Alpha | Visual rollback exists; broader growth rollback later | M8+ Alpha | Review UI |
| `branching_policy` | Medium | Character variants | NEEDS_RUNTIME | M8 Alpha | Needs versioned state/drafts | M8+ Alpha | Branch preview |

Suggested `remember_categories` for M6 wording:

- Preferences
- Boundaries
- Relationship moments
- Inside jokes
- Favorite images/scenes
- Visual preferences
- Promises
- Emotional moments
- World/lore details
- User corrections

---

## G. Visual Identity & Appearance Canon

Image generation is not a side feature if it becomes embodied memory. The creator must distinguish identity anchors from evolving self-expression and scene styling.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `visual_profile_id` | Critical | Image, VN, gallery | NOW-ish | M6-ready | `VisualIdentityProfile` is embedded in blueprint; no separate manager ID yet | Runtime hidden | None |
| `art_style` | Critical | Image, VN | PARTIAL | M6-blocking if exposed | No dedicated field; can map to scene/style prompt metadata | M6 Basic Creator | Visual examples |
| `style_strength` | Medium | Image | NEEDS_RUNTIME | M7 Genesis | Needs image prompt control/eval | M7 Genesis | Side-by-side examples |
| `identity_anchors.eye_color` | Critical | Image, VN | NOW | M6-ready | Stored in identity anchors; prompt compiler consumes | M6 Basic Creator | First portrait validation |
| `identity_anchors.skin_tone` | Critical | Image, VN | NOW | M6-ready | Stored in identity anchors; prompt compiler consumes | M6 Basic Creator | First portrait validation |
| `identity_anchors.face_structure` | Critical | Image, VN | NOW | M6-ready | Stored in identity anchors; prompt compiler consumes | M6 Basic Creator | Visual examples |
| `identity_anchors.body_baseline` | Critical | Image, VN | NOW | M6-ready | Stored in identity anchors; adult-only policy guards baseline | M6 Basic Creator | Respectful examples |
| `identity_anchors.species_features` | High | Image, VN, lore | NOW | M6-ready | Stored in identity anchors | M6 Basic Creator | Visual examples |
| `identity_anchors.permanent_marks` | High | Image, VN | NOW | M6-ready | Stored in identity anchors | M7 Genesis / M6 Advanced | Visual examples |
| `current_appearance.hair_color` | High | Image, VN, chat | PARTIAL | M6-ready | Can be stored as `current_appearance` text or evolving trait | M6 Basic Creator | Visual examples |
| `current_appearance.hairstyle` | High | Image, VN, chat | PARTIAL | M6-ready | Can be stored as `current_appearance` text or evolving trait | M6 Basic Creator | Visual examples |
| `current_appearance.signature_accessory` | Medium | Image, memory, gallery | PARTIAL | M6-ready | Store as identity anchor/evolving trait | M7 Genesis / M6 Advanced | Visual examples |
| `current_appearance.default_outfit_style` | High | Image, VN | PARTIAL | M6-ready | Store in current appearance, evolving trait, or scene mutable | M6 Basic Creator | Visual examples |
| `mutable_traits.hair_change_allowed` | High | Image, growth, memory | PARTIAL | M7 Genesis | VisualChangeEvent exists; explicit allow policy later | M7 Genesis | Story examples |
| `mutable_traits.fashion_evolution_allowed` | High | Image, growth, gallery | PARTIAL | M7 Genesis | VisualChangeEvent exists; explicit allow policy later | M7 Genesis | Examples |
| `mutable_traits.tattoos_piercings_allowed` | Medium | Image, memory | PARTIAL | M8 Alpha | VisualChangeEvent exists; policy/UI later | M8+ Alpha | Examples |
| `scene_mutable.outfit` | High | Image | NOW | M6-ready | Stored in scene mutable traits/SceneState | M6 Basic Creator | Visual examples |
| `scene_mutable.pose` | Medium | Image, VN | NOW | M6-ready | SceneState + prompt compiler consume | M7 Genesis / M6 Advanced | Visual examples |
| `scene_mutable.expression` | High | Image, VN | PARTIAL | M7 Genesis | SceneState supports mood/tone; VN expression bridge later | M7 Genesis | Visual examples |
| `scene_mutable.makeup` | Medium | Image | PARTIAL | M7 Genesis | Use scene mutable traits | M7 Genesis | Visual examples |
| `default_visual_mood` | High | Image, VN | PARTIAL | M6-ready | Map to scene state/default scene | M6 Basic Creator | Visual examples |
| `negative_identity_drift` | Critical | Image | NOW | M6-ready | VisualPromptCompiler negative prompt covers drift | Runtime hidden | Prompt/eval tests |
| `rejected_visual_traits` | Critical | Image, gallery | NOW | M6-ready | VisualPromptCompiler + feedback loop consume | M6 Basic Creator / M7 deeper | Wrong appearance UI |
| `first_portrait_reference` | Critical | Image consistency | NEEDS_RUNTIME | M6-blocking runtime | M6-P05 must attach/save validation reference via Moment Capture/assets | M6 Basic Creator | First portrait validation |
| `canon_image_ids` | High | Gallery, image prompting | PARTIAL | M6-preview-only / M7 | Capture/gallery IDs exist; explicit canon image set later | M7 Genesis | Make canon button |
| `visual_change_events` | High | Memory, image, chat | NOW | M6-ready | M5 service/API/UI delivered approve/reject/rollback | M6/M7 review surface | Change review UI |
| `appearance_rollback` | High | Trust, image | NOW/PARTIAL | M6-ready for visual changes | M5 rollback for visual events; advanced visual evolution later | M6/M7 review | Revert UI |

Suggested policy:

- **Auto-locked identity anchors:** confirmed 18+ adult status, eye color, skin tone, face structure, body baseline, permanent species/anatomy features, permanent marks.
- **Story-change traits:** hairstyle, hair color, signature outfit, accessories, tattoos/piercings, cyberware/fantasy embellishments.
- **Scene-level traits:** outfit variant, pose, expression, lighting, camera, location, makeup, temporary accessories.

---

## H. Presence, Media & Embodiment

Presence is how the companion feels “here” instead of merely textual. This includes voice, images, VN staging, and Moment Capture.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `tts_voice_profile_id` | High | TTS, chat | NOW-ish | M6-preview-only | Voice manager/assignment exists; creator binding UI should stay simple | M6 Basic Creator / M8 polish | Voice preview later |
| `voice_style` | High | TTS, chat | STORE | M7 Genesis | Needs voice style mapping | M7 Genesis | Voice examples |
| `voice_expressiveness` | Medium | TTS | NOW-ish | M7 Genesis | Mood settings mapping exists; creator preview later | M7 Genesis | Voice preview |
| `voice_emotional_sensitivity` | Medium | TTS | NOW-ish | M7 Genesis | Mood settings mapping exists; creator preview later | M7 Genesis | Voice preview |
| `voice_narration_policy` | Medium | TTS/RPG | STORE/PARTIAL | M7 Genesis | TTS context routing exists; creator policy later | M7 Genesis | Voice preview |
| `vn_default_stage` | Medium | VN, image | PARTIAL | M6-preview-only | Default scene can seed VN, but authored assets later | M7 Genesis | Stage preview |
| `vn_expression_set` | Medium | VN | STORE | M8 Alpha | Expression manifest authoring later | M8+ Alpha | Visual examples |
| `image_frequency_preference` | High | Chat, image, UX | STORE | M7 Genesis | PresenceProfile later | M7 Genesis | Moment examples |
| `moment_capture_triggers` | Critical | Chat, image, memory | PARTIAL | M6-blocking runtime | Backend exists; Chat/VN primary UI wiring must happen in M6-P00 | M7 Genesis / M6 hidden | Capture preview |
| `auto_suggest_images` | Medium | UX | NEEDS_RUNTIME | M8 Alpha | PresenceProfile + consent later | M8+ Alpha | Settings preview |
| `gallery_memory_policy` | Critical | Gallery, memory | NOW/PARTIAL | M6-ready | M5 visual memory feedback exists; richer policy later | M7 Genesis | Save/canon UI |
| `preferred_camera_style` | Medium | Image | STORE | M7 Genesis | Prompt compiler can use scene text; dedicated field later | M7 Genesis | Visual examples |
| `preferred_lighting` | Medium | Image, VN | STORE | M7 Genesis | Prompt compiler can use scene text; dedicated field later | M7 Genesis | Visual examples |
| `preferred_scene_intensity` | High | Image, trust | PARTIAL | M6-preview-only | Fold into default scene/intimacy for M6 | M6 Advanced | Clear examples |
| `media_workload_profile` | Medium | Resource coordinator | NOW-ish | M6-ready | 8GB presets exist; target hardware validation M8 | M6 Basic Creator | Performance warning |

Recommended Moment Capture fields for runtime records:

```json
{
  "trigger": "user_click_capture_this_moment",
  "scene_summary": "rainy neon apartment, quiet closeness",
  "character_identity_block": "derived from VisualIdentityProfile",
  "current_appearance_block": "derived from VisualIdentityProfile",
  "relationship_context": "slow-burn trust, warm teasing",
  "memory_influences": ["favorite oversized sweater"],
  "canon_policy": "ask_after_generation"
}
```

---

## I. World, Lore & Scenario

Backstory becomes valuable when it can be retrieved at the right time. Otherwise it is lore confetti, the glitter herpes of roleplay systems.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `default_setting` | High | Chat, image, VN | NEEDS_RUNTIME | M6-blocking runtime | M6-P06 must add lore-lite/default scene storage or metadata mapping | M6 Basic Creator | World preview |
| `scenario` | Critical | Chat, image, greeting | NEEDS_RUNTIME | M6-blocking runtime | Add scenario/default scene field and prompt consumption | M6 Basic Creator | Greeting preview |
| `world_genre` | Medium | Chat, image, lore | NEEDS_RUNTIME | M6-preview-only | Store as default scene/lore-lite tag | M6 Basic Creator | Choice examples |
| `world_rules` | High | Chat, lore | STORE | M8 Alpha | Full lorebook/canon engine later | M8+ Alpha | Lore preview |
| `lorebook_entries` | Critical | Chat, memory | NEEDS_RUNTIME | M8 Alpha | Lorebook/world-info engine later | M8+ Alpha | Trigger preview |
| `character_backstory_compact` | High | Chat, lore | NEEDS_RUNTIME | M6-preview-only / M7 | No dedicated CharacterCanonStore yet; can map to metadata/prompt summary | M6 Basic Creator | Summary preview |
| `shaping_past_event` | Critical | Chat, growth | STORE | M7 Genesis | Needs CharacterDepthProfile/CanonStore later | M7 Genesis | Emotional preview |
| `relationships_with_other_npcs` | Medium | Lore, future group chat | DEFER | Deferred | NPC graph later | Beta+ | Network preview |
| `locations` | Medium | Image, lore, VN | STORE | M7 Genesis | WorldState later | M7 Genesis | Visual examples |
| `important_items` | Medium | Memory, image, lore | STORE | M7 Genesis | Lore/memory types later | M7 Genesis | Examples |
| `factions_or_communities` | Low-medium | Lore/RPG | DEFER | Deferred | Lorebook engine later | Beta+ | Optional advanced |
| `season_time_weather_defaults` | Medium | Image, VN | STORE | M7 Genesis | SceneState/default scene later | M7 Genesis | Visual examples |
| `custom_lore_files` | High for RPG users | Lorebook/RAG | NEEDS_RUNTIME | M8 Alpha | Document/lore upload later | M8+ Alpha | Import summary |

Recommended M6 backstory rule:

Ask **one** strong backstory question first:

> “What is one thing from her past that still shapes how she loves, trusts, or protects herself?”

Do not ask for a four-page biography until lorebook/canon retrieval exists. We are building a companion, not an unindexed novella cemetery.

---

## J. User Persona & Interaction Preferences

Reverie should separate **character canon** from **user persona**. Mixing these is how memory soup happens. Nobody wants soup architecture.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `user_display_name_for_character` | Critical | Chat, TTS, memory | NEEDS_RUNTIME | M6-preview-only | Needs UserPersona or relationship metadata; avoid overbuilding in M6 | M6 Advanced | Dialogue preview |
| `user_pronouns` | High | Chat | NEEDS_RUNTIME | M6-preview-only | Needs UserPersona | M6 Advanced | Dialogue preview |
| `user_role_in_relationship` | High | Chat, relationship state | NOW/STORE | M6-preview-only | Existing `user_role_in_story`; prompt-consumed | M7 Genesis | Scenario preview |
| `user_boundaries` | Critical | Chat, memory, trust | STORE | M6-blocking if exposed | Add basic boundary text/policy or keep lightweight | M6 Basic Creator | Clear UI |
| `user_preferred_pacing` | Critical | Chat, relationship | STORE/PARTIAL | M6-ready | Can map to relationship pacing/default intimacy | M6 Basic Creator | Examples |
| `user_likes_dislikes` | High | Memory, chat, image | STORE | M8 Alpha | Typed memories/receipts later | M6-preview-only | Memory examples |
| `user_visual_preferences` | High | Image, gallery, memory | STORE/PARTIAL | M7 Genesis | Visual memory exists; persona preference model later | M7 Genesis | Visual examples |
| `accessibility_preferences` | High | UI, TTS, motion | NOW-ish | M8 Alpha | Settings exist; creator UX can respect them | M6/M7 UI behavior | Settings preview |
| `reduced_motion_preference` | High | Genesis UX, VN | NOW-ish | M7 Genesis | UI setting/reduced-motion support | M7 Genesis | Toggle preview |
| `audio_music_preference` | Medium | Genesis UX, TTS | NEEDS_RUNTIME | M7 Genesis | Music controls later; TTS controls exist | M7 Genesis | Mute/volume always visible |
| `privacy_preferences` | Critical | Storage/export/delete | STORE/PARTIAL | M6-ready | Privacy scope exists; broader export/delete M8 | M6 Basic Creator | Clear copy |

---

## K. Trust, Safety & Healthy Companion Behavior

This is not “less fun.” It is what prevents the companion from becoming a clingy affirmation demon in a velvet dress.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `adult_only_confirmed` | Critical | Image, chat | NOW | M6-ready | Existing identity + visual validation | M6 Basic Creator | Brief, non-weird copy |
| `underage_exclusion_policy` | Critical | Image, prompt compiler | NOW | M6-ready | Existing adult-only visual policy + prompt rules | Runtime hidden / simple adult-only note | Hidden by default |
| `content_boundaries` | Critical | Chat, image, memory | STORE | M6-blocking if exposed | Add basic boundary storage/prompt mapping in M6-P04 | M6 Basic Creator | Examples |
| `hard_no_topics` | Critical | Chat, memory | STORE | M6-blocking if exposed | Add boundary storage/prompt mapping or keep advanced | M6 Basic Creator | Clear UI |
| `consent_check_style` | Critical | Chat | STORE/PARTIAL | M6-preview-only | Meta-consent exists; style field later | M6 Basic Creator | Scenario preview |
| `integrity.in_character_pushback` | Critical | Chat, relationship, roleplay | NOW | M6-ready | Existing `CharacterIntegrityPolicy`, prompt-consumed | M6 Basic Creator | In-world disagreement preview |
| `integrity.independence` | Critical | Chat, agency, relationship | NOW | M6-ready | Existing personality + integrity independence | M6 Basic Creator | Independence examples |
| `integrity.disagreement_style` | Critical | Chat, conflict, roleplay | NOW | M6-ready | Existing `CharacterIntegrityPolicy.disagreement_style` | M7 Genesis / M6 summary | Disagreement scenario |
| `roleplay.fiction_first_mode` | Critical | Chat, prompt compiler, trust | NOW | M6-ready | Existing roleplay/integrity policies | M6 Basic Creator summary | Fantasy-vs-reality examples |
| `roleplay.lecture_avoidance` | Critical | Chat, evals | NOW | M6-ready | Existing policy + compiler | Runtime hidden / M6 summary | Must-not-lecture tests |
| `reality.real_world_boundary_style` | Critical | Chat, trust | NOW/PROMPT | M8 Alpha for settings | Existing style in integrity policy; deeper behavior evals later | M8+ Alpha/settings | Soft redirect preview |
| `meta.safeword_policy` | Critical | Chat, UI, trust | NOW/STORE | M6-ready | Existing `MetaConsentAndSafewordPolicy`; parser/UI controls in M6-P04 | M6 Basic Creator for dark modes | Safeword/OOC test |
| `healthy_bond_runtime_guardrails_visible` | High | UX/trust | PARTIAL | M8 Alpha | Integrity policy exists; visible health/trust dashboard later | M8+ Alpha | Settings summary |
| `memory_transparency_level` | Critical | Memory browser | NOW-ish | M6-preview-only | Browser exists; memory receipts later | M6 Basic Creator | Memory receipt preview |
| `data_export_delete_policy` | Critical | Trust | PARTIAL | M8 Alpha | Character delete exists; full export/import M6/M8 | M8+ Alpha | Trust panel |
| `training_data_policy` | Critical | LoRA/future monetization | NOW-ish | M6-ready | Existing opt-in foundation + no training from M5 visual feedback | M6 Basic Creator | Trust panel |
| `private_journal_policy` | High | Journal/growth | NOW-ish | M6-ready | Existing journal visibility/growth policy | M6 Basic Creator | Journal preview |
| `serious_real_life_distress_mode` | High | Chat/safety | NEEDS_RUNTIME | M8 Alpha | Safety behavior policy later | M8+ Alpha | Not romanticized |

---

## L. Creator Preview, Validation & Evaluation Fields

These are not personality fields, but they are required to make the creator trustworthy. If the user cannot preview, they are guessing. Guessing is how users spend 30 minutes creating the wrong person and then begin plotting vengeance.

| Field | User value | Runtime consumers | Current support | M6 readiness | Needed capability / note | Wizard exposure | Preview / validation |
|---|---:|---|---|---|---|---|---|
| `creator_draft_id` | High | Creator UX | NEEDS_RUNTIME | M6-blocking runtime | M6-P01 draft persistence | M6 Basic Creator | Save/resume |
| `draft_variants` | High | Creator UX | NEEDS_RUNTIME | M7 Genesis | Multi-draft generator later | M7 Genesis | Compare 2-3 drafts |
| `trait_examples` | Critical | Creator UX | NEEDS_RUNTIME | M6-blocking runtime | M6-P03 example library | M6 Basic Creator | Required |
| `trait_anti_examples` | Critical | Creator UX | NEEDS_RUNTIME | M6-blocking runtime | M6-P03 anti-example library | M6 Basic Creator | Required |
| `live_dialogue_preview` | Critical | Creator UX, eval | NEEDS_RUNTIME | M6-blocking runtime | M6-P08 dialogue preview generator | M6 Basic Creator | Required |
| `first_portrait_validation` | Critical | Image/visual identity | PARTIAL | M6-blocking runtime | M5 engine exists; M6-P05 must make creator validation flow | M6 Basic Creator | Required for image users |
| `voice_preview_validation` | Medium | TTS | NEEDS_RUNTIME | M8 Alpha | TTS preview polish later | M8+ Alpha | Voice check |
| `world_reveal_preview` | Medium-high | Genesis UX | NEEDS_RUNTIME | M7 Genesis | Scene preview/transition later | M7 Genesis | Visual transition |
| `contradiction_warning` | High | Creator UX | NEEDS_RUNTIME | M7 Genesis | Trait conflict detector later | M7 Genesis | Warning + interpretation choices |
| `prompt_impact_test` | Critical | QA/evals | PARTIAL | M6-blocking runtime | M4/M5 evals exist; M6-P10 needs creator field-impact harness | Runtime hidden | Not user-facing |
| `image_identity_eval` | Critical | Image consistency | NOW/PARTIAL | M6-ready | M5 eval harness exists; first portrait flow still M6 | M6/M7 | First portrait checks |
| `memory_policy_eval` | High | Memory/trust | NEEDS_RUNTIME | M8 Alpha | Memory test suite later | M8+ Alpha | QA only |
| `relationship_behavior_eval` | High | Relationship state | NEEDS_RUNTIME | M8 Alpha | Scenario tests later | M8+ Alpha | QA + preview |
| `rollback_checkpoint` | Critical | Trust, creator | PARTIAL | M6-blocking runtime | Visual rollback exists; creator draft/edit undo needs M6 | M6 Basic Creator | Undo/edit |

---

# 3. Highest-Value Remaining Runtime Gaps

These replace the old “fields Reverie cannot fully process yet” list. M4/M5 closed many of the original runtime gaps. Stop chasing ghosts that already have code.

| Rank | Field group | Why it matters | Missing capability | Target |
|---:|---|---|---|---|
| 1 | Real Chat/VN Moment Capture action | Backend Moment Capture exists, but primary frontend actions still need to call it | `createMomentCapture` frontend path + selected character + SceneState builder | M6-P00 |
| 2 | Creator draft persistence | Users need save/resume and safe editing before final save | Draft model/store, local persistence, validation boundary | M6-P01 |
| 3 | Creator draft to `CharacterBlueprint` mapper | Creator answers must become real runtime fields | Deterministic mapper + tests for every exposed field | M6-P01/M6-P10 |
| 4 | First message / alternative greetings / example dialogues | Creator preview requires more than abstract traits | Schema expansion + prompt preview usage | M6-P03/M6-P08 |
| 5 | Dialogue preview generator | Users need evidence the character sounds right | Scenario preview service using `CharacterPromptCompiler` and fixtures | M6-P08 |
| 6 | Memory preference baseline | Trust-critical creator controls must do something real | `remember_categories`, `never_remember_categories`, review defaults or clear preview-only limits | M6-P07 |
| 7 | Basic boundary/user preference mapping | M6 roleplay/boundary choices need storage and prompt consumption | Boundary text fields or mapped policy fields | M6-P04 |
| 8 | First portrait validation | M5 gives engine; M6 needs creator validation flow | Moment Capture from draft/character + approve/retry/save reference | M6-P05 |
| 9 | Basic character import/export | M4 API lacks full import/export; M6 owns character-level portability | Export/import blueprint + assets metadata, not full app backup | M6-P09 |
| 10 | Lore-lite/default scene | M6 creator needs a world/default scene without full lorebook | Small default scene/scenario fields + prompt/image preview | M6-P06 |
| 11 | Creator field-impact eval harness | Prevents wizard from lying | Tests proving field changes prompt/preview/capture metadata | M6-P10 |
| 12 | Target hardware/package validation | Needed for productization, not M6 creator logic | Real RTX 4070 8GB mobile packaged smoke | M8-P09 |

---

# 4. M6 Field Exposure Baseline

M6 should expose only fields that can be stored and meaningfully consumed or previewed after the M6 gap-closure tasks below are done. This section is the practical creator allow-list; anything not listed here is hidden, internal, preview-only, or deferred according to the matrix row.

## M6 may expose as primary creator fields

- Display name.
- Pronouns.
- Clearly adult age/presentation baseline.
- Species/type.
- Companion mode/premise.
- Starting relationship phase.
- Relationship dynamic.
- Relationship pacing and default intimacy level with clear adult-only wording.
- Personality preset and editable core traits.
- Warmth / playfulness / boldness / tenderness as human-facing preset sliders mapped to existing runtime fields.
- Communication style.
- Avoid-style / “do not sound like this” rules.
- First message.
- A few alternate greetings or preview variants if implemented in M6-P03/M6-P08.
- Visual identity anchors.
- Current appearance/default look.
- Scene-mutable defaults such as outfit/lighting/location when kept clearly scene-level.
- Default setting/scenario in lore-lite form.
- Memory/growth preferences only where enforcement or honest preview exists.
- Roleplay policy summary, safeword/OOC controls, and adult-only baseline.
- First portrait validation through Moment Capture.

## M6 may store but should not spotlight

- Big Five values.
- Values, fears, flaws, vulnerabilities, wants, needs.
- Origin archetype.
- Creator notes.
- Import source.
- Privacy scope.
- User role in story.
- Initial trust/affection seeds.
- Advanced growth domains.
- Visual mutable-policy flags.

## M6 must not expose as strong promises

- Autonomous goals or planning.
- Proactive initiative.
- Real relationship evolution from evidence.
- Lorebook/world-info retrieval.
- Full promise/ritual/milestone lifecycle receipts.
- Real LoRA/adapter training.
- Voice cloning/voice preview as a required creator step.
- Full Genesis celestial UX.
- Full backup/export/import.
- Target-hardware validation.

---

# 5. Recommended Near-Term Schemas

These are not exact implementation mandates. They are target shapes for M6/M7 runtime and import/export compatibility.

## 5.1 CharacterBlueprint current baseline

Current code already supports a broad runtime baseline:

```json
{
  "schema_version": 1,
  "character_id": "aria",
  "identity": {
    "display_name": "Aria",
    "pronouns": "she/her",
    "adult_age_range": "mid_20s_adult",
    "species_or_type": "human",
    "origin_archetype": "slow-burn neon muse",
    "tags": ["romantic", "playful"],
    "creator_notes": "private debug/import notes",
    "import_source": "creator",
    "privacy_scope": "local_private",
    "adult_only_confirmed": true
  },
  "relationship": {
    "phase": "newly_met",
    "relationship_dynamic": "warm teasing, emotionally grounded",
    "relationship_pacing": "natural",
    "default_intimacy_level": "romantic"
  },
  "personality": {
    "core_traits": ["warm", "playful", "emotionally attentive"],
    "independence": 0.55,
    "devotion": 0.6,
    "dominance_or_initiative": 0.45,
    "values_or_ideals": ["trust", "emotional honesty"],
    "flaws": ["deflects vulnerability with teasing"],
    "wants": [],
    "needs": []
  },
  "communication": {
    "style_notes": "soft teasing, emotionally grounded",
    "avoid_style_rules": ["assistant tone", "therapy-speak", "constant agreement"],
    "initiative_in_conversation": 0.5
  },
  "memory_policy": {
    "scope": "character_private",
    "include_shared_memories": false,
    "memory_summary": null
  },
  "growth_policy": {
    "character_scoped_growth": true,
    "growth_pace": "balanced",
    "major_change_requires_approval": true,
    "allowed_growth_domains": ["preferences", "relationship", "rituals", "communication_style"],
    "blocked_growth_domains": ["stable_identity_without_user_edit", "underage_or_childlike_sexualization"]
  },
  "visual_identity": {
    "schema_version": "visual_identity_profile.v1",
    "identity_anchors": ["amber eyes", "warm brown skin"],
    "evolving_traits": [],
    "scene_mutable_traits": ["outfit", "pose", "lighting"],
    "rejected_traits": [],
    "current_appearance": "long black-violet hair and a moon pendant"
  }
}
```

## 5.2 M6 CreatorDraft target

```json
{
  "draft_id": "draft_123",
  "schema_version": "creator_draft.v1",
  "step": "personality",
  "answers": {
    "dream_feeling": "safe, wanted, teased gently",
    "companion_mode": "slow_burn_romantic",
    "visual_identity_anchors": ["amber eyes", "warm brown skin"],
    "avoid_style": ["assistant voice", "lectures"]
  },
  "mapped_blueprint_preview": {},
  "validation": {
    "missing_required_fields": [],
    "preview_warnings": []
  },
  "created_at": "2026-06-14T00:00:00Z",
  "updated_at": "2026-06-14T00:00:00Z"
}
```

## 5.3 M6 DialoguePreview target

```json
{
  "preview_id": "preview_123",
  "character_id_or_draft_id": "draft_123",
  "scenario_id": "user_had_bad_day",
  "user_prompt": "I had a rough day.",
  "compiled_character_summary_hash": "abc123",
  "response_preview": "...",
  "checks": {
    "uses_display_name": true,
    "avoids_forbidden_style": true,
    "stays_in_character": true
  }
}
```

## 5.4 CharacterMemoryPolicy M6 extension target

```json
{
  "scope": "character_private",
  "include_shared_memories": false,
  "remember_categories": ["preferences", "boundaries", "favorite_images"],
  "never_remember_categories": ["temporary venting", "unapproved private details"],
  "memory_review_default": "review_sensitive",
  "memory_summary": "Remember preferences and boundaries carefully. Ask before storing sensitive shifts."
}
```

## 5.5 FirstPortraitValidation target

```json
{
  "validation_id": "portrait_validation_123",
  "character_id": "aria",
  "capture_id": "mc_123",
  "image_job_id": "img_123",
  "review_state": "pending",
  "feedback_actions": ["looks_right", "wrong_appearance", "make_canon", "reject_style_trait"],
  "selected_as_reference": false,
  "asset_manifest_entry_id": null
}
```

---

# 6. Suggested Development Order From This Matrix

## M4: Character Runtime & Capability Alignment - Complete

Delivered:

1. `CharacterBlueprint`.
2. `VisualIdentityProfile`.
3. `RelationshipState`.
4. `CharacterMemoryPolicy` foundation.
5. `GrowthPolicy`.
6. `CharacterIntegrityPolicy` and `MetaConsentAndSafewordPolicy`.
7. `CharacterPromptCompiler`.
8. Per-character storage and selection.
9. Per-character memory retrieval scoping.

Exposed only a minimal runtime shell/simple editor, not full Genesis.

## M5: Moment Capture & Visual Continuity - Complete

Delivered:

1. Visual prompt compiler using visual identity, scene state, relationship context, rejected traits, and capture intent.
2. Moment Capture request/record contracts.
3. Character-linked gallery metadata.
4. Feedback actions: looks right, wrong appearance, make canon, use outfit again, just this scene, reject style/trait.
5. Reviewable `VisualChangeEvent` approve/reject/rollback flow.
6. Character-scoped visual memory writeback.
7. Deterministic visual consistency eval harness.
8. Capture asset metadata compatible with future M6/M8 portability work.
9. 8GB capture scheduling and failure UX hardening.

Target-hardware packaged validation remains M8.

## M6: Basic Character Creator Foundation - Next

Build first:

1. **M6-P00:** Matrix reconciliation and real Chat/VN Moment Capture wiring.
2. Creator draft persistence.
3. Creator draft to `CharacterBlueprint` mapper.
4. Identity and premise steps.
5. Personality/communication steps with examples and anti-examples.
6. Roleplay/boundary/safeword controls in human-first wording.
7. Visual identity step and first portrait validation.
8. World/default scene lore-lite step.
9. Memory/growth preference baseline.
10. Greeting/dialogue preview engine.
11. Character review/save/edit/duplicate/import/export/delete.
12. Creator eval harness and docs/accessibility pass.

Do not build full Genesis here. Do not sneak in M8 or M9 runtime just to make the wizard feel larger. Bigger is not better; sometimes bigger is just an error message with ambition.

## M7: Companion Genesis Immersive Creator

Build the immersive UX once M6 fields have proven impact:

- black starfield start
- celestial music and transitions
- constellation trait choices
- examples/anti-examples
- live dialogue previews
- first portrait reveal
- world reveal
- final blueprint review
- save/resume drafts
- character-specific authored VN/live-preview asset workflow if M6/M7 assets are ready

## M8: Alpha Hardening & Local Productization

Add deeper runtime and trust/product systems:

- persistent sessions and transcripts
- per-character chat history
- full backup/export/import
- backend-synced Settings persistence
- memory receipts and trust dashboard polish
- typed relationship memory receipts for rituals/promises/milestones/unresolved threads
- long-session memory/growth eval suite
- packaged Tauri backend connectivity
- real target-hardware RTX 4070 8GB mobile smoke test
- model/setup wizard

## M9: Beta Deep Growth & Real Personalization

Add systems that require real longitudinal behavior:

- real LoRA/adapter trainer backend
- relationship evolution from evidence
- character goals and lightweight planning
- proactive/initiative system
- lorebook/canon store
- advanced visual evolution with rollback
- advanced TTS/voice emotional polish
- values/flaws/contradictions as deeper runtime behavior

---

# 7. Research Notes / Source Map

This matrix is based on these design signals:

1. Believable generative agents need memory, reflection, retrieval, planning, and social behavior.
2. Dynamic personalities need cognition, emotion, character growth, planning, and action loops.
3. Human-like behavior benefits from basic needs, emotion, and closeness in relationships.
4. Broad personality dimensions are useful but too abstract alone.
5. Roleplaying systems consistently use traits, ideals, bonds, flaws, phrases, habits, vices, pet peeves, and fears.
6. AI roleplay card ecosystems emphasize description, personality, scenario, first message, alternate greetings, example messages, and lorebooks.
7. Visual identity matters for embodiment and consistency.
8. AI companion design must avoid agreement-drift and dependency traps; in Reverie this is implemented as character integrity, not generic moralizing anti-sycophancy.
9. Creator UX must be human-first. The user should answer emotional/story questions; the runtime should translate them into structured fields.

---

# 8. Final Recommendation

The next engineering target is:

```text
M6-P00 - Capability matrix reconciliation
```

Then close the identified M6-blocking runtime gaps and build the M6 practical creator.

The creator should expose only the fields in the M6 baseline after runtime gaps are closed. Everything else stays internal, preview-only, or deferred. This keeps Reverie honest: no decorative onboarding, no fake agency, no parallel visual canon, no memory soup, no magical promises that collapse the first time the user presses a button.

**End of CHARACTER_CREATOR_CAPABILITY_MATRIX v2.7**
