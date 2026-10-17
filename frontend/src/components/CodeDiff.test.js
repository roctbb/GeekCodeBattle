import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CodeDiff from './CodeDiff.vue'
it('shows removed and added text safely and distinguishes final newline', async () => {
  const wrapper = mount(CodeDiff, {
    props: { before: 'print(1)\n', after: '<script>alert(1)</script>' },
  })
  expect(wrapper.find('script').exists()).toBe(false)
  expect(wrapper.get('.removed code').text()).toBe('print(1)')
  expect(wrapper.get('.added code').text()).toBe('<script>alert(1)</script>')
  await wrapper.get('input').setValue(true)
  expect(wrapper.get('.removed code').text()).toContain('↵')
  expect(wrapper.get('.added code').text()).not.toContain('↵')
  wrapper.unmount()
})
