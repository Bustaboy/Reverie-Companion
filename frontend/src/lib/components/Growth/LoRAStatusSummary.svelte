<script lang="ts">
  import type { LoRATrainingJob, PersonalLoRACounts, PersonalLoRASettings } from '$lib/types/growth';

  interface Props {
    settings: PersonalLoRASettings | null;
    job: LoRATrainingJob | null;
    counts: PersonalLoRACounts;
  }

  let { settings, job, counts }: Props = $props();

  const labelFor = (value: string | undefined | null) =>
    (value ?? 'idle').replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

  const formatDate = (value: string | null | undefined) => {
    if (!value) return 'Not trained yet';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Not trained yet';
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
  };

  const progress = $derived(Math.min(Math.max(job?.progress ?? (job?.status === 'completed' ? 1 : 0), 0), 1));
  const status = $derived(job?.status ?? 'idle');
  const lastTrained = $derived(job?.completed_at ? formatDate(job.completed_at) : settings?.active_adapter_id ? 'Adapter enabled' : 'Not trained yet');
  const nextScheduled = $derived(
    settings?.training_opt_in
      ? counts.approved > 0
        ? 'Manual start when you choose'
        : 'After examples are approved'
      : 'Not scheduled — opt-in is off'
  );
</script>

<article class="lora-card" aria-labelledby="lora-status-heading">
  <div class="card-heading">
    <p class="eyebrow">LoRA training status</p>
    <h2 id="lora-status-heading">Practice stays optional</h2>
    <span>{labelFor(status)}</span>
  </div>

  <div class="training-progress" aria-label="Current LoRA training progress">
    <div><span style={`width: ${Math.max(7, Math.round(progress * 100))}%`}></span></div>
    <strong>{Math.round(progress * 100)}%</strong>
  </div>

  <dl class="lora-stats">
    <div>
      <dt>Last trained</dt>
      <dd>{lastTrained}</dd>
    </div>
    <div>
      <dt>Next scheduled</dt>
      <dd>{nextScheduled}</dd>
    </div>
    <div>
      <dt>Approved notes</dt>
      <dd>{counts.approved}</dd>
    </div>
    <div>
      <dt>Needs review</dt>
      <dd>{counts.pending_review}</dd>
    </div>
  </dl>

  <p class="lora-note">This dashboard only summarizes training readiness. Review and training controls remain in the dedicated Training page.</p>
</article>

<style>
  .lora-card {
    padding: 1.2rem;
    border: 1px solid var(--line);
    border-radius: 1.35rem;
    background:
      radial-gradient(circle at top right, rgba(240, 154, 159, 0.18), transparent 45%),
      rgba(255, 255, 255, 0.055);
  }

  .card-heading {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.25rem 0.75rem;
    align-items: start;
  }

  .card-heading .eyebrow {
    grid-column: 1 / -1;
  }

  .card-heading h2 {
    margin: 0;
    font-size: 1.25rem;
  }

  .card-heading span {
    padding: 0.4rem 0.65rem;
    border: 1px solid rgba(255, 176, 166, 0.25);
    border-radius: 999px;
    color: #ffd8d3;
    background: rgba(255, 176, 166, 0.09);
    font-size: 0.82rem;
    font-weight: 800;
  }

  .training-progress {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.75rem;
    margin: 1rem 0;
  }

  .training-progress div {
    height: 0.65rem;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.09);
  }

  .training-progress span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #ffb0a6, #d98bd2);
    box-shadow: 0 0 20px rgba(255, 176, 166, 0.36);
  }

  .lora-stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.7rem;
    margin: 0;
  }

  .lora-stats div {
    padding: 0.78rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 0.95rem;
    background: rgba(0, 0, 0, 0.12);
  }

  dt {
    color: var(--dim);
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  dd {
    margin: 0.28rem 0 0;
    color: var(--text);
    font-weight: 800;
  }

  .lora-note {
    margin: 0.9rem 0 0;
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.45;
  }
</style>
