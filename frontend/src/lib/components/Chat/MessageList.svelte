<script lang="ts">
  import { tick } from 'svelte';
  import MessageBubble from './MessageBubble.svelte';
  import type { ChatGenerationState } from '$lib/stores/chatStore';
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    messages: ChatMessage[];
    generationState: ChatGenerationState;
  }

  let { messages, generationState }: Props = $props();
  let listElement: HTMLElement;

  const scrollSignature = $derived(
    messages.map((message) => `${message.id}:${message.content.length}:${message.status ?? 'complete'}`).join('|')
  );

  $effect(() => {
    scrollSignature;

    void tick().then(() => {
      listElement?.scrollTo({ top: listElement.scrollHeight, behavior: 'smooth' });
    });
  });
</script>

<section bind:this={listElement} class="message-list" aria-label="Conversation messages">
  <div class="message-list-inner">
    {#each messages as message (message.id)}
      <MessageBubble {message} />
    {/each}

    {#if generationState === 'thinking'}
      <p class="thinking-state" aria-live="polite">Reverie is thinking<span aria-hidden="true">...</span></p>
    {/if}
  </div>
</section>
