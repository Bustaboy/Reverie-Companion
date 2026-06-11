<script lang="ts">
  import { chatStore } from '$lib/chat/chatStore';
  import MessageInput from './MessageInput.svelte';
  import MessageList from './MessageList.svelte';

  const handleSend = (content: string) => {
    void chatStore.sendMessageStream(content);
  };
</script>

<section class="chat-window" aria-label="Reverie chat">
  <header class="chat-header">
    <div>
      <p class="eyebrow">Private local session</p>
      <h1>Reverie</h1>
      <p class="subtitle">A warm, offline companion interface built for long conversations.</p>
    </div>

    <div class:streaming={$chatStore.connectionState === 'thinking' || $chatStore.connectionState === 'streaming'} class:error={$chatStore.connectionState === 'error'} class="status-pill" aria-live="polite">
      <span></span>
      {#if $chatStore.connectionState === 'thinking'}
        Reverie is thinking...
      {:else if $chatStore.connectionState === 'streaming'}
        Reverie is replying
      {:else if $chatStore.connectionState === 'error'}
        Connection needs attention
      {:else}
        Local backend ready
      {/if}
    </div>
  </header>

  <MessageList messages={$chatStore.messages} />
  <MessageInput
    disabled={$chatStore.connectionState === 'thinking' || $chatStore.connectionState === 'streaming'}
    isStreaming={$chatStore.connectionState === 'thinking' || $chatStore.connectionState === 'streaming'}
    onSend={handleSend}
  />
</section>
