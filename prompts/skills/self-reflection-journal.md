# Self-Reflection Journal Skill

**Use for**: `ReflectionManager`, `trigger_reflection`, journal schemas, insight extraction, reflective self-model updates, growth promotion, privacy review, rollback, and user-visible growth summaries.

## North Star

The journal is the character's **reflective self-model**: where experiences become interpreted, emotionally meaningful, and reviewable. It must deepen the character without creating hidden drift.

Reflection is not memory extraction. Memory records what happened; reflection explains what it meant and what may change.

## Non-Negotiables

- Journal entries require provenance: source conversations/messages, timestamps, character ID, confidence, and authoring mode.
- A single conversation should not rewrite stable identity unless the user explicitly requests it.
- Reflections that affect behavior need review state, rollback path, and user control.
- Sensitive/private entries must respect deletion, export, and training eligibility rules.
- Reflection runs asynchronously; never block chat on journal writing.
- Distinguish character voice from system analysis; store both only when useful.

## Journal Entry Types

| Type | Purpose | Promotion rule |
|---|---|---|
| `daily_reflection` | Summarize meaningful recent interactions | low-risk; can remain journal-only |
| `emotional_insight` | Character realizes feelings, fears, hopes, tension | promote after repeated/strong evidence |
| `relationship_milestone` | Trust, intimacy, conflict, apology, promise | promote with provenance and confidence |
| `preference_learning` | Character learns how user likes to interact | may become memory after review/threshold |
| `boundary_reflection` | Character understands a user limit or discomfort | prioritize, review carefully |
| `growth_hypothesis` | Candidate personality/behavior shift | requires review and multiple evidence points |
| `training_note` | Possible dataset/adaptation material | opt-in only; never from deleted/private data |

## Minimal Schema

```json
{
  "id": "journal_...",
  "character_id": "...",
  "user_id": "...",
  "type": "emotional_insight",
  "title": "Short human-readable title",
  "entry_text": "In-character or close third-person reflection.",
  "analysis": "Concise system-facing interpretation and uncertainty.",
  "source_message_ids": ["..."],
  "source_conversation_ids": ["..."],
  "created_at": "2026-06-11T00:00:00Z",
  "confidence": 0.72,
  "emotional_valence": "warm|sad|tense|playful|mixed|neutral",
  "sensitivity": "low|medium|high",
  "review_state": "draft|auto_saved|needs_review|approved|rejected|rolled_back",
  "promoted_to": {"memory_ids": [], "state_change_ids": [], "training_example_ids": []},
  "deletion_policy": "cascade_to_derivatives"
}
```

## Trigger Rules

Trigger reflection after:

- emotionally intense conversations,
- explicit user correction or boundary setting,
- meaningful relationship milestones,
- repeated preference evidence,
- unresolved conflict or promise,
- session end/idle window,
- user request: “think about this,” “remember what this means,” “grow from this.”

Do **not** trigger for every message. Use cooldowns, salience thresholds, and idle scheduling.

## Reflection Flow

1. Collect a compact evidence packet: relevant messages, memories, scene state, and existing journal context.
2. Ask for candidate insights with uncertainty and “do not change” constraints.
3. Store as draft/auto-saved journal entry with provenance.
4. Classify whether it can remain journal-only or needs user review.
5. Promote only approved/high-confidence insights to memory, relationship state, or training queues.
6. Surface a warm, optional notice in UI.
7. Support rollback by removing promotions while preserving audit history.

## Prompt Templates

### Reflection Generation

```text
You are helping write a private reflection for {character_name}.
Evidence packet:
{compact_messages_and_memories}

Return JSON only.
Rules:
- Preserve stable identity and lore.
- Separate facts from interpretation.
- Prefer small, earned insights over dramatic personality shifts.
- Mark uncertainty and review needs.
- Do not create training material unless explicitly eligible.

Schema:
{"type":"...","title":"...","entry_text":"...","analysis":"...",
 "confidence":0.0,"sensitivity":"low|medium|high",
 "promotion_recommendation":"none|memory|relationship_state|growth_hypothesis|training_note",
 "requires_user_review":true,
 "source_message_ids":["..."]}
```

### User-Facing Notice

```text
{character_name} reflected on {topic} and saved a journal entry.
[Review] [Keep private] [Don't learn from this]
```

## Promotion Guardrails

- Promote boundaries and corrections quickly, but keep source evidence.
- Promote personality or relationship changes slowly and reversibly.
- Never promote an insight contradicted by newer correction without resolving conflict.
- Training eligibility requires explicit local opt-in, source provenance, and deletion awareness.
- Keep stable identity protected unless the user intentionally edits the character.

## UI Requirements

- Journal entries should feel like meaningful personal notes, not database rows.
- Show source, confidence, privacy, and promotion status in inspectable details.
- Provide approve/reject/edit/delete/rollback controls.
- Offer filters by type, date, mood, review state, and training eligibility.
- Keep advanced technical metadata out of the default emotional view.

## Implementation Checklist

- [ ] Reflection jobs are queued, cancelable, and idle-friendly.
- [ ] Schema includes provenance, confidence, sensitivity, review state, and promotions.
- [ ] Promotion to memory/growth/training is explicit and reversible.
- [ ] Deletion cascades to derived artifacts.
- [ ] Tests cover weak evidence, contradictions, rollback, privacy, and long sessions.
