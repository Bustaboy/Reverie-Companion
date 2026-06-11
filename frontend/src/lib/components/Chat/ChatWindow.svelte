<script lang="ts">
  import MessageInput from './MessageInput.svelte';
  import MessageList from './MessageList.svelte';
  import { chatStore } from '$lib/stores/chatStore';

  const handleSend = (content: string) => {
    void chatStore.sendMessage(content);
  };
</script>

<section class="chat-window" aria-label="Reverie chat">
  <header class="chat-header">
    <div>
      <p class="eyebrow">Private local session</p>
      <h1>Reverie</h1>
      <p class="subtitle">A warm, offline companion interface built for long conversations.</p>
    </div>

    <div class:streaming={$chatStore.generationState !== 'idle'} class="status-pill" aria-label="Companion status">
      <span></span>
      {$chatStore.generationState === 'idle' ? 'Local backend ready' : 'Reverie is responding'}
    </div>
  </header>

  <MessageList messages={$chatStore.messages} generationState={$chatStore.generationState} />
  <MessageInput onSend={handleSend} disabled={$chatStore.generationState !== 'idle'} />
</section>
