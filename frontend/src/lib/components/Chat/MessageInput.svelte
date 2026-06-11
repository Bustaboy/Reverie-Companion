<script lang="ts">
  interface Props {
    onSend: (message: string) => void;
  }

  let { onSend }: Props = $props();
  let draft = $state('');

  const send = () => {
    const value = draft.trim();
    if (!value) return;

    onSend(value);
    draft = '';
  };

  const handleKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };
</script>

<form class="message-composer" onsubmit={(event) => { event.preventDefault(); send(); }}>
  <label class="sr-only" for="message-input">Message Reverie</label>
  <textarea
    id="message-input"
    bind:value={draft}
    onkeydown={handleKeydown}
    placeholder="Share what is on your mind..."
    rows="1"
  ></textarea>

  <button type="submit" disabled={!draft.trim()} aria-label="Send message">
    <span>Send</span>
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3.4 20.4 21.2 12 3.4 3.6 6 10.8l8.3 1.2L6 13.2l-2.6 7.2Z" />
    </svg>
  </button>
</form>
