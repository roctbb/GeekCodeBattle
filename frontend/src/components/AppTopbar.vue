<template>
  <nav class="navbar app-topbar sticky-top" aria-label="Основная навигация">
    <div class="container topbar-layout">
      <a class="navbar-brand fw-semibold app-brand d-flex align-items-center gap-2" href="#" @click.prevent="navigate('go-battles')">
        <CodeBattleMark /><span>Code<span class="brand-gold">Battle</span></span>
      </a>
      <div v-if="me" ref="account" class="account-menu" @keydown="onKeydown" @focusout="onFocusOut">
        <button ref="trigger" type="button" class="account-trigger" :aria-label="`Меню пользователя: ${displayName}`"
          :aria-expanded="open" aria-haspopup="dialog" aria-controls="account-panel" :title="displayName" @click="toggle"
          @keydown.down.prevent="show(0)" @keydown.up.prevent="show(-1)">
          <span class="account-avatar" aria-hidden="true">
            <img v-if="avatarUrl && !avatarFailed" :src="avatarUrl" alt="" width="32" height="32" decoding="async" referrerpolicy="no-referrer" @error="avatarFailed = true" />
            <span v-else>{{ initials }}</span>
          </span>
          <span class="topbar-name">{{ displayName }}</span><AppIcon name="chevron-down" class="account-chevron" />
        </button>
        <div v-if="open" id="account-panel" ref="panel" class="account-menu-panel" role="dialog" :aria-label="settingsOpen ? 'Настройки интерфейса' : 'Меню пользователя'">
          <template v-if="!settingsOpen">
            <div class="account-menu-heading"><strong>{{ displayName }}</strong><small>{{ isTeacher ? 'Преподаватель' : 'Участник' }}</small></div>
            <button type="button" :aria-current="isTeacher ? (teacherPage === 'battles' && !resultsActive ? 'page' : null) : (!resultsActive ? 'page' : null)" @click="navigate('go-battles')"><AppIcon name="bolt" />{{ isTeacher ? 'Батлы' : 'Мой батл' }}</button>
            <button v-if="isTeacher" type="button" :aria-current="teacherPage === 'tasks' && !resultsActive ? 'page' : null" @click="navigate('go-packages')"><AppIcon name="file" />Задачи</button>
            <button v-if="isTeacher" type="button" :aria-current="teacherPage === 'play' && !resultsActive ? 'page' : null" @click="navigate('go-play')"><AppIcon name="play" />Участвовать в батле</button>
            <button type="button" :aria-current="resultsActive ? 'page' : null" @click="navigate('go-results')"><AppIcon name="history" />Мои результаты</button>
            <div class="account-divider" />
            <button type="button" @click="showSettings"><AppIcon name="settings" />Настройки интерфейса</button>
            <button type="button" @click="navigate('logout')"><AppIcon name="leave" />Выйти</button>
          </template>
          <template v-else>
            <button ref="settingsBack" type="button" class="settings-back" @click="showNavigation"><AppIcon name="arrow-left" />Назад в меню</button>
            <slot name="preferences" :embedded="true" />
          </template>
        </div>
      </div>
      <slot v-else name="preferences" :embedded="false" />
    </div>
  </nav>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import CodeBattleMark from './CodeBattleMark.vue'
