<script lang="ts">
  const navItems = [
    { label: 'Chat', hint: 'Current session', active: true },
    { label: 'Characters', hint: 'Coming soon', active: false },
    { label: 'Memory', hint: 'Long-term recall', active: false },
    { label: 'Visual Novel', hint: 'Future mode', active: false },
    { label: 'Settings', hint: 'Privacy & models', active: false }
  ];
</script>

<aside class="sidebar" aria-label="Reverie workspace navigation">
  <div class="brand">
    <div class="brand-mark">R</div>
    <div>
      <strong>Reverie</strong>
      <span>Offline companion</span>
    </div>
  </div>

  <nav class="nav-list" aria-label="Primary navigation">
    {#each navItems as item}
      <button class:active={item.active} type="button" disabled={!item.active}>
        <span>{item.label}</span>
        <small>{item.hint}</small>
      </button>
    {/each}
  </nav>

  <div class="sidebar-card">
    <p>Foundation ready</p>
    <span>Character panels, memories, and settings can slot into this sidebar without changing the chat shell.</span>
  </div>
</aside>
