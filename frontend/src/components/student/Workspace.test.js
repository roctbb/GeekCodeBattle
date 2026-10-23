import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import StudentActiveRoomView from './StudentActiveRoomView.vue'
const api = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }))
vi.mock('../../api', () => ({ default: api }))
let wrapper
const props = {
  roomId: 'room',
  meId: 'me',
  submitCode: 'print(3)',
  submitLanguage: 'python',
  task: {
    title: 'A+B',
    statement_md: 'Сложите числа',
    public_tests: [{ input: '1 2', expected: '3' }],
  },
}
const global = {
  stubs: {
    SolutionEditor: { name: 'SolutionEditor', props: ['diagnostics'], template: '<textarea aria-label="Код решения" />' },
    RouterLink: { template: '<a><slot /></a>' },
  },
}
afterEach(() => {
  wrapper?.unmount()
  vi.useRealTimers()
  vi.clearAllMocks()
  localStorage.clear()
})

it.each([
  ['compilation_error', 'Ошибка компиляции'],
  ['runtime_error', 'Ошибка времени выполнения'],
  ['time_limit_exceeded', 'Превышен лимит времени'],
  ['output_limit_exceeded', 'Превышен лимит вывода'],
])('shows %s and the count of all tests when submitting', async (verdict, label) => {
  wrapper = mount(StudentActiveRoomView, { props: { ...props, mySubmission: {
    id: 'sub', verdict, tests_passed: 2, tests_total: 7, source_code: props.submitCode, language: 'python',
  } }, global })
  await wrapper.get('.send-button').trigger('click')
  expect(wrapper.emitted('submit')).toHaveLength(1)
  expect(wrapper.findAll('.console-tabs button')[2].attributes('aria-pressed')).toBe('true')
  expect(wrapper.text()).toContain(label)
  expect(wrapper.get('.submission-test-count').text()).toBe('Пройдено тестов: 2 из 7 (включая скрытые)')
})

it('does not invent a zero count for pending or unknown results', async () => {
  wrapper = mount(StudentActiveRoomView, { props: { ...props, mySubmission: {
    id: 'sub', verdict: 'queued', tests_passed: null, tests_total: null,
  } }, global })
  await wrapper.findAll('.console-tabs button')[2].trigger('click')
  expect(wrapper.text()).toContain('Проверяется')
  expect(wrapper.find('.submission-test-count').exists()).toBe(false)
})

it('runs custom input independently of scored submission and marks stale results', async () => {
  api.post.mockResolvedValue({
    data: {
      id: 'run',
      kind: 'custom',
      language: 'python',
      source_code: 'print(3)',
      verdict: 'completed',
      tests: [{ input: '9', actual: '3', expected: null }],
    },
  })
  wrapper = mount(StudentActiveRoomView, { props, global })
  await wrapper.findAll('.console-tabs button')[1].trigger('click')
  await wrapper.get('#custom-input').setValue('9')
  await wrapper
    .findAll('button')
    .find((b) => b.attributes('aria-label') === 'Запустить свой ввод')
    .trigger('click')
  await flushPromises()
  expect(api.post).toHaveBeenCalledWith(
    '/rooms/room/runs',
    { kind: 'custom', language: 'python', source_code: 'print(3)', input: '9' },
    expect.any(Object),
  )
  expect(wrapper.emitted('submit')).toBeUndefined()
  expect(wrapper.get('.run-output').text()).toBe('3')
  expect(wrapper.find('.notice-warning').exists()).toBe(false)
  await wrapper.get('#custom-input').setValue('10')
  expect(wrapper.text()).toContain('предыдущей версии кода или входных данных')
  await wrapper.get('#custom-input').setValue('9')
  expect(wrapper.find('.notice-warning').exists()).toBe(false)
  await wrapper.setProps({ submitCode: 'print(4)' })
  expect(wrapper.text()).toContain(
    'Результат относится к предыдущей версии кода',
  )
})

it('does not apply a delayed run result after changing rooms', async () => {
  let resolve
  api.post.mockReturnValue(
    new Promise((r) => {
      resolve = r
    }),
  )
  wrapper = mount(StudentActiveRoomView, { props, global })
  await wrapper
    .findAll('button')
    .find((b) => b.attributes('aria-label') === 'Проверить примеры')
    .trigger('click')
  await wrapper.setProps({ roomId: 'next-room' })
  resolve({
    data: {
      id: 'old',
      kind: 'examples',
      verdict: 'completed',
      message: 'OLD RESULT',
      tests: [],
    },
  })
  await flushPromises()
  expect(wrapper.text()).not.toContain('OLD RESULT')
})

