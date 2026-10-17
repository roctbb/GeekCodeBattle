import { afterEach, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'
import TeacherTaskEditorView from './TeacherTaskEditorView.vue'
let wrapper
function setup(tests) {
  const form = reactive({ title:'Сумма', statement_md:'**Сложите** числа', difficulty:'medium', check_type:'tests', tests_json:JSON.stringify(tests) })
  wrapper = mount(TeacherTaskEditorView, { props:{ hasTask:true, packageName:'Основы', packageTaskForm:form }, attachTo:document.body })
  return form
}
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = '' })
it('paginates tests without losing order, hidden flags or other test metadata', async () => {
  const tests = Array.from({ length:8 }, (_,i) => ({ input:String(i), expected:String(i + 1), hidden:i > 0, weight:i }))
  const form = setup(tests)
  expect(wrapper.findAll('.test-case')).toHaveLength(6)
  await wrapper.get('[aria-label="Следующие тесты"]').trigger('click')
  expect(wrapper.findAll('.test-case')).toHaveLength(2)
  await wrapper.get('#input-6').setValue('changed')
  const saved = JSON.parse(form.tests_json)
  expect(saved[6]).toEqual({ ...tests[6], input:'changed' })
  expect(saved.slice(0,6)).toEqual(tests.slice(0,6))
  await wrapper.findAll('button').find(b => b.text() === 'Добавить тест').trigger('click')
  expect(JSON.parse(form.tests_json)).toHaveLength(9)
  expect(document.activeElement.id).toBe('input-8')
})
it('blocks invalid JSON and duplicate saves while saving, and supports keyboard save', async () => {
  const form = setup([])
  await wrapper.get('#task-title').trigger('keydown', { key:'s', ctrlKey:true })
  expect(wrapper.emitted('save')).toHaveLength(1)
  await wrapper.setProps({ saving:true })
  await wrapper.get('#task-title').trigger('keydown', { key:'s', metaKey:true })
  expect(wrapper.emitted('save')).toHaveLength(1)
  await wrapper.setProps({ saving:false })
  form.tests_json = '{'; await wrapper.vm.$nextTick()
  expect(wrapper.get('[role="alert"]').text()).toContain('Некорректный JSON')
  expect(wrapper.get('#task-tests-json').exists()).toBe(true)
  expect(wrapper.get('.save-task').attributes('disabled')).toBeDefined()
})
