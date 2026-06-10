<script lang="ts">
  import ChatWindow from '$lib/components/Chat/ChatWindow.svelte';
  import Sidebar from './Sidebar.svelte';
</script>

<div class="app-shell">
  <Sidebar />
  <main class="main-panel">
    <ChatWindow />
  </main>
</div>