it('resumes an existing checker job after returning to the editor', async () => {
  vi.useFakeTimers()
  api.post.mockRejectedValue({ response: { status: 409, data: { error: {
    message: 'Previous run is still being checked', details: { run_id: 'pending-run' },
  } } } })
  api.get.mockResolvedValueOnce({ data: {
    id: 'pending-run', kind: 'examples', verdict: 'queued', tests: [],
  } }).mockResolvedValueOnce({ data: {
    id: 'pending-run', kind: 'examples', verdict: 'completed',
    language: 'python', source_code: 'print(3)', tests: [{ actual: '3', expected: '3', passed: true }],
  } })
  wrapper = mount(StudentActiveRoomView, { props, global })
  await wrapper.get('.run-button').trigger('click')
  await flushPromises()
  expect(api.get).toHaveBeenCalledWith('/rooms/room/runs/pending-run', expect.any(Object))
  expect(wrapper.text()).toContain('Код выполняется')
  await vi.advanceTimersByTimeAsync(1200)
  expect(wrapper.text()).toContain('Пройден')
  expect(wrapper.text()).not.toContain('Предыдущий запуск ещё проверяется')
})

it('keeps the task and editor locked throughout the server countdown', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-17T12:00:00Z'))
  wrapper = mount(StudentActiveRoomView, {
    props: {
      ...props,
      task: null,
      effectsEnabled: false,
      round: {
        is_preparing: true,
        server_now: '2026-10-17T12:00:00Z',
        started_at: '2026-10-17T12:00:03Z',
      },
    },
    global,
  })
  expect(wrapper.find('.arena-solution').exists()).toBe(false)
  expect(wrapper.get('.match-countdown').text()).toBe('3')
  expect(wrapper.get('.match-countdown').classes()).not.toContain('animated')
  await vi.advanceTimersByTimeAsync(3000)
  expect(wrapper.emitted('round-start')).toHaveLength(1)
  expect(wrapper.find('.arena-solution').exists()).toBe(false)
  // A request may arrive a few milliseconds early or fail. Retry without
  // exposing the editor until the server actually releases the task.
  await vi.advanceTimersByTimeAsync(1000)
  expect(wrapper.emitted('round-start')).toHaveLength(2)
  expect(wrapper.find('.arena-solution').exists()).toBe(false)
  await wrapper.setProps({ round: { is_preparing: false }, task: props.task })
  expect(wrapper.find('.arena-solution').exists()).toBe(true)
  await vi.advanceTimersByTimeAsync(6000)
  expect(wrapper.emitted('round-start')).toHaveLength(2)
})

it('binds official diagnostics to the source and clears them after editing or a newer successful run', async () => {
  const code = 'x = 1\nprint(x / 0)'
  wrapper = mount(StudentActiveRoomView, { props: { ...props, submitCode: code, mySubmission: {
    id: 'sub', language: 'python', source_code: code, created_at: '2026-10-17T12:00:00Z', verdict: 'internal_error',
    checker_message: 'File "main.py", line 2\nZeroDivisionError: division by zero',
  } }, global })
  const editor = wrapper.findComponent({ name: 'SolutionEditor' })
  expect(editor.props('diagnostics').items[0].line).toBe(2)
  await wrapper.setProps({ submitCode: code + '\nprint(3)' })
  expect(editor.props('diagnostics')).toBeNull()
  await wrapper.setProps({ submitCode: code })
  api.post.mockResolvedValueOnce({ data: { id: 'run', created_at: '2026-10-17T12:01:00Z', language: 'python', source_code: code, kind: 'examples', verdict: 'completed', tests: [{ passed: true, actual: '3', expected: '3' }] } })
  await wrapper.get('.run-button').trigger('click')
  await flushPromises()
  expect(editor.props('diagnostics').items).toEqual([])
  expect(wrapper.find('.code-diff').exists()).toBe(false)
})

