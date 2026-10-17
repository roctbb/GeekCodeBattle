import { afterEach, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AppTopbar from './AppTopbar.vue'
let wrapper
const me = { id:'user', name:'Бородин Ростислав Алексеевич', avatar_url:'https://codingprojects.ru/avatar.jpg' }
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = '' })
it('keeps destinations in the profile menu and supports keyboard navigation and escape', async () => {
  wrapper = mount(AppTopbar, { props:{ me, isTeacher:true }, attachTo:document.body })
  expect(wrapper.find('.account-menu-panel').exists()).toBe(false)
  const trigger = wrapper.get('.account-trigger')
  await trigger.trigger('keydown', { key:'ArrowDown' })
  expect(document.activeElement.textContent).toBe('Батлы')
  await wrapper.get('.account-menu-panel').trigger('keydown', { key:'End' })
  expect(document.activeElement.textContent).toBe('Выйти')
  await wrapper.get('.account-menu-panel').trigger('keydown', { key:'Escape' })
  expect(wrapper.find('.account-menu-panel').exists()).toBe(false)
  expect(document.activeElement).toBe(trigger.element)
  await trigger.trigger('click')
  await wrapper.findAll('button').find(b => b.text() === 'Задачи').trigger('click')
  expect(wrapper.emitted('go-packages')).toHaveLength(1)
  expect(trigger.attributes('aria-expanded')).toBe('false')
})
it('uses the signed avatar URL and falls back to initials after an image error', async () => {
  wrapper = mount(AppTopbar, { props:{ me } })
  expect(wrapper.get('img').attributes()).toMatchObject({ src:me.avatar_url, referrerpolicy:'no-referrer', alt:'' })
  await wrapper.get('img').trigger('error')
  expect(wrapper.get('.account-avatar').text()).toBe('БР')
  await wrapper.setProps({ me:{ ...me, avatar_url:'https://codingprojects.ru/new.jpg' } })
  expect(wrapper.get('img').attributes('src')).toContain('new.jpg')
  await wrapper.setProps({ me:{ ...me, avatar_url:'javascript:alert(1)' } })
  expect(wrapper.find('img').exists()).toBe(false)
})
it('opens interface settings inside the same panel and closes on an outside click', async () => {
  wrapper = mount(AppTopbar, { props:{ me }, slots:{ preferences:'<p>Тема оформления</p>' }, attachTo:document.body })
  await wrapper.get('.account-trigger').trigger('click')
  await wrapper.findAll('button').find(b => b.text() === 'Настройки интерфейса').trigger('click')
  expect(wrapper.text()).toContain('Тема оформления')
  await wrapper.get('.settings-back').trigger('click')
  expect(document.activeElement.textContent).toContain('Настройки интерфейса')
  document.body.dispatchEvent(new Event('pointerdown', { bubbles:true }))
  await wrapper.vm.$nextTick()
  expect(wrapper.get('.account-trigger').attributes('aria-expanded')).toBe('false')
})
