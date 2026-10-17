// @vitest-environment node
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import { expect, it } from 'vitest'
const source = readFileSync('public/theme-init.js', 'utf8')
it.each([
  ['light', true, 'light'], ['dark', false, 'dark'], ['system', true, 'dark'], ['invalid', false, 'light'],
])('applies saved preference %s before the app starts', (preference, dark, expected) => {
  const element = { dataset:{}, style:{} }
  runInNewContext(source, { document:{ documentElement:element }, localStorage:{ getItem:() => preference }, matchMedia:() => ({ matches:dark }) })
  expect(element.dataset).toEqual({ theme:expected, bsTheme:expected })
  expect(element.style.colorScheme).toBe(expected)
})
it('can paint a default theme with blocked storage and no media query API', () => {
  const element = { dataset:{}, style:{} }
  runInNewContext(source, { document:{ documentElement:element }, localStorage:{ getItem:() => { throw new Error('blocked') } } })
  expect(element.dataset.theme).toBe('light')
})
