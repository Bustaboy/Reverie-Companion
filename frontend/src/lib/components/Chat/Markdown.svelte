<script lang="ts">
  import { renderMarkdown } from '$lib/utils/markdown';

  interface Props {
    content: string;
  }

  let { content }: Props = $props();
</script>

<div class="markdown-content">
  {@html renderMarkdown(content)}
</div>
