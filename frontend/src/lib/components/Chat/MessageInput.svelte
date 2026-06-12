<script lang="ts">
  import { tick } from 'svelte';

  interface Props {
    onSend: (message: string) => void;
    disabled?: boolean;
  }

  let { onSend, disabled = false }: Props = $props();
  let draft = $state('');
  let textareaElement: HTMLTextAreaElement;

  const canSend = $derived(draft.trim().length > 0 && !disabled);
  const draftLength = $derived(draft.trim().length);

  const resizeComposer = () => {
    if (!textareaElement) return;

    textareaElement.style.height = 'auto';
    textareaElement.style.height = `${Math.min(textareaElement.scrollHeight, 192)}px`;
  };

  const focusComposer = async () => {
    await tick();
    textareaElement?.focus();
  };

  const send = () => {
    const value = draft.trim();
    if (!value || disabled) return;

    onSend(value);
    draft = '';
    resizeComposer();
  };

  const handleInput = () => {
    resizeComposer();
  };

  const handleKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };

  $effect(() => {
    disabled;

    if (!disabled) {
      void focusComposer();
    }
  });

  $effect(() => {
    draft;
    resizeComposer();
  });
</script>

<form
  class:composer-disabled={disabled}
  class="message-composer"
  aria-busy={disabled}
  onsubmit={(event) => {
    event.preventDefault();
    send();
  }}
>
  <label class="sr-only" for="message-input">Message Reverie</label>
  <textarea
    id="message-input"
    bind:this={textareaElement}
    bind:value={draft}
    oninput={handleInput}
    onkeydown={handleKeydown}
    placeholder={disabled ? 'Reverie is finishing her thought...' : 'Share what is on your mind...'}
    rows="1"
    aria-disabled={disabled}
    aria-describedby="message-input-help"
    readonly={disabled}
  ></textarea>

  <button type="submit" disabled={!canSend} aria-label="Send message">
    <span>{disabled ? 'Thinking' : 'Send'}</span>
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3.4 20.4 21.2 12 3.4 3.6 6 10.8l8.3 1.2L6 13.2l-2.6 7.2Z" />
    </svg>
  </button>

  <p id="message-input-help" class="composer-help">Enter sends, Shift+Enter adds a line. {draftLength > 0 ? `${draftLength} character${draftLength === 1 ? '' : 's'}` : 'Your draft stays local until you send.'}</p>
</form>
