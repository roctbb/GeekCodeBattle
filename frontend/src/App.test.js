import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
const mocks = vi.hoisted(() => ({
  handlers: {},
  get: vi.fn(),
  post: vi.fn(),
  emit: vi.fn(),
  disconnect: vi.fn(),
}))
vi.mock('./api', () => ({ default: { get: mocks.get, post: mocks.post } }))
vi.mock('socket.io-client', () => ({
  io: () => ({
    on: (event, callback) => {
      mocks.handlers[event] = callback
    },
    emit: mocks.emit,
    disconnect: mocks.disconnect,
    connect: vi.fn(),
  }),
}))
import App from './App.vue'
let wrapper
afterEach(() => {
  wrapper?.unmount()
  vi.clearAllMocks()
  localStorage.clear()
})

it('saves separate language drafts and restores them after a language switch', async () => {
  const me={id:'draft-user',role:'student',name:'Игрок'}
  mocks.get.mockImplementation(async path=>({data:{'/auth/options':{dev_login_enabled:true,geekclass_enabled:false},'/me':me,'/battles':[{id:'battle',title:'Батл',status:'running'}],'/me/state':{me,room_id:'room',match_id:'match',battle_id:'battle'},'/rooms/room':{status:'active',task:{id:'task',title:'Сумма'},participants:[]}}[path]}))
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:{template:'<div />'}}]})
  await router.push('/')
  wrapper=mount(App,{global:{plugins:[router],stubs:{StudentActiveRoomView:true}}})
  await flushPromises()
  const editor=wrapper.findComponent({name:'StudentActiveRoomView'})
  editor.vm.$emit('update:submit-code','print(42)');await flushPromises()
  editor.vm.$emit('update:submit-language','cpp');await flushPromises()
  expect(editor.attributes('submit-code')).toBe('')
  editor.vm.$emit('update:submit-code','int main(){}');await flushPromises()
  editor.vm.$emit('update:submit-language','python');await flushPromises()
  expect(editor.attributes('submit-code')).toBe('print(42)')
  const draft=JSON.parse(localStorage.getItem('gcb:submit-draft:v1:draft-user:room'))
  expect(draft.drafts).toEqual({python:'print(42)',cpp:'int main(){}'})
})

it('restores every language draft when undoing a submission restore', async () => {
  const me = { id: 'restore-user', role: 'student', name: 'Игрок' }
  mocks.get.mockImplementation(async path => ({ data: {
    '/auth/options': { dev_login_enabled: true, geekclass_enabled: false }, '/me': me,
    '/battles': [{ id: 'battle', title: 'Батл', status: 'running' }],
    '/me/state': { me, room_id: 'room', match_id: 'match', battle_id: 'battle' },
    '/rooms/room': { status: 'active', task: { id: 'task', title: 'Сумма' }, participants: [] },
  }[path] }))
  const key = 'gcb:submit-draft:v1:restore-user:room'
  localStorage.setItem(key, JSON.stringify({ version: 3, language: 'python', source_code: 'python draft',
    drafts: { python: 'python draft', cpp: 'cpp draft' } }))
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/results/:battleId', name: 'my-result-detail', component: { template: '<div />' } },
  ] })
  await router.push('/results/battle')
  wrapper = mount(App, { global: { plugins: [router], stubs: { StudentActiveRoomView: true, BattleResultDetail: true } } })
  await flushPromises()
  wrapper.findComponent({ name: 'BattleResultDetail' }).vm.$emit('restore', {
    taskId: 'task', language: 'cpp', source_code: 'archived solution',
  })
  await flushPromises()
  let editor = wrapper.findComponent({ name: 'StudentActiveRoomView' })
  expect(editor.attributes('submit-code')).toBe('archived solution')
  editor.vm.$emit('restore-draft')
  await flushPromises()
  expect(editor.attributes('submit-code')).toBe('python draft')
  editor.vm.$emit('update:submit-language', 'cpp')
  await flushPromises()
  expect(editor.attributes('submit-code')).toBe('cpp draft')
})

