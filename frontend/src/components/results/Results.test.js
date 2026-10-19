import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import StudentBattleLobbyView from '../student/StudentBattleLobbyView.vue'
import TeacherBattleStatistics from '../teacher/TeacherBattleStatistics.vue'
import BattleResultDetail from './BattleResultDetail.vue'
const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('../../api', () => ({default: mocks}))
let wrapper
const global = { stubs: {RouterLink: {template: '<a><slot /></a>'}} }
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })

it('requires an invite and exposes an actionable error before successful admission', async () => {
  wrapper = mount(StudentBattleLobbyView, {global})
  expect(wrapper.get('button').attributes('disabled')).toBeDefined()
  await wrapper.get('input').setValue('BADCODE')
  mocks.post.mockRejectedValueOnce({response:{data:{error:{message:'Инвайт не найден'}}}})
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(wrapper.get('[role=alert]').text()).toContain('Инвайт не найден')
  expect(wrapper.emitted('joined')).toBeUndefined()
  mocks.post.mockResolvedValueOnce({data:{id:'battle'}})
  await wrapper.get('input').setValue('PYTHON-7A')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(mocks.post).toHaveBeenLastCalledWith('/battles/join',{code:'PYTHON-7A'})
  expect(wrapper.emitted('joined')[0][0]).toEqual({id:'battle'})
})

const data = {battle:{id:'battle',title:'Батл',status:'finished'},summary:{participants:1,tasks:2,solved:1,attempts:2,pending:0},tasks:[{id:'one',title:'Сумма'},{id:'two',title:'Цикл'}],students:[{user_id:'masha',name:'Маша',place:1,points:140,rating_delta:12,assigned:1,solved:1,unsolved:0,not_assigned:1,attempts:2,pending:0,tasks:[{task_id:'one',title:'Сумма',state:'solved',assigned:true,attempts:2,statement_md:'**Сложите** числа',difficulty:'easy',submissions:[{id:'ok',source_code:'print(3)',language:'python',verdict:'accepted',progress:1},{id:'wrong',source_code:'<script>alert(1)</script>',language:'python',verdict:'wrong_answer',progress:0}]},{task_id:'two',title:'Цикл',state:'not_assigned',assigned:false,attempts:0,statement_md:'Цикл',submissions:[]}]}]}

it('shows the error category and total count including hidden tests in personal history', async () => {
  const report = structuredClone(data)
  report.students[0].tasks[0].submissions = [{
    id: 'limited', source_code: 'while True: pass', language: 'python', verdict: 'time_limit_exceeded',
    progress: 2 / 7, tests_passed: 2, tests_total: 7, visible_tests_passed: 1, visible_tests_total: 1,
    comment: 'Превышен лимит времени.',
  }]
  mocks.get.mockResolvedValue({ data: report })
  wrapper = mount(BattleResultDetail, { props: { path: '/me/results/battle', taskId: 'one' }, global })
  await flushPromises()
  expect(wrapper.text()).toContain('Превышен лимит времени')
  expect(wrapper.text()).toContain('Пройдено тестов: 2 из 7 (включая скрытые)')
  expect(wrapper.text()).not.toContain('Публичные тесты: 1/1')
})
it('opens a specific student and task from the teacher matrix', async () => {
  mocks.get.mockResolvedValue({data})
  wrapper=mount(TeacherBattleStatistics,{props:{battleId:'battle'},global})
  await flushPromises()
  expect(wrapper.findAll('.matrix-cell')).toHaveLength(0)
  await wrapper.findAll('button').find(b => b.text() === 'По задачам').trigger('click')
  const cell=wrapper.findAll('button').find(b=>b.attributes('aria-label')?.includes('Сумма'))
  await cell.trigger('click')
  expect(wrapper.emitted('open-student')[0][0]).toEqual({studentId:'masha',taskId:'one'})
  await wrapper.get('[aria-label="Поиск ученика"]').setValue('Другой')
  expect(wrapper.text()).toContain('По запросу никого не найдено')
})
it('shows both accepted and failed code as text and distinguishes unassigned tasks', async () => {
  mocks.get.mockResolvedValue({data})
  wrapper=mount(BattleResultDetail,{props:{path:'/me/results/battle',taskId:'one'},global})
  await flushPromises()
  expect(mocks.get).toHaveBeenCalledWith('/me/results/battle')
  expect(wrapper.text()).toContain('print(3)')
  expect(wrapper.text()).toContain('<script>alert(1)</script>')
  expect(wrapper.find('script').exists()).toBe(false)
  expect(wrapper.text()).toContain('Не выдавалась')
  await wrapper.get('select').setValue('unsolved')
  expect(wrapper.findAll('.result-task')).toHaveLength(0)
})

it('shows the real tournament position, movement and neighboring participants', async () => {
  mocks.get.mockResolvedValue({ data: { ...data, standing: { place: 3, total: 12, previous_place: 5, change: 2,
    neighbors: [{ user_id: 'other', name: 'Аня', place: 2, battle_points: 150 }, { user_id: 'masha', name: 'Маша', place: 3, battle_points: 140 }] } } })
  wrapper = mount(BattleResultDetail, { props: { path: '/me/results/battle' }, global })
  await flushPromises()
  expect(wrapper.get('.standing-place').text()).toBe('3 из 12')
  expect(wrapper.get('.standing-change').text()).toContain('↑ 2')
  expect(wrapper.get('.standing-neighbors .is-me').text()).toContain('МашаВы')
  expect(wrapper.get('.standing-neighbors .is-me').text()).toContain('140')
  expect(wrapper.text()).toContain('Аня')
})
