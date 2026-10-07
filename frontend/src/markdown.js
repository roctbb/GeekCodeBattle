import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const markdown = new MarkdownIt({ html: false, breaks: true, linkify: false })
// Task content must never load tracking pixels or CDN resources.
markdown.renderer.rules.image = (tokens, index) =>
  markdown.utils.escapeHtml(tokens[index].content || 'Изображение')
export function renderMarkdown(source) {
  return DOMPurify.sanitize(markdown.render(String(source || '')), {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['img', 'iframe', 'style'],
  })
}
