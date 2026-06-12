<script lang="ts">
  import { tick } from 'svelte';
  import MessageBubble from './MessageBubble.svelte';
  import type { ChatGenerationState } from '$lib/stores/chatStore';
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    messages: ChatMessage[];
    generationState: ChatGenerationState;
  }

  const STICKY_SCROLL_THRESHOLD_PX = 140;

  let { messages, generationState }: Props = $props();
  let listElement: HTMLElement;
  let shouldStickToBottom = true;
  let pendingScrollFrame: number | null = null;

  const scrollSignature = $derived(
    messages.map((message) => `${message.id}:${message.content.length}:${message.status ?? 'complete'}`).join('|')
  );

  const updateStickyScrollPreference = () => {
    if (!listElement) return;

    const distanceFromBottom = listElement.scrollHeight - listElement.scrollTop - listElement.clientHeight;
    shouldStickToBottom = distanceFromBottom < STICKY_SCROLL_THRESHOLD_PX;
  };

  const scrollToConversationEnd = async (behavior: ScrollBehavior = 'smooth') => {
    await tick();

    if (!listElement || !shouldStickToBottom) return;

    if (pendingScrollFrame) {
      cancelAnimationFrame(pendingScrollFrame);
    }

    // Streaming can produce many small DOM updates. Coalescing scroll work into
    // one animation frame keeps token rendering smooth and avoids scroll jitter.
    pendingScrollFrame = requestAnimationFrame(() => {
      listElement?.scrollTo({ top: listElement.scrollHeight, behavior });
      pendingScrollFrame = null;
    });
  };

  $effect(() => {
    scrollSignature;

    void scrollToConversationEnd(generationState === 'streaming' ? 'auto' : 'smooth');

    return () => {
      if (pendingScrollFrame) {
        cancelAnimationFrame(pendingScrollFrame);
        pendingScrollFrame = null;
      }
    };
  });
</script>

<section bind:this={listElement} class="message-list" aria-label="Conversation messages" role="log" aria-live="polite" aria-relevant="additions text" onscroll={updateStickyScrollPreference}>
  <div class="message-list-inner">
    {#if messages.length === 0 && generationState === 'idle'}
      <div class="conversation-empty" aria-live="polite">
        <span aria-hidden="true">✦</span>
        <h2>Begin a private reverie.</h2>
        <p>Share a mood, a scene, or a quiet thought. Reverie will keep the interface calm while memory, voice, and imagery stay under your control.</p>
      </div>
    {/if}

    {#each messages as message (message.id)}
      <MessageBubble {message} />
    {/each}

    {#if generationState === 'thinking'}
      <div class="thinking-state" aria-live="polite" aria-label="Reverie is thinking">
        <span class="thinking-orb" aria-hidden="true"></span>
        <span>Reverie is gathering her thoughts</span>
        <span class="thinking-dots" aria-hidden="true"><i></i><i></i><i></i></span>
      </div>
    {/if}
  </div>
</section>
