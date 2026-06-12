<script lang="ts">
  interface Props {
    label: string;
    value: number;
    tone: string;
    description: string;
  }

  let { label, value, tone, description }: Props = $props();
  const bounded = $derived(Math.min(Math.max(value, 0), 1));
  const percent = $derived(Math.round(bounded * 100));
</script>

<article class="feeling-card" style={`--feeling-level: ${bounded}; --feeling-tone: ${tone};`}>
  <div class="feeling-topline">
    <span>{label}</span>
    <strong>{percent}%</strong>
  </div>
  <div class="feeling-meter" aria-label={`${label} level`} role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow={percent}>
    <span></span>
  </div>
  <p>{description}</p>
</article>

<style>
  .feeling-card {
    padding: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 1.15rem;
    background:
      radial-gradient(circle at 18% 0%, color-mix(in srgb, var(--feeling-tone) 22%, transparent), transparent 70%),
      rgba(255, 255, 255, 0.052);
  }

  .feeling-topline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .feeling-topline span {
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .feeling-topline strong {
    color: #fff3f3;
    font-size: 1.35rem;
  }

  .feeling-meter {
    height: 0.55rem;
    margin: 0.85rem 0 0.8rem;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.09);
  }

  .feeling-meter span {
    display: block;
    width: calc(var(--feeling-level) * 100%);
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, color-mix(in srgb, var(--feeling-tone) 62%, #ffffff), var(--feeling-tone));
    box-shadow: 0 0 22px color-mix(in srgb, var(--feeling-tone) 34%, transparent);
  }

  p {
    margin: 0;
    color: var(--muted);
    font-size: 0.93rem;
    line-height: 1.45;
  }
</style>
