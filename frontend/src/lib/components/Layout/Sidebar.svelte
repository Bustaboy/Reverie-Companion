<script lang="ts">
  const futureSections = [
    { label: 'Characters', detail: 'Companion roster' },
    { label: 'Memories', detail: 'Long-term context' },
    { label: 'Visual Novel', detail: 'Scene mode' },
    { label: 'Settings', detail: 'Local app controls' }
  ];
</script>

<aside class="sidebar" aria-label="Reverie navigation">
  <div class="brand">
    <div class="brand-mark" aria-hidden="true">R</div>
    <div>
      <p class="eyebrow">Offline companion</p>
      <h1>Reverie</h1>
    </div>
  </div>

  <section class="panel hero-card" aria-label="Current companion">
    <div class="avatar" aria-hidden="true">✦</div>
    <div>
      <p class="panel-label">Active muse</p>
      <h2>Seraphina</h2>
      <p>Warm, attentive, and waiting for your next message.</p>
    </div>
  </section>

  <nav class="nav-list" aria-label="Future Reverie features">
    {#each futureSections as section}
      <button type="button" aria-disabled="true">
        <span>{section.label}</span>
        <small>{section.detail}</small>
      </button>
    {/each}
  </nav>

  <div class="privacy-note">
    <span aria-hidden="true">●</span>
    <p>Local-first foundation. Backend integration will be added later.</p>
  </div>
</aside>