const props = defineProps({
  me: { type: Object, default: null }, isTeacher: Boolean, resultsActive: Boolean,
  teacherPage: { type: String, default: 'battles' }, navigationKey: String,
})
const emit = defineEmits(['go-battles', 'go-packages', 'go-play', 'go-results', 'logout'])
const account = ref(), trigger = ref(), panel = ref(), settingsBack = ref()
const open = ref(false), settingsOpen = ref(false), avatarFailed = ref(false)
const displayName = computed(() => props.me?.name?.trim() || 'Пользователь')
const initials = computed(() => displayName.value.split(/\s+/).slice(0, 2).map(part => Array.from(part)[0]).join('').toLocaleUpperCase('ru-RU'))
const avatarUrl = computed(() => {
  if (typeof props.me?.avatar_url !== 'string') return ''
  try { const url = new URL(props.me.avatar_url); return ['https:', 'http:'].includes(url.protocol) ? url.href : '' } catch { return '' }
})
const items = () => [...(panel.value?.querySelectorAll('button:not(:disabled)') || [])]
async function show(index = 0) {
  settingsOpen.value = false
  open.value = true
  await nextTick()
  items().at(index)?.focus()
}
function close(restoreFocus = false) { open.value = false; settingsOpen.value = false; if (restoreFocus) trigger.value?.focus() }
function toggle() { if (open.value) close(); else show() }
function navigate(event) { close(); emit(event) }
async function showSettings() { settingsOpen.value = true; await nextTick(); settingsBack.value?.focus() }
async function showNavigation() { await show(); items().find(item => item.textContent.includes('Настройки интерфейса'))?.focus() }
function outside(event) { if (!account.value?.contains(event.target)) close() }
function onFocusOut(event) { if (event.relatedTarget && !account.value?.contains(event.relatedTarget)) close() }
function onKeydown(event) {
  if (!open.value) return
  if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(true); return }
  if (settingsOpen.value || !panel.value?.contains(event.target)) return
  const available = items(), index = available.indexOf(document.activeElement)
  const next = { ArrowDown: (index + 1) % available.length, ArrowUp: (index - 1 + available.length) % available.length, Home: 0, End: available.length - 1 }[event.key]
  if (next !== undefined) { event.preventDefault(); available[next]?.focus() }
}
watch(avatarUrl, () => { avatarFailed.value = false })
watch(() => [props.navigationKey, props.teacherPage, props.resultsActive, props.me?.id], () => close())
onMounted(() => document.addEventListener('pointerdown', outside))
onUnmounted(() => document.removeEventListener('pointerdown', outside))
</script>

<style scoped>
.app-topbar > .topbar-layout { display:flex; justify-content:space-between; align-items:center; gap:1.5rem; max-width:1280px; min-height:48px; }
.app-brand { margin:0; font-size:1.125rem; letter-spacing:-.025em; flex-shrink:0; }
.account-menu { position:relative; min-width:0; }
.account-trigger { display:flex; align-items:center; gap:10px; min-height:44px; padding:5px 8px; border:1px solid transparent; border-radius:8px; background:transparent; color:var(--app-ink); }
.account-trigger:hover, .account-trigger[aria-expanded='true'] { background:var(--app-hover); border-color:var(--app-border); }
.account-avatar { display:flex; align-items:center; justify-content:center; flex-shrink:0; width:32px; height:32px; border-radius:50%; background:var(--app-brand-soft); color:var(--app-brand); font-size:11px; font-weight:700; }
.account-avatar img { display:block; width:100%; height:100%; object-fit:cover; border-radius:inherit; }
.topbar-name { max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; }
.account-chevron { width:10px; color:var(--app-muted); transition:transform 120ms ease; }
.account-trigger[aria-expanded='true'] .account-chevron { transform:rotate(180deg); }
.account-menu-panel { position:absolute; z-index:1060; top:calc(100% + 12px); right:0; width:min(300px,calc(100vw - 24px)); max-height:calc(100dvh - 100px); overflow-y:auto; padding:8px; background:var(--app-card); border:1px solid var(--app-border); border-radius:10px; box-shadow:var(--app-popover-shadow); }
.account-menu-heading { display:grid; gap:4px; padding:10px 12px 14px; border-bottom:1px solid var(--app-border); margin-bottom:6px; overflow-wrap:anywhere; font-size:13px; }
.account-menu-heading small { color:var(--app-muted); }
.account-menu-panel button { display:flex; align-items:center; gap:10px; width:100%; min-height:44px; padding:11px 12px; border:0; border-radius:5px; background:transparent; color:var(--app-ink); text-align:left; font-size:13px; }
.account-menu-panel button:hover, .account-menu-panel button[aria-current='page'] { background:var(--app-brand-soft); color:var(--app-brand); }
.account-menu-panel button > .app-icon { width:16px; color:var(--app-muted); }
.account-divider { border-top:1px solid var(--app-border); margin:6px 12px; }
.account-menu-panel .settings-back { margin-bottom:8px; color:var(--app-muted); }
@media(max-width:575px) { .topbar-name { display:none; } .app-topbar > .topbar-layout { gap:12px; } }
</style>
