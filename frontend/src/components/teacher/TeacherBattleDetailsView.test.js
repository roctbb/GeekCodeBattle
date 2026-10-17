import { afterEach, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TeacherBattleDetailsView from './TeacherBattleDetailsView.vue'
let wrapper
const battle = { id:'battle', title:'Алгоритмы', status:'running', invite_code:'CPP8' }
const global = { stubs:{ TeacherBattleStatistics:true, BattleInviteSettings:true } }
afterEach(() => wrapper?.unmount())
it('shows one main action and merges the live queue with admitted participants', async () => {
  wrapper = mount(TeacherBattleDetailsView, { global, props:{ selectedBattle:battle, battleTasks:[{ id:'task' }], queueEntries:[{ user_id:'one', name:'Анна', status:'fighting', is_online:true }], leaderboardParticipants:[{ user_id:'one', name:'Анна', battle_points:140 }, { user_id:'two', name:'Борис', battle_points:30 }] } })
  expect(wrapper.findAll('tbody tr')).toHaveLength(2)
  expect(wrapper.text()).toContain('Борис')
  expect(wrapper.text()).toContain('140')
  expect(wrapper.find('battle-invite-settings-stub').exists()).toBe(false)
  expect(wrapper.text()).not.toContain('Завершить батл')
  await wrapper.get('.main-battle-action').trigger('click')
  expect(wrapper.emitted('stop')).toHaveLength(1)
  await wrapper.get('#battle-tab-settings').trigger('click')
  expect(wrapper.emitted('update:section').at(-1)).toEqual(['settings'])
  await wrapper.setProps({ section:'settings' })
  expect(wrapper.find('battle-invite-settings-stub').exists()).toBe(true)
})
it('filters rooms by state and participant, preserving journal access', async () => {
  const rooms = [{ room_id:'active', status:'active', latest_match:{ task:{ title:'Сумма' }, participants:[{ student:{ name:'Анна' } }] } }, { room_id:'past', status:'finished', latest_match:{ task:{ title:'Цикл' }, participants:[{ student:{ name:'Борис' } }] } }]
  wrapper = mount(TeacherBattleDetailsView, { global, props:{ selectedBattle:battle, section:'rooms', battleLogs:rooms } })
  expect(wrapper.text()).toContain('Анна')
  expect(wrapper.text()).not.toContain('Борис')
  await wrapper.findAll('button').find(b => b.text() === 'Завершённые').trigger('click')
  await wrapper.get('[aria-label="Разделы батла"] button').trigger('keydown', { key:'End' })
  expect(wrapper.emitted('update:section').at(-1)).toEqual(['settings'])
  await wrapper.get('.rooms-table button').trigger('click')
  expect(wrapper.emitted('open-room-log').at(-1)).toEqual(['past'])
  await wrapper.get('[placeholder="Участник или задача"]').setValue('Анна')
  expect(wrapper.find('.rooms-table').exists()).toBe(false)
})