it('ignores invalid persisted volume and draft types', async () => {
  const me = { id: 'invalid-draft', role: 'student', name: 'Игрок' }
  mocks.get.mockImplementation(async path => ({ data: {
    '/auth/options': { dev_login_enabled: true }, '/me': me,
    '/battles': [{ id: 'battle', title: 'Батл', status: 'running' }],
    '/me/state': { me, room_id: 'room', match_id: 'match', battle_id: 'battle' },
    '/rooms/room': { status: 'active', task: { id: 'task', title: 'Сумма' }, participants: [] },
  }[path] }))
  localStorage.setItem('codebattle:experience', JSON.stringify({ volume: 'bad' }))
  localStorage.setItem('gcb:submit-draft:v1:invalid-draft:room', JSON.stringify({
    version: 3, language: 'unknown', source_code: { broken: true }, drafts: { python: 'valid fallback' },
  }))
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  await router.push('/')
  wrapper = mount(App, { global: { plugins: [router], stubs: { StudentActiveRoomView: true } } })
  await flushPromises()
  const editor = wrapper.findComponent({ name: 'StudentActiveRoomView' })
  expect(editor.attributes('submit-language')).toBe('python')
  expect(editor.attributes('submit-code')).toBe('valid fallback')
  expect(wrapper.text()).toContain('Громкость 40%')
})
it('restores a missed round finish, opens stopped battle results, and resumes through admission', async () => {
  const me = { id: 'student', role: 'student', name: 'Маша', win_streak: 0 }
  let state = {
    me,
    battle_id: 'battle',
    room_id: 'room',
    match_id: 'match',
    last_result: null,
  }
  mocks.get.mockImplementation(async (path) => ({
    data: {
      '/auth/options': { dev_login_enabled: true, geekclass_enabled: false },
      '/me': me,
      '/battles': [{ id: 'battle', title: 'Баттл', status: 'running' }],
      '/me/state': state,
      '/rooms/room': {
        status: 'active',
        task: { title: 'Сумма' },
        participants: [],
        my_submission: { verdict: 'queued' },
      },
      '/battles/battle/queue': { entries: [] },
      '/battles/battle/leaderboard': { participants: [] },
    }[path],
  }))
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/results/:battleId', name: 'my-result-detail', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  wrapper = mount(App, {
    global: {
      plugins: [router],
      stubs: { StudentActiveRoomView: true, StudentJoinedBattleView: true, BattleResultDetail: true },
    },
  })
  await flushPromises()
  const initialRequests = mocks.get.mock.calls.filter(
    ([url]) => url === '/me/state',
  ).length
  mocks.handlers.disconnect()
  await flushPromises()
  expect(wrapper.text()).toContain('Соединение потеряно')
  state = {
    me: { ...me, win_streak: 1 },
    room_id: null,
    match_id: null,
    battle_id: 'battle',
    last_result: {
      battle_id: 'battle',
      task_title: 'Сумма',
      result_type: 'win',
      points: 140,
      is_final: true,
    },
  }
  mocks.handlers.connect()
  await flushPromises()
  expect(
    mocks.get.mock.calls.filter(([url]) => url === '/me/state').length,
  ).toBeGreaterThan(initialRequests)
  expect(wrapper.text()).toContain('Победа')
  expect(wrapper.text()).toContain('+140')
  expect(wrapper.text()).not.toContain('Соединение потеряно')
  state = { ...state, battle_id: null, result_battle_id: 'battle' }
  mocks.handlers.connect()
  await flushPromises()
  expect(router.currentRoute.value.fullPath).toBe('/results/battle')
  const report = wrapper.findComponent({ name: 'BattleResultDetail' })
  expect(report.attributes('path')).toBe('/me/results/battle')
  mocks.post.mockResolvedValue({ data: {} })
  state = { ...state, battle_id: 'battle', result_battle_id: null }
  report.vm.$emit('resume', 'battle')
  await flushPromises()
  expect(mocks.post).toHaveBeenCalledWith('/battles/battle/queue/join')
  expect(router.currentRoute.value.fullPath).toBe('/')
})


