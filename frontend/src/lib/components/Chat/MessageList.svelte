<script lang="ts">
  import { afterUpdate } from 'svelte';
  import MessageBubble from './MessageBubble.svelte';
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    messages: ChatMessage[];
  }

  let { messages }: Props = $props();
  let listElement: HTMLDivElement;

  afterUpdate(() => {
    listElement?.scrollTo({ top: listElement.scrollHeight, behavior: 'smooth' });
  });
</script>

<section bind:this={listElement} class="message-list" aria-label="Conversation messages">
  <div class="message-list-inner">
    {#each messages as message (message.id)}
      <MessageBubble {message} />
    {/each}
  </div>
</section>
