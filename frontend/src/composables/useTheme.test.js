import { afterEach, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { initializeTheme, THEME_KEY, useTheme } from './useTheme'
let wrapper, theme
function setup(dark = false) {
  const media = { matches:dark, addEventListener:vi.fn(), removeEventListener:vi.fn() }
  vi.stubGlobal('matchMedia', () => media)
  wrapper = mount({ setup() { theme = useTheme(); return {} }, template:'<div />' })
  return media
}
afterEach(() => { wrapper?.unmount(); wrapper = null; localStorage.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
it('follows the system until a specific theme is chosen, and saves the choice', async () => {
  const media = setup(true)
  expect(document.documentElement.dataset.theme).toBe('dark')
  const change = media.addEventListener.mock.calls[0][1]
  change({ matches:false }); await nextTick()
  expect(document.documentElement.dataset.bsTheme).toBe('light')
  theme.preference.value = 'dark'; await nextTick()
  expect(localStorage.getItem(THEME_KEY)).toBe('dark')
  change({ matches:true }); change({ matches:false }); await nextTick()
  expect(theme.resolved.value).toBe('dark')
  wrapper.unmount(); wrapper = null
  expect(media.removeEventListener).toHaveBeenCalledWith('change', change)
})
it('restores preferences and synchronizes changes from another tab', async () => {
  localStorage.setItem(THEME_KEY, 'dark'); setup(false)
  expect(theme.resolved.value).toBe('dark')
  window.dispatchEvent(new StorageEvent('storage', { key:THEME_KEY, newValue:'light' })); await nextTick()
  expect(document.documentElement.dataset.theme).toBe('light')
  window.dispatchEvent(new StorageEvent('storage', { key:THEME_KEY, newValue:'broken' })); await nextTick()
  expect(theme.preference.value).toBe('system')
})
it('can initialize and change theme when storage is unavailable', async () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked') })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked') })
  initializeTheme(); setup()
  theme.preference.value = 'dark'; await nextTick()
  expect(document.documentElement.style.colorScheme).toBe('dark')
})
