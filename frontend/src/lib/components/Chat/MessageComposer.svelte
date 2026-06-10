<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{ send: string }>();

  let draft = '';

  function sendMessage() {
    const content = draft.trim();

    if (!content) {
      return;
    }

    dispatch('send', content);
    draft = '';
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }
</script>

<form class="composer" on:submit|preventDefault={sendMessage} aria-label="Message composer">
  <textarea
    bind:value={draft}
    on:keydown={handleKeydown}
    rows="1"
    placeholder="Write to your companion..."
    aria-label="Message text"
  ></textarea>
  <button type="submit" disabled={!draft.trim()} aria-label="Send message">
    Send
  </button>
</form>

<style>
  .composer {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0.85rem;
    padding: 1rem 1.2rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 1.35rem;
    background: rgba(255, 255, 255, 0.065);
    box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
  }

  textarea {
    width: 100%;
    max-height: 10rem;
    min-height: 2.8rem;
    resize: vertical;
    border: 0;
    outline: 0;
    background: transparent;
    color: #fff8f4;
    font: inherit;
    line-height: 1.55;
  }

  textarea::placeholder {
    color: #887d89;
  }

  button {
    align-self: end;
    min-width: 5.7rem;
    height: 2.8rem;
    border: 0;
    border-radius: 0.95rem;
    background: linear-gradient(135deg, #ff8f78, #b28cff);
    color: #170e18;
    cursor: pointer;
    font-weight: 800;
    box-shadow: 0 15px 35px rgba(255, 143, 120, 0.25);
    transition:
      opacity 160ms ease,
      transform 160ms ease;
  }

  button:hover:not(:disabled) {
    transform: translateY(-1px);
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.45;
  }

  @media (max-width: 560px) {
    .composer {
      grid-template-columns: 1fr;
    }

    button {
      width: 100%;
    }
  }
</style>
