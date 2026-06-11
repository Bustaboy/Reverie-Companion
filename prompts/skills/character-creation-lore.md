# Character Creation and Lore Skill

**Use for**: character cards, personas, lorebooks, species/body facts, dialogue style, boundaries, import/export, visual identity, NSFW continuity, relationship anchors, and character schema design.

## North Star

A Reverie character is a persistent simulated person, not a prompt wrapper. Design characters with a stable core, mutable state, and room for earned growth.

## Non-Negotiables

- Separate stable identity from mutable state and scene state.
- Protect body/species facts, pronouns, core voice, values, boundaries, and lore from accidental drift.
- Make NSFW/futa/slime traits physically coherent and emotionally integrated, not bolted-on tags.
- Keep user-editable data local, exportable, versioned, and reversible.
- Avoid prompt-only monoliths; use structured fields that can feed memory, UI, media, and growth systems.

## Character Layers

| Layer | Contains | Update rule |
|---|---|---|
| Stable identity | name, pronouns, species/body facts, core voice, values, lore role | user edit or explicit migration only |
| Presentation | avatar, sprites, wardrobe defaults, visual tags | user edit, versioned |
| Voice | diction, rhythm, humor, taboo/NSFW tone, sample dialogue | curated edits and evals |
| Boundaries | hard limits, consent style, dislikes, safety expectations | user-controlled, high priority |
| Relationship anchors | first meeting, promises, nicknames, intimacy baseline | evidence-backed memory/growth |
| Mutable state | mood, goals, recent events, trust/tension, learned preferences | memory/reflection/growth flow |
| Scene state | location, pose, clothing, props, arousal/intimacy, continuity | session scoped unless promoted |
| Lore/world | places, factions, rules, species traits | versioned lorebook entries |

## Recommended Schema

```json
{
  "id": "character_...",
  "version": 1,
  "identity": {
    "name": "...",
    "pronouns": "...",
    "species": "...",
    "body_facts": ["..."],
    "core_values": ["..."],
    "stable_boundaries": ["..."]
  },
  "voice": {
    "summary": "...",
    "speech_patterns": ["..."],
    "sample_dialogue": ["..."]
  },
  "relationship": {
    "starting_dynamic": "...",
    "anchors": ["..."]
  },
  "appearance": {
    "base_description": "...",
    "visual_tags": ["..."],
    "asset_refs": []
  },
  "lore_refs": ["lore_..."],
  "memory_growth_settings": {
    "learning_enabled": true,
    "requires_review_for": ["identity", "training", "high_sensitivity"]
  }
}
```

## Card Writing Rules

- Lead with what makes the character emotionally distinct.
- Include enough physical continuity for chat, VN mode, and Futa-Vision prompts.
- Use positive directives (“speaks in warm teasing fragments”) over long negative lists.
- Provide 3-6 dialogue examples that demonstrate voice under different moods.
- Keep stable facts concise; put deep world details in lore entries.
- Mark boundaries and consent style clearly.
- Avoid stuffing all memory or user history into the card.

## Prompt Template: Character Card Draft

```text
Create a Reverie character card.
Inputs:
- Concept:
- Species/body facts:
- Emotional fantasy:
- Relationship starting point:
- NSFW/futa/slime traits if any:
- Boundaries:
- Visual style:

Return sections:
1. Stable identity
2. Core voice and sample dialogue
3. Relationship anchors
4. Appearance and visual continuity
5. Lore hooks
6. Boundaries and consent style
7. Growth settings
Keep it structured, concise, and local-first.
```

## Lorebook Rules

- Store lore as scoped entries with triggers/tags and priority.
- Distinguish canon from rumors, memories, and mutable discoveries.
- Keep entries short enough for retrieval; use summaries for large lore.
- Version lore changes and show conflicts before applying edits.
- Retrieval should respect active character, scene, location, and relationship context.

## Import/Export Guidance

- Preserve original card data when importing from other formats.
- Map unstructured prompts into structured fields with an import preview.
- Flag ambiguous identity/body/boundary fields for user review.
- Include schema version, asset references, memory/growth settings, and lore links in exports.
- Never silently merge imported data into existing memories or journals.

## Continuity Tests

- Character keeps voice across casual, emotional, and NSFW scenes.
- Body/species facts remain consistent in chat, VN, and media metadata.
- User edit to stable identity warns about memory/journal conflicts.
- Lore retrieval adds relevant context without flooding prompts.
- Character can grow in relationship state without changing core identity.
