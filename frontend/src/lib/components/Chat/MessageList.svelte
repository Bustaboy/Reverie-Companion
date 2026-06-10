<script lang="ts">
  import { afterUpdate } from 'svelte';
  import type { ChatMessage } from '$lib/types/chat';
  import MessageBubble from './MessageBubble.svelte';

  export let messages: ChatMessage[] = [];

  let listElement: HTMLDivElement;

  afterUpdate(() => {
    listElement?.scrollTo({ top: listElement.scrollHeight, behavior: 'smooth' });
  });
</script>

<div class="message-list" bind:this={listElement} aria-live="polite">
  {#each messages as message (message.id)}
    <MessageBubble {message} />
  {/each}
</div>

<style>
  .message-list {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 1rem;
    min-height: 0;
    padding: 1.4rem 1.6rem 0.8rem;
    overflow-y: auto;
    scrollbar-color: rgba(255, 196, 171, 0.32) transparent;
  }

  .message-list::-webkit-scrollbar {
    width: 0.75rem;
  }

  .message-list::-webkit-scrollbar-thumb {
    border: 0.22rem solid transparent;
    border-radius: 999px;
    background: rgba(255, 196, 171, 0.32);
    background-clip: content-box;
  }

  @media (max-width: 680px) {
    .message-list {
      padding: 1rem;
    }
  }
</style>
