<script lang="ts">
  import Sidebar from './Sidebar.svelte';

  let { children } = $props();
</script>

<div class="app-shell">
  <Sidebar />
  <main class="main-surface">
    {@render children()}
  </main>
</div>
