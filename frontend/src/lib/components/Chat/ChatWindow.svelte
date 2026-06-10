<script lang="ts">
  import type { ChatMessage } from '$lib/types/chat';
  import MessageInput from './MessageInput.svelte';
  import MessageList from './MessageList.svelte';

  const initialMessages: ChatMessage[] = [
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Welcome back. I am here with you — unrushed, offline, and private.\n\nTell me what kind of mood you want to explore tonight, or ask me to remember something for later once memory support is connected.',
      createdAt: new Date()
    }
  ];

  let messages = $state<ChatMessage[]>(initialMessages);

  function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
    return {
      id: crypto.randomUUID(),
      role,
      content,
      createdAt: new Date()
    };
  }

  function handleSend(content: string) {
    messages = [...messages, createMessage('user', content)];

    window.setTimeout(() => {
      messages = [
        ...messages,
        createMessage(
          'assistant',
          `I hear you. For now I am a local UI prototype, so I can only echo the shape of a response.\n\n**You said:** ${content}`
        )
      ];
    }, 300);
  }
</script>

<section class="chat-window" aria-label="Reverie chat">
  <header class="chat-header">
    <div>
      <p class="eyebrow">Private session</p>
      <h2>Seraphina</h2>
    </div>
    <div class="status-pill" aria-label="Local prototype status">
      <span aria-hidden="true"></span>
      Local state only
    </div>
  </header>

  <MessageList {messages} />
  <MessageInput onSend={handleSend} />
</section>
