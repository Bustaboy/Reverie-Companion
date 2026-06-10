<script lang="ts">
  import Sidebar from './Sidebar.svelte';
</script>

<div class="app-shell">
  <Sidebar />
  <main class="content-shell">
    <slot />
  </main>
</div>

<style>
  .app-shell {
    display: flex;
    min-height: 100vh;
    overflow: hidden;
  }

  .content-shell {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 100vh;
  }

  @media (max-width: 860px) {
    .app-shell {
      flex-direction: column;
      overflow: auto;
    }

    .content-shell {
      min-height: 0;
    }
  }
</style>
