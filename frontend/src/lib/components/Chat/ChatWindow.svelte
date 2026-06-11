<script lang="ts">
  import MessageInput from './MessageInput.svelte';
  import MessageList from './MessageList.svelte';
  import { createChatMessage, createInitialMessages, createPrototypeAssistantReply } from '$lib/chat/messages';
  import type { ChatMessage } from '$lib/types/chat';

  let messages = $state<ChatMessage[]>(createInitialMessages());

  const handleSend = (content: string) => {
    messages = [...messages, createChatMessage('user', content)];

    window.setTimeout(() => {
      messages = [...messages, createPrototypeAssistantReply()];
    }, 300);
  };
</script>

<section class="chat-window" aria-label="Reverie chat">
  <header class="chat-header">
    <div>
      <p class="eyebrow">Private local session</p>
      <h1>Reverie</h1>
      <p class="subtitle">A warm, offline companion interface built for long conversations.</p>
    </div>

    <div class="status-pill" aria-label="Prototype status">
      <span></span>
      Local UI prototype
    </div>
  </header>

  <MessageList {messages} />
  <MessageInput onSend={handleSend} />
</section>
