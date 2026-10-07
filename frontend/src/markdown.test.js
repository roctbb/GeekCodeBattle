import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './markdown'

describe('task Markdown', () => {
  it('renders readable headings, emphasis, code and examples', () => {
    const result = renderMarkdown(
      '## Условие\n**Сумма** `a + b`\n\n```python\nprint(3)\n```',
    )
    expect(result).toContain('<h2>Условие</h2>')
    expect(result).toContain('<strong>Сумма</strong>')
    expect(result).toContain('print(3)')
  })
  it('does not execute HTML or load external images and frames', () => {
    const output = document.createElement('div')
    output.innerHTML = renderMarkdown(
      '<script>alert(1)</script>\n<img src="https://cdn.example/a.png" onerror="alert(1)">\n![example](https://cdn.example/pixel)\n[unsafe](javascript:alert(1))',
    )
    expect(output.querySelector('script,img,iframe,[onerror],[src]')).toBeNull()
    expect(output.querySelector('[href^="javascript:"]')).toBeNull()
  })
})
