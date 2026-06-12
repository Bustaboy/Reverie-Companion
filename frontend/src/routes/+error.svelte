<script lang="ts">
  import { page } from '$app/stores';
</script>

<svelte:head>
  <title>Reverie recovered</title>
</svelte:head>

<section class="app-error-boundary" aria-labelledby="reverie-error-title">
  <div class="error-card">
    <p class="eyebrow">Graceful recovery</p>
    <h1 id="reverie-error-title">Something in this panel stumbled.</h1>
    <p>
      Chat, memory, voice, and local files are kept separate so one unavailable feature should not take down the whole companion.
      You can return home, lower the 8GB performance preset, or retry after optional services like ComfyUI finish starting.
    </p>
    {#if $page.error?.message}
      <pre>{$page.error.message}</pre>
    {/if}
    <a href="/">Return to Reverie</a>
  </div>
</section>
