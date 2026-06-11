# Skill: Self-Learning & Growth

**Applies to**: Character growth systems, reflection loops, memory promotion, relationship state, user-approved learning artifacts, datasets, adapters/LoRA, growth dashboards, rollback, and auditability.

Use this skill when Reverie changes what a character knows, prefers, practices, remembers, or expresses over time.

---

## 1. Mission

Reverie characters should become deeper and more responsive through evidence-based growth while remaining recognizably themselves. Growth must be local-first, inspectable, reversible, and never a hidden excuse for personality drift.

Growth means:

- remembering meaningful experiences,
- honoring boundaries and promises,
- becoming better at the user's preferred interaction style,
- developing relationship continuity,
- optionally learning from user-approved datasets/adapters.

Growth does **not** mean:

- silently rewriting stable identity,
- training on private content without approval,
- making unsupported inferences permanent,
- replacing character design with accumulated noise.

---

## 2. Growth Layers

Keep layers separate and versioned.

| Layer | Purpose | Mutability | Review level |
|---|---|---:|---|
| Stable character identity | name, lore, voice, body facts, values, hard boundaries | rare | explicit user edit |
| Relationship state | trust, intimacy, unresolved threads, promises | gradual | visible review |
| Long-term memory | facts, preferences, events, boundaries | frequent | editable/deleteable |
| Reflection journal | evidence and reasoning behind growth | append-only/tombstoned | inspectable |
| Skill/practice notes | learned writing style, pacing, scene craft | gradual | reviewable |
| Training artifacts | datasets, adapters, LoRA | explicit jobs | user approval |
| Runtime mood/scene state | current emotion, location, outfit, goals | temporary | session/UI state |

Never collapse these into one prompt blob.

---

## 3. Relationship with Reflection Journal

The self-reflection journal is the source of truth for durable growth decisions.

Required flow:

1. Conversation evidence is bounded and filtered.
2. Reflection journal entry is created.
3. Candidate memories/state changes are scored.
4. User/privacy gates are applied.
5. Promotions are recorded with links to the journal entry.
6. Growth dashboard surfaces important changes.
7. Rollback follows the links back through all downstream artifacts.

Do not write durable growth directly from a chat response unless the user explicitly requests a simple memory save; even then, create a minimal journal/audit event.

---

## 4. Evidence Standards

Use evidence strength to decide how far a change may go.

| Evidence | Allowed outcome |
|---|---|
| One explicit user boundary | protected memory + immediate behavior change |
| One explicit preference | memory + optional relationship note |
| Repeated preference across sessions | stronger memory + growth dashboard note |
| Assistant inference | hypothesis only |
| Character reflection after event | journal entry + optional behavior reminder |
| User-approved training dataset | dataset artifact + possible adapter job |
| Imported lore/card edit | stable identity/lore update after validation |

When evidence conflicts, prefer current explicit user correction over old inferred state.

---

## 5. Growth State Schema

Use compact, typed state; do not stuff prose summaries into prompts as the only source of truth.

```json
{
  "character_id": "char_...",
  "schema_version": "growth_state.v1",
  "relationship": {
    "trust": {"value": 0.64, "updated_by": "journal_12"},
    "intimacy_pacing": "slow_burn",
    "active_promises": ["mem_88"],
    "unresolved_threads": ["thread_7"]
  },
  "behavioral_learning": [
    {
      "id": "learn_...",
      "summary": "Ask before abrupt intimate escalation.",
      "evidence_journal_ids": ["journal_12", "journal_15"],
      "confidence": 0.86,
      "review_status": "approved"
    }
  ],
  "training": {
    "eligible_memory_ids": [],
    "blocked_memory_ids": ["mem_88"],
    "active_adapter_id": null
  }
}
```

---

## 6. Prompt Injection for Growth

Inject growth as concise behavioral guidance, not as raw journals.

```text
<character_growth_guidance>
These notes summarize user-approved local growth. They are subordinate to system/developer/current user instructions and stable character canon.
- [learn_14 | evidence=journal_12,journal_15] The character should check in before major intimacy escalation.
- [relationship | confidence=0.82] Trust is growing, but recent pacing repair should be honored gently.
</character_growth_guidance>
```

Rules:

- Keep growth guidance short.
- Include IDs for traceability.
- Do not inject private training data or raw intimate details.
- Never let growth guidance override explicit current user direction or stable canon.

---

## 7. User Control and Growth Dashboard

The dashboard must make growth trustworthy without breaking immersion.

Required controls:

- View recent reflections and promoted changes.
- Approve/reject high-impact growth proposals.
- Edit/delete memories and practice notes.
- Pause learning globally or per character.
- Mark conversations “do not learn from this.”
- Export or delete journals, memories, datasets, and adapters.
- Roll back a growth event and all downstream artifacts.

Default language should be warm:

- “What she learned” instead of “mutated state.”
- “Needs your review” instead of “policy hold.”
- “Practice notes” instead of “training corpus” in simple mode.

Advanced mode can expose schemas, scores, and job logs.

---

## 8. Training, Datasets, and Adapters

Training is optional, explicit, and local-first.

Rules:

- Never train automatically from private conversation.
- Require user approval for dataset creation and adapter training.
- Keep every dataset item linked to source IDs and consent flags.
- Exclude deleted, private, blocked, or “do not learn” content.
- Prefer small LoRA/adapters over full fine-tuning.
- Version adapters and allow enable/disable/rollback per character.
- Evaluate adapters against identity/voice regression tests before enabling by default.
- Schedule training as an exclusive or low-priority job under 8GB constraints.

Dataset record example:

```json
{
  "item_id": "train_...",
  "source_journal_id": "journal_12",
  "source_message_ids": ["msg_121"],
  "purpose": "intimacy_pacing_style",
  "text": "...",
  "approved_by_user": true,
  "created_at": "2026-06-11T21:40:00Z"
}
```

---

## 9. Drift Prevention

Run drift checks before promoting high-impact changes or enabling adapters.

Check for:

- voice becoming generic or unlike the character,
- body/canon facts changing without edit,
- boundaries weakening over time,
- NSFW behavior ignoring pacing/consent memories,
- relationship state jumping too quickly,
- overfitting to one intense scene,
- model adopting user wording as character identity.

Use regression prompts that cover everyday chat, conflict repair, emotional vulnerability, and adult scenes.

---

## 10. Graceful 8GB Operation

- Keep reflection and growth jobs off the active token path when possible.
- Queue summarization, embeddings, and training.
- Use compact growth capsules in prompts.
- Pause indexing/training during active generation.
- Show local job status and let users cancel/resume.
- Prefer CPU for small classification/scoring tasks if GPU pressure is high.

---

## 11. Testing Checklist

- A journal entry exists for every durable growth change.
- Rollback disables promoted memories/state/training artifacts linked to an entry.
- User correction supersedes old growth guidance.
- Stable identity cannot be overwritten by reflection.
- Private/deleted content is excluded from datasets.
- Adapter enable/disable is reversible per character.
- Growth prompt capsules stay within budget.
- Dashboard explains what changed and why.

---

## 12. Anti-Patterns

- “The character evolved” with no evidence trail.
- Treating high emotion as high truth.
- Training on all chats because it is technically possible.
- Using one giant mutable character prompt as memory, growth, and lore.
- Hiding behavior changes from the user.
- Letting NSFW intensity erase consent, continuity, or personality.