it('uses a compact fullscreen layout without recreating the editor and restores page scrolling', async () => {
  wrapper = mount(StudentActiveRoomView, { props, global })
  const editor = wrapper.findComponent({ name: 'SolutionEditor' }).vm
  const original = document.body.style.overflow
  await wrapper.findAll('button').find(button => button.text() === 'На весь экран').trigger('click')
  expect(wrapper.get('.arena').classes()).toContain('is-fullscreen')
  expect(wrapper.get('.arena-workspace').classes()).not.toContain('is-split')
  expect(document.body.style.overflow).toBe('hidden')
  await wrapper.get('.focus-controls button').trigger('click')
  expect(wrapper.get('.arena-workspace').classes()).toContain('show-task')
  expect(wrapper.findComponent({ name: 'SolutionEditor' }).vm).toBe(editor)
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
  await flushPromises()
  expect(wrapper.get('.arena').classes()).not.toContain('is-fullscreen')
  expect(document.body.style.overflow).toBe(original)
  expect(wrapper.get('.run-button').attributes('aria-keyshortcuts')).toContain('+Enter')
  expect(wrapper.get('.send-button').attributes('aria-keyshortcuts')).toContain('+Shift+Enter')
})

it('counts elapsed time and unlocks surrender after ten server minutes without reloading', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-17T09:00:00Z'))
  wrapper = mount(StudentActiveRoomView, { props: { ...props, round: {
    is_active: true, started_at: '2026-10-17T12:00:00Z', server_now: '2026-10-17T12:09:59Z',
    surrender_available_at: '2026-10-17T12:10:00Z', can_surrender: false,
  } }, global })
  expect(wrapper.get('.arena-clock').text()).toContain('Время решения09:59')
  expect(wrapper.get('.surrender-button').text()).toBe('Сдаться через 00:01')
  expect(wrapper.get('.surrender-button').attributes('disabled')).toBeDefined()
  await vi.advanceTimersByTimeAsync(1000)
  expect(wrapper.get('.arena-clock strong').text()).toBe('10:00')
  expect(wrapper.get('.surrender-button').attributes('disabled')).toBeUndefined()
  await wrapper.get('.surrender-button').trigger('click')
  expect(wrapper.emitted('surrender')).toHaveLength(1)
  await wrapper.setProps({ canSubmit: false })
  expect(wrapper.get('.surrender-button').attributes('disabled')).toBeDefined()
  expect(wrapper.text()).not.toContain('До конца раунда')
})

it('unlocks surrender immediately when the opponent solves before ten minutes', async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-23T12:01:00Z'))
  wrapper = mount(StudentActiveRoomView, { props: { ...props, round: {
    is_active: true, started_at: '2026-10-23T12:00:00Z', server_now: '2026-10-23T12:01:00Z',
    surrender_available_at: '2026-10-23T12:10:00Z', can_surrender: false,
  }, participants: [{ student_id: 'me' }, { student_id: 'opponent' }] }, global })
  expect(wrapper.get('.surrender-button').attributes('disabled')).toBeDefined()
  await wrapper.setProps({ participants: [{ student_id: 'me' }, { student_id: 'opponent', accepted_at: '2026-10-23T12:00:59Z' }] })
  expect(wrapper.get('.surrender-button').text()).toBe('Сдаться')
  expect(wrapper.get('.surrender-button').attributes('disabled')).toBeUndefined()
  await wrapper.get('.surrender-button').trigger('click')
  expect(wrapper.emitted('surrender')).toHaveLength(1)
})

it('shows surrender and the solve bonus while keeping the editor available', async () => {
  wrapper = mount(StudentActiveRoomView, { props: { ...props, participants: [
    { student_id: 'me', name: 'Я' }, { student_id: 'other', name: 'Соперник', surrendered_at: '2026-10-17T12:10:00Z' },
  ], round: { surrender_solve_bonus: 20 } }, global })
  expect(wrapper.get('.round-notice').text()).toContain('+20 очков')
  expect(wrapper.get('.round-notice').text()).toContain('Время не ограничено')
  expect(wrapper.findAll('.arena-player')[1].text()).toContain('Сдался')
  expect(wrapper.find('.arena-solution').exists()).toBe(true)
  await wrapper.findAll('button').find(button => button.text() === 'На весь экран').trigger('click')
  expect(wrapper.get('.round-notice').exists()).toBe(true)
})
