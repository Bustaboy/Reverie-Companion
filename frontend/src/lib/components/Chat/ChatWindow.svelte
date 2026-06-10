<script lang="ts">
  import type { ChatMessage } from '$lib/types/chat';
  import MessageComposer from './MessageComposer.svelte';
  import MessageList from './MessageList.svelte';

  const starterMessages: ChatMessage[] = [
    {
      id: crypto.randomUUID(),
      role: 'assistant',
      content:
        "Welcome home. I'm **Seraphina**, your local Reverie companion. This first frontend shell is running entirely on local state, so we can shape the experience before connecting memory and model systems.",
      createdAt: new Date()
    },
    {
      id: crypto.randomUUID(),
      role: 'assistant',
      content:
        'Try sending a message. I will echo a gentle placeholder response for now, and the input will clear so the chat loop feels real.',
      createdAt: new Date()
    }
  ];

  let messages = starterMessages;

  function createMessage(role: ChatMessage['role'], content: string): ChatMessage {
    return {
      id: crypto.randomUUID(),
      role,
      content,
      createdAt: new Date()
    };
  }

  function handleSend(event: CustomEvent<string>) {
    const userMessage = createMessage('user', event.detail);
    const assistantMessage = createMessage(
      'assistant',
      'I hear you. For now, this is a simulated local reply so the interface can be refined before the backend arrives. I will keep this moment in the conversation history until you refresh.'
    );

    messages = [...messages, userMessage, assistantMessage];
  }
</script>

<section class="chat-window" aria-label="Chat interface">
  <header class="chat-header">
    <div>
      <p class="eyebrow">Current session</p>
      <h2>Private conversation</h2>
      <p class="subtitle">A calm, local-first foundation for companion chat, memory, and future VN mode.</p>
    </div>
    <div class="status-pill" aria-label="Local mode enabled">
      <span></span>
      Local only
    </div>
  </header>

  <MessageList {messages} />

  <footer class="composer-wrap">
    <MessageComposer on:send={handleSend} />
    <p class="composer-note">Backend integration is intentionally disabled in this milestone.</p>
  </footer>
</section>

<style>
  .chat-window {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
    min-height: 100vh;
  }

  .chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1.45rem 1.6rem 1.1rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(16, 13, 19, 0.58);
    backdrop-filter: blur(20px);
  }

  .eyebrow,
  h2,
  .subtitle {
    margin: 0;
  }

  .eyebrow {
    color: #caa89d;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.13em;
    text-transform: uppercase;
  }

  h2 {
    margin-top: 0.2rem;
    color: #fff7f1;
    font-size: clamp(1.45rem, 3vw, 2.1rem);
    letter-spacing: -0.05em;
  }

  .subtitle {
    margin-top: 0.35rem;
    color: #a89ba8;
    line-height: 1.45;
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    flex: none;
    padding: 0.5rem 0.72rem;
    border: 1px solid rgba(164, 255, 211, 0.18);
    border-radius: 999px;
    background: rgba(117, 255, 189, 0.08);
    color: #b8f8d4;
    font-size: 0.82rem;
    font-weight: 800;
  }

  .status-pill span {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 999px;
    background: #8dffc4;
    box-shadow: 0 0 20px rgba(141, 255, 196, 0.75);
  }

  .composer-wrap {
    padding: 0.8rem 1.6rem 1.2rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    background: linear-gradient(180deg, rgba(16, 13, 19, 0.58), rgba(16, 13, 19, 0.92));
  }

  .composer-note {
    margin: 0.55rem 0 0;
    color: #817682;
    font-size: 0.82rem;
    text-align: center;
  }

  @media (max-width: 680px) {
    .chat-header {
      align-items: flex-start;
      flex-direction: column;
      padding: 1rem;
    }

    .chat-window {
      min-height: calc(100vh - 9rem);
    }

    .composer-wrap {
      padding: 0.8rem 1rem 1rem;
    }
  }
</style>
