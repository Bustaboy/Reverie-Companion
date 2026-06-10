<script lang="ts">
  import { tick } from 'svelte';
  import type { ChatMessage } from '$lib/types/chat';
  import MessageBubble from './MessageBubble.svelte';

  interface Props {
    messages: ChatMessage[];
  }

  let { messages }: Props = $props();
  let scrollContainer: HTMLDivElement;

  $effect(() => {
    messages.length;
    tick().then(() => {
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    });
  });
</script>

<section class="message-list" bind:this={scrollContainer} aria-label="Conversation messages">
  <div class="message-list-inner">
    {#each messages as message (message.id)}
      <MessageBubble {message} />
    {/each}
  </div>
</section>
