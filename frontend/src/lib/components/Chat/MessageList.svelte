<script lang="ts">
  import { tick } from 'svelte';
  import MessageBubble from './MessageBubble.svelte';
  import type { ChatGenerationState } from '$lib/stores/chatStore';
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    messages: ChatMessage[];
    generationState: ChatGenerationState;
  }

  const AUTO_SCROLL_THRESHOLD_PX = 140;

  let { messages, generationState }: Props = $props();
  let listElement: HTMLElement;
  let shouldStickToBottom = $state(true);

  const scrollSignature = $derived(
    messages.map((message) => `${message.id}:${message.content.length}:${message.status ?? 'complete'}`).join('|')
  );

  const isNearBottom = () => {
    if (!listElement) return true;

    return listElement.scrollHeight - listElement.scrollTop - listElement.clientHeight < AUTO_SCROLL_THRESHOLD_PX;
  };

  const updateStickiness = () => {
    shouldStickToBottom = isNearBottom();
  };

  const scrollToBottom = (behavior: ScrollBehavior) => {
    listElement?.scrollTo({ top: listElement.scrollHeight, behavior });
  };

  $effect(() => {
    scrollSignature;
    generationState;

    if (!shouldStickToBottom) return;

    void tick().then(() => {
      const prefersReducedMotion = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
      scrollToBottom(prefersReducedMotion || generationState === 'streaming' ? 'auto' : 'smooth');
    });
  });
</script>

<section bind:this={listElement} class="message-list" aria-label="Conversation messages" onscroll={updateStickiness}>
  <div class="message-list-inner">
    {#each messages as message (message.id)}
      <MessageBubble {message} />
    {/each}
  </div>
</section>
