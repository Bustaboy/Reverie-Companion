<script lang="ts">
  const navItems = [
    { label: 'Chat', detail: 'Current conversation', active: true },
    { label: 'Characters', detail: 'Coming soon', active: false },
    { label: 'Memories', detail: 'Coming soon', active: false },
    { label: 'Settings', detail: 'Coming soon', active: false }
  ];
</script>

<aside class="sidebar" aria-label="Primary navigation">
  <div class="brand-block">
    <div class="brand-mark">R</div>
    <div>
      <p class="eyebrow">Offline companion</p>
      <h1>Reverie</h1>
    </div>
  </div>

  <div class="companion-card">
    <div class="portrait" aria-hidden="true">✦</div>
    <div>
      <p class="card-label">Active companion</p>
      <h2>Seraphina</h2>
      <p class="card-copy">Warm, attentive, and ready to grow with you.</p>
    </div>
  </div>

  <nav class="nav-list">
    {#each navItems as item}
      <a class:active={item.active} href="/" aria-current={item.active ? 'page' : undefined}>
        <span>{item.label}</span>
        <small>{item.detail}</small>
      </a>
    {/each}
  </nav>

  <div class="sidebar-footer">
    <p>Local-first foundation</p>
    <span>No backend connection yet</span>
  </div>
</aside>

<style>
  .sidebar {
    display: flex;
    flex-direction: column;
    gap: 1.4rem;
    min-width: 18rem;
    width: 18rem;
    min-height: 100vh;
    padding: 1.35rem;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.01)),
      rgba(14, 11, 18, 0.82);
    backdrop-filter: blur(24px);
  }

  .brand-block {
    display: flex;
    align-items: center;
    gap: 0.85rem;
  }

  .brand-mark,
  .portrait {
    display: grid;
    place-items: center;
    flex: none;
    border: 1px solid rgba(255, 196, 171, 0.26);
    background: linear-gradient(145deg, rgba(244, 149, 132, 0.28), rgba(133, 91, 255, 0.18));
    box-shadow: 0 16px 45px rgba(244, 149, 132, 0.16);
  }

  .brand-mark {
    width: 2.7rem;
    height: 2.7rem;
    border-radius: 1rem;
    color: #ffe8de;
    font-weight: 800;
  }

  .eyebrow,
  .card-label {
    margin: 0 0 0.18rem;
    color: #caa89d;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
  }

  h1,
  h2,
  p {
    margin: 0;
  }

  h1 {
    color: #fff7f1;
    font-size: 1.35rem;
    letter-spacing: -0.04em;
  }

  .companion-card {
    display: grid;
    gap: 1rem;
    padding: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 1.35rem;
    background: rgba(255, 255, 255, 0.045);
  }

  .portrait {
    width: 4.35rem;
    height: 4.35rem;
    border-radius: 1.4rem;
    color: #ffd9cc;
    font-size: 1.35rem;
  }

  h2 {
    color: #fff5ee;
    font-size: 1.08rem;
  }

  .card-copy {
    margin-top: 0.35rem;
    color: #a99aa8;
    font-size: 0.9rem;
    line-height: 1.45;
  }

  .nav-list {
    display: grid;
    gap: 0.55rem;
  }

  .nav-list a {
    display: grid;
    gap: 0.2rem;
    padding: 0.85rem 0.95rem;
    border: 1px solid transparent;
    border-radius: 1rem;
    color: #d9cdd9;
    text-decoration: none;
    transition:
      background 160ms ease,
      border-color 160ms ease,
      color 160ms ease;
  }

  .nav-list a:hover,
  .nav-list a.active {
    border-color: rgba(255, 196, 171, 0.2);
    background: rgba(255, 196, 171, 0.08);
    color: #fff7f1;
  }

  .nav-list span {
    font-weight: 700;
  }

  .nav-list small {
    color: #918593;
  }

  .sidebar-footer {
    margin-top: auto;
    padding: 0.9rem;
    border-radius: 1rem;
    background: rgba(0, 0, 0, 0.18);
    color: #beacae;
    font-size: 0.84rem;
  }

  .sidebar-footer span {
    display: block;
    margin-top: 0.25rem;
    color: #827783;
  }

  @media (max-width: 860px) {
    .sidebar {
      width: 100%;
      min-width: 0;
      min-height: auto;
      border-right: 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    .companion-card,
    .sidebar-footer {
      display: none;
    }

    .nav-list {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .nav-list a {
      padding: 0.7rem;
    }

    .nav-list small {
      display: none;
    }
  }
</style>
