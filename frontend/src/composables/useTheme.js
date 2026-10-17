import { computed, onUnmounted, ref, watch } from 'vue'

export const THEME_KEY = 'codebattle:theme'
export const THEME_CONTEXT = Symbol('codebattle-theme')
const normalize = value => ['light', 'dark', 'system'].includes(value) ? value : 'system'

function savedPreference() {
  try { return normalize(localStorage.getItem(THEME_KEY)) } catch { return 'system' }
}
function mediaQuery() {
  return typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null
}
function apply(theme) {
  document.documentElement.dataset.theme = theme
  document.documentElement.dataset.bsTheme = theme
  document.documentElement.style.colorScheme = theme
}
export function initializeTheme() {
  const preference = savedPreference()
  apply(preference === 'system' ? (mediaQuery()?.matches ? 'dark' : 'light') : preference)
}

export function useTheme() {
  const preference = ref(savedPreference()), media = mediaQuery(), systemDark = ref(Boolean(media?.matches))
  const resolved = computed(() => preference.value === 'system' ? (systemDark.value ? 'dark' : 'light') : preference.value)
  const change = event => { systemDark.value = event.matches }
  const storage = event => {
    if (event.key === THEME_KEY || event.key === null) preference.value = normalize(event.newValue)
  }
  media?.addEventListener?.('change', change)
  window.addEventListener('storage', storage)
  watch(resolved, apply, { immediate: true })
  watch(preference, value => { try { localStorage.setItem(THEME_KEY, value) } catch {} })
  onUnmounted(() => {
    media?.removeEventListener?.('change', change)
    window.removeEventListener('storage', storage)
  })
  return { preference, resolved }
}
