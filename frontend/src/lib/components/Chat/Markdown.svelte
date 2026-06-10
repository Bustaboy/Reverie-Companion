<script lang="ts">
  import { marked } from 'marked';

  interface Props {
    content: string;
  }

  let { content }: Props = $props();

  marked.use({
    gfm: true,
    breaks: true
  });

  const escapeHtml = (value: string) =>
    value.replace(/[&<>"']/g, (character) => {
      const entities: Record<string, string> = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      };

      return entities[character];
    });

  const renderMarkdown = (value: string) => marked.parse(escapeHtml(value), { async: false }) as string;
</script>

<div class="markdown-content">
  {@html renderMarkdown(content)}
</div>
