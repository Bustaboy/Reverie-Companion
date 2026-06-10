import { marked } from 'marked';

marked.use({
  gfm: true,
  breaks: true
});

const htmlEntities: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
};

export const escapeHtml = (value: string) =>
  value.replace(/[&<>"']/g, (character) => htmlEntities[character]);

export const renderMarkdown = (value: string) =>
  marked.parse(escapeHtml(value), { async: false }) as string;
