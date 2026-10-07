import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import StudentActiveRoomView from './StudentActiveRoomView.vue'
let wrapper
afterEach(() => {
  wrapper?.unmount()
  localStorage.clear()
})
function render(props = {}) {
  wrapper = mount(StudentActiveRoomView, {
    props: {
      task: {
        title: 'Сумма',
        statement_md: '## Условие\nСложите числа.',
        difficulty: 'easy',
      },
      submitCode: 'print(3)',
      ...props,
    },
    global: {
      stubs: {
        Codemirror: { template: '<textarea aria-label="Код решения" />' },
      },
    },
  })
  return wrapper
}
describe('round workspace', () => {
  it('starts focused on code and supports the task tab and split layout', async () => {
    render()
    expect(wrapper.find('.arena-solution').exists()).toBe(true)
    const tabs = wrapper.findAll('.workspace-tabs button')
    await tabs[1].trigger('click')
    expect(wrapper.find('.arena-workspace').classes()).toContain('show-task')
    expect(wrapper.find('.markdown-text h2').text()).toBe('Условие')
    await wrapper.find('.split-toggle').trigger('click')
    expect(wrapper.find('.arena-workspace').classes()).toContain('is-split')
    expect(localStorage.getItem('gcb:layout')).toBe('split')
  })
  it('blocks submission during checking, offline and for an empty draft', async () => {
    render({ isChecking: true })
    expect(wrapper.find('.btn-primary').attributes('disabled')).toBeDefined()
    await wrapper.setProps({ isChecking: false, canSubmit: false })
    expect(wrapper.find('.btn-primary').attributes('disabled')).toBeDefined()
    await wrapper.setProps({ canSubmit: true, submitCode: '  ' })
    expect(wrapper.find('.btn-primary').attributes('disabled')).toBeDefined()
    await wrapper.setProps({ submitCode: 'print(3)' })
    await wrapper.find('.btn-primary').trigger('click')
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })
})
