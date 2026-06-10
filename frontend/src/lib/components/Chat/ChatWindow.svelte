<script lang="ts">
  import MessageInput from './MessageInput.svelte';
  import MessageList from './MessageList.svelte';
  import type { ChatMessage } from '$lib/types/chat';

  const initialMessages: ChatMessage[] = [
    {
      id: 'welcome-1',
      role: 'assistant',
      content:
        "Good evening. I'm here with you. Tell me what kind of scene, mood, or memory you want to explore first.\n\n*For now this is a local UI prototype — the backend will be connected later.*",
      createdAt: new Date()
    }
  ];

  let messages = $state<ChatMessage[]>(initialMessages);

  const createMessage = (role: ChatMessage['role'], content: string): ChatMessage => ({
    id: crypto.randomUUID(),
    role,
    content,
    createdAt: new Date()
  });

  const handleSend = (content: string) => {
    messages = [...messages, createMessage('user', content)];

    window.setTimeout(() => {
      messages = [
        ...messages,
        createMessage(
          'assistant',
          "I heard you. Backend connection comes later, but the chat flow is ready for a real local model response.\n\n**Next foundation pieces:** character state, memory retrieval, and settings."
        )
      ];
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
