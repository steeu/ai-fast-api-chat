import DOMPurify from 'dompurify'
import { Marked } from 'marked'

const marked = new Marked({ gfm: true, breaks: true, async: false })

// Open links from AI answers in a new tab
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

/** Markdown → sanitized HTML. Marked doesn't sanitize, so model output must go through DOMPurify. */
export function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(marked.parse(text) as string)
}
