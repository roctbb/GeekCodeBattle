import { afterEach, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TestResult from './TestResult.vue'
let wrapper
afterEach(() => wrapper?.unmount())
it('keeps passed examples compact and makes raw output available on demand', () => {
  wrapper = mount(TestResult, { props: { test: { passed: true, input: '1 2', actual: '3', expected: '3' } } })
  expect(wrapper.text()).toContain('Пройден')
  expect(wrapper.find('.code-diff').exists()).toBe(false)
  expect(wrapper.get('details').attributes('open')).toBeUndefined()
})
it('opens a meaningful output comparison for a failed example', () => {
  wrapper = mount(TestResult, { props: { test: { passed: false, input: '1 2', actual: '4', expected: '3' } } })
  expect(wrapper.get('details').attributes('open')).toBeDefined()
  expect(wrapper.text()).toContain('Ожидалось')
  expect(wrapper.text()).toContain('Получено')
  expect(wrapper.get('.removed code').text()).toBe('3')
  expect(wrapper.get('.added code').text()).toBe('4')
})
it('renders custom output as text without inventing an assessment', () => {
  wrapper = mount(TestResult, { props: { custom: true, test: { actual: '<script>test</script>', expected: null } } })
  expect(wrapper.get('.run-output').text()).toBe('<script>test</script>')
  expect(wrapper.find('script').exists()).toBe(false)
  expect(wrapper.find('.code-diff').exists()).toBe(false)
  expect(wrapper.text()).not.toContain('Пройден')
})
