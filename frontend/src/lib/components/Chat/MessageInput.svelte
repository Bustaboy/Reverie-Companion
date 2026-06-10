<script lang="ts">
  interface Props {
    onSend: (content: string) => void;
  }

  let { onSend }: Props = $props();
  let draft = $state('');

  function submit() {
    const content = draft.trim();

    if (!content) return;

    onSend(content);
    draft = '';
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }
</script>

<form class="message-input" onsubmit={(event) => { event.preventDefault(); submit(); }}>
  <label class="sr-only" for="chat-draft">Message Reverie</label>
  <textarea
    id="chat-draft"
    bind:value={draft}
    rows="1"
    placeholder="Share what is on your mind…"
    onkeydown={handleKeydown}
  ></textarea>
  <button type="submit" disabled={!draft.trim()} aria-label="Send message">
    <span>Send</span>
    <span aria-hidden="true">↗</span>
  </button>
</form>