it('does not restore a session from a delayed snapshot after logout', async () => {
  const me = { id: 'student', role: 'student', name: 'Маша' }
  let resolveSnapshot
  const pending = new Promise(resolve => { resolveSnapshot = resolve })
  mocks.get.mockImplementation(async path => {
    if (path === '/me/state') return pending
    return { data: { '/auth/options': { dev_login_enabled: true, geekclass_enabled: false }, '/me': me, '/battles': [] }[path] }
  })
  mocks.post.mockResolvedValue({ data: {} })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })
  await router.push('/')
  wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  await wrapper.findAll('button').find(button => button.text() === 'Выйти').trigger('click')
  await flushPromises()
  resolveSnapshot({ data: { me, room_id: null, battle_id: null, last_result: null } })
  await flushPromises()
  expect(wrapper.text()).not.toContain('Маша')
  expect(wrapper.text()).not.toContain('Выйти')
})

it('loads the requested task on a direct teacher link', async () => {
  const task = { id: 'task', title: 'Сумма', statement_md: '**Условие**', difficulty: 'easy', check_type: 'tests', config: { tests: [] } }
  mocks.get.mockImplementation(async path => ({ data: {
    '/auth/options': { dev_login_enabled: true, geekclass_enabled: false },
    '/me': { id: 'teacher', role: 'teacher', name: 'Учитель' }, '/battles': [],
    '/task-packages': [{ id: 'package', name: 'Основы' }],
    '/task-packages/package': { package: { id: 'package', name: 'Основы' }, tasks: [task] },
  }[path] }))
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/packages/:packageId/tasks/:taskId', name: 'package-task-editor', component: { template: '<div />' } }] })
  await router.push('/packages/package/tasks/task')
  wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  await vi.waitFor(() => expect(wrapper.find('#task-title').exists()).toBe(true))
  expect(wrapper.get('#task-title').element.value).toBe('Сумма')
  expect(wrapper.text()).toContain('Так увидит ученик')
})

it('does not replay historical celebrations and announces an observed round only once', async () => {
  const me={id:'event-user',role:'student',name:'Игрок',win_streak:0}
  let state={me,room_id:'room',match_id:'match',battle_id:'battle',last_result:{match_id:'old',battle_id:'battle',task_title:'Прошлая задача',result_type:'win',points:140,is_final:true}}
  mocks.get.mockImplementation(async path=>({data:structuredClone({'/auth/options':{dev_login_enabled:true,geekclass_enabled:false},'/me':me,'/battles':[{id:'battle',title:'Батл',status:'running'}],'/me/state':state,'/rooms/room':{status:'active',task:{id:'task',title:'Сумма'},participants:[]},'/battles/battle/queue':{entries:[]},'/battles/battle/leaderboard':{participants:[]}}[path])}))
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:{template:'<div />'}}]})
  await router.push('/')
  wrapper=mount(App,{global:{plugins:[router],stubs:{StudentActiveRoomView:true,StudentJoinedBattleView:true}}})
  await flushPromises()
  mocks.handlers.connect();await flushPromises()
  expect(wrapper.find('.battle-event').exists()).toBe(false)
  state={...state,room_id:null,match_id:null,last_result:{...state.last_result,match_id:'match',task_title:'Сумма'}}
  mocks.handlers.connect();await flushPromises()
  await vi.waitFor(() => expect(wrapper.find('.battle-event').exists()).toBe(true))
  expect(wrapper.get('.battle-event h2').text()).toBe('Победа')
  await wrapper.get('.battle-event button').trigger('click')
  mocks.handlers.connect();await flushPromises()
  expect(wrapper.find('.battle-event').exists()).toBe(false)
})
