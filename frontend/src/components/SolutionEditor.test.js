import { afterEach, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SolutionEditor from './SolutionEditor.vue'
let wrapper
afterEach(() => wrapper?.unmount())
it('preserves each language undo history while switching editor models', async () => {
  wrapper = mount(SolutionEditor, {
    props: {
      identity: 'room:python',
      language: 'python',
      modelValue: 'print(1)',
      fontSize: 15,
      tabSize: 4,
      theme: 'dark',
    },
  })
  await wrapper.setProps({ modelValue: 'print(2)' })
  expect(wrapper.get('.cm-content').text()).toBe('print(2)')
  await wrapper.setProps({
    identity: 'room:cpp',
    language: 'cpp',
    modelValue: 'int main(){}',
  })
  expect(wrapper.get('.cm-content').text()).toBe('int main(){}')
  await wrapper.setProps({
    identity: 'room:python',
    language: 'python',
    modelValue: 'print(2)',
  })
  wrapper.vm.undo()
  expect(wrapper.get('.cm-content').text()).toBe('print(1)')
  expect(wrapper.emitted('update:modelValue').at(-1)).toEqual(['print(1)'])
})

it('reconciles a cached document when identities change but the model text is equal', async () => {
  wrapper = mount(SolutionEditor, {
    props: { identity: 'room:python', language: 'python', modelValue: 'old draft' },
  })
  await wrapper.setProps({ identity: 'room:cpp', language: 'cpp', modelValue: 'restored code' })
  await wrapper.setProps({ identity: 'room:python', language: 'python' })
  expect(wrapper.get('.cm-content').text()).toBe('restored code')
  expect(wrapper.emitted('cursor').at(-1)).toEqual([{ line: 1, column: 1 }])
  wrapper.vm.undo()
  expect(wrapper.get('.cm-content').text()).toBe('old draft')
})

it('shows gutter and inline diagnostics only for the exact checked source and language', async () => {
  const source = 'value = 1\nprint(value / 0)'
  wrapper = mount(SolutionEditor, { props: { modelValue: source, language: 'python', identity: 'room:python',
    diagnostics: { source_code: source, language: 'python', items: [{ line: 2, severity: 'error', message: 'division by zero' }] } } })
  expect(wrapper.find('.cm-lint-marker-error').exists()).toBe(true)
  expect(wrapper.get('.cm-lintRange-error').text()).toBe('print(value / 0)')
  await wrapper.setProps({ modelValue: source + '\nprint(2)' })
  expect(wrapper.find('.cm-lint-marker-error').exists()).toBe(false)
  await wrapper.setProps({ modelValue: source, language: 'cpp', identity: 'room:cpp' })
  expect(wrapper.find('.cm-lintRange-error').exists()).toBe(false)
})

it('prioritizes run and submit shortcuts over default editor commands', async () => {
  wrapper = mount(SolutionEditor, { props: { modelValue: 'print(1)', language: 'python' } })
  await wrapper.get('.cm-content').trigger('keydown', { key: 'Enter', code: 'Enter', ctrlKey: true })
  await wrapper.get('.cm-content').trigger('keydown', { key: 'Enter', code: 'Enter', ctrlKey: true, shiftKey: true })
  expect(wrapper.emitted('run')).toHaveLength(1)
  expect(wrapper.emitted('submit')).toHaveLength(1)
  expect(wrapper.get('.cm-content').text()).toBe('print(1)')
})
