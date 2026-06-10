import DOMPurify from 'dompurify';
import { marked } from 'marked';

marked.use({
  gfm: true,
  breaks: true
});

export function renderAssistantMarkdown(source: string): string {
  const rendered = marked.parse(source, { async: false }) as string;

  return DOMPurify.sanitize(rendered, {
    USE_PROFILES: { html: true },
    ALLOWED_ATTR: ['href', 'title', 'target', 'rel'],
    ALLOWED_TAGS: [
      'a',
      'blockquote',
      'br',
      'code',
      'em',
      'hr',
      'li',
      'ol',
      'p',
      'pre',
      'strong',
      'ul'
    ]
  });
}
