<script lang="ts">
  import ChatWindow from '$lib/components/Chat/ChatWindow.svelte';
  import AppShell from '$lib/components/Layout/AppShell.svelte';
</script>

<svelte:head>
  <title>Reverie — Local Companion</title>
  <meta
    name="description"
    content="A local-first Reverie desktop companion frontend built with Tauri 2 and SvelteKit."
  />
</svelte:head>

<AppShell>
  <ChatWindow />
</AppShell>
