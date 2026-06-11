# Self-Learning Growth Skill

**Use for**: character growth loops, evolving relationship/personality state, learning artifacts, user-approved datasets, adapter/LoRA workflows, growth dashboards, rollback, audits, and long-term behavioral change.

## North Star

Reverie characters should grow like people: slowly, from evidence, with memory and reflection, while staying recognizable. Growth deepens identity; it does not silently replace it.

## Non-Negotiables

- Growth must be evidence-backed, inspectable, reversible, and local-first.
- Stable identity, body facts, core voice, lore, and boundaries are protected unless the user intentionally edits them.
- Separate memory, journal insight, relationship state, prompt/config changes, datasets, and adapters.
- Training uses only approved, local, non-deleted, eligible data.
- No hidden cloud learning, telemetry, or surprise fine-tuning.
- Every durable change needs provenance, confidence, review state, and rollback path.

## Growth Layers

| Layer | Purpose | Update speed |
|---|---|---|
| Memory | Facts/events/preferences/boundaries | fast for clear facts, slower for interpretations |
| Journal | Character meaning-making | after salient events or idle windows |
| Relationship state | trust, intimacy, tension, commitments | gradual, evidence weighted |
| Behavioral nudges | prompt-time style/context hints | reversible and scoped |
| Datasets | curated examples for future training | opt-in, reviewed |
| Adapters/LoRA | durable learned behavior | rare, explicit, versioned |

## Evidence Ladder

1. **Single weak signal** → keep as low-confidence candidate or journal note.
2. **Clear explicit statement** → memory candidate, maybe auto-save depending sensitivity.
3. **Repeated pattern** → higher confidence memory or relationship-state update.
4. **Emotional milestone/correction/boundary** → journal + reviewable state change.
5. **User-approved learning set** → dataset item.
6. **Validated dataset + user consent** → adapter/training job.

## Growth Event Schema

```json
{
  "id": "growth_...",
  "character_id": "...",
  "type": "relationship_state|behavioral_nudge|dataset_item|adapter_version",
  "summary": "What changed in human language",
  "evidence_ids": ["message_...", "memory_...", "journal_..."],
  "before": {},
  "after": {},
  "confidence": 0.0,
  "review_state": "proposed|approved|applied|rejected|rolled_back",
  "sensitivity": "low|medium|high",
  "created_at": "2026-06-11T00:00:00Z",
  "rollback_plan": "How to undo derived changes"
}
```

## Growth Flow

1. Detect candidate signal from memory/reflection.
2. Attach evidence and classify protected vs mutable fields.
3. Propose the smallest useful change.
4. Require review for identity, relationship, high-sensitivity, training, or adapter changes.
5. Apply as scoped state/prompt metadata before considering model training.
6. Monitor for contradictions, user corrections, or drift.
7. Roll back cleanly when rejected/deleted.

## Training and Adapter Rules

- Default to no training; prompt-time memory and state should solve most needs.
- Curate examples from approved memories/journals/conversations only.
- Store source links, consent state, license/privacy flags, and deletion dependencies.
- Use LoRA/QLoRA with 8GB-aware scheduling; never train during active chat/media.
- Version adapters with base model, dataset hash, hyperparameters, eval notes, and rollback path.
- Provide preview/evaluation before making an adapter default.

## Prompt Templates

### Growth Proposal

```text
Given this evidence packet, propose at most one growth change.
Rules:
- Preserve stable identity and lore.
- Prefer reversible state or prompt-time nudges over training.
- Mark uncertainty and review needs.
- Do not use deleted/private/unapproved data.

Return JSON:
{"summary":"...","layer":"memory|journal|relationship_state|behavioral_nudge|dataset|adapter",
 "evidence_ids":["..."],"confidence":0.0,
 "requires_user_review":true,"protected_field_risk":"none|low|high",
 "rollback_plan":"..."}
```

### User-Facing Growth Copy

```text
{character_name} may be learning that {insight}.
Evidence: {short_sources}.
[Approve] [Edit] [Keep as journal only] [Reject]
```

## Dashboard Requirements

- Show what changed, why, when, and how to undo it.
- Separate emotional growth from technical training details.
- Highlight pending review and privacy-sensitive items.
- Provide pause learning / do not learn from this / delete everywhere controls.
- Advanced view may show datasets, adapter versions, evals, and job logs.

## Drift Prevention

- Compare proposed changes against stable identity and lore.
- Use confidence thresholds and repeated evidence for personality/relationship changes.
- Prefer decay for uncertain states instead of permanent mutation.
- Treat contradictions as review events.
- Run regression prompts/evals for voice and boundary consistency before adapter promotion.

## Test Cases

- Weak single signal does not mutate character identity.
- Repeated preference becomes reviewable memory/growth.
- Deleted source removes dependent dataset items and adapter eligibility.
- User rejects growth proposal and behavior reverts.
- Training job is queued, cancelable, and blocked while chat GPU work is active.
- Adapter version can be disabled or rolled back.
