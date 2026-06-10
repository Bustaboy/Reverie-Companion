<script lang="ts">
  import { tick } from 'svelte';
  import MessageBubble from './MessageBubble.svelte';
  import type { ChatMessage } from '$lib/types/chat';

  interface Props {
    messages: ChatMessage[];
  }

  let { messages }: Props = $props();
  let listElement: HTMLDivElement;

  const latestMessageId = $derived(messages[messages.length - 1]?.id);

  $effect(() => {
    latestMessageId;

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
  </div>
</section>
