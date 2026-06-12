<script lang="ts">
  export interface GrowthTimelineEvent {
    id: string;
    date: string;
    title: string;
    detail: string;
    theme: string;
    intensity: number;
  }

  interface Props {
    events: GrowthTimelineEvent[];
  }

  let { events }: Props = $props();

  const formatDate = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Recently';
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date);
  };
</script>

<section class="timeline-panel" aria-labelledby="growth-timeline-heading">
  <div class="section-heading">
    <p class="eyebrow">Recent growth events</p>
    <h2 id="growth-timeline-heading">What changed between you</h2>
  </div>

  {#if events.length === 0}
    <div class="empty-timeline">
      <span>♡</span>
      <h3>No growth events yet</h3>
      <p>Meaningful reflections will appear here as tone, trust, interests, and emotional bonds evolve.</p>
    </div>
  {:else}
    <div class="timeline-list">
      {#each events as event (event.id)}
        <article class="timeline-event" style={`--event-strength: ${Math.min(Math.max(event.intensity, 0.18), 1)}`}>
          <div class="timeline-dot" aria-hidden="true"></div>
          <div>
            <div class="event-topline">
              <span>{formatDate(event.date)}</span>
              <strong>{event.theme}</strong>
            </div>
            <h3>{event.title}</h3>
            <p>{event.detail}</p>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>

<style>
  .timeline-panel {
    min-height: 0;
    padding: 1.2rem;
    border: 1px solid var(--line);
    border-radius: 1.35rem;
    background: rgba(18, 14, 22, 0.58);
  }

  .section-heading h2,
  .empty-timeline h3,
  .timeline-event h3 {
    margin: 0;
  }

  .section-heading h2 {
    margin-top: 0.2rem;
    font-size: 1.25rem;
  }

  .timeline-list {
    display: grid;
    gap: 0.8rem;
    margin-top: 1rem;
  }

  .timeline-event {
    position: relative;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.85rem;
    padding: 0.95rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 1.05rem;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.068), rgba(255, 255, 255, 0.03));
  }

  .timeline-dot {
    width: 0.78rem;
    height: 0.78rem;
    margin-top: 0.25rem;
    border-radius: 999px;
    background: #ffb0a6;
    box-shadow: 0 0 calc(18px * var(--event-strength)) rgba(255, 176, 166, 0.58);
  }

  .event-topline {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 0.65rem;
    color: var(--dim);
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .event-topline strong {
    color: #f9c4bd;
  }

  .timeline-event h3 {
    margin-top: 0.25rem;
    color: var(--text);
    font-size: 1rem;
  }

  .timeline-event p,
  .empty-timeline p {
    margin: 0.35rem 0 0;
    color: var(--muted);
    line-height: 1.48;
  }

  .empty-timeline {
    margin-top: 1rem;
    padding: 1.4rem;
    text-align: center;
    border: 1px dashed rgba(255, 255, 255, 0.12);
    border-radius: 1.15rem;
    color: var(--muted);
  }

  .empty-timeline span {
    display: inline-grid;
    place-items: center;
    width: 2.5rem;
    height: 2.5rem;
    margin-bottom: 0.65rem;
    border-radius: 999px;
    background: rgba(240, 154, 159, 0.13);
    color: #ffd8d3;
  }
</style>
