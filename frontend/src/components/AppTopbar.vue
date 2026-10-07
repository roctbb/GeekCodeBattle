<template>
  <nav class="navbar app-topbar sticky-top" aria-label="Основная навигация">
    <div class="container topbar-layout">
      <a class="navbar-brand fw-semibold app-brand d-flex align-items-center gap-2" href="#" @click.prevent="$emit('go-battles')">
        <span class="brand-dot" aria-hidden="true"></span>
        <span>GeekCodeBattle</span>
      </a>
      <div v-if="me" class="topbar-links">
        <template v-if="isTeacher">
          <button type="button" class="btn btn-sm nav-link" :aria-current="teacherPage === 'battles' ? 'page' : null" @click="$emit('go-battles')">Сражения</button>
          <button type="button" class="btn btn-sm nav-link" :aria-current="teacherPage === 'tasks' ? 'page' : null" @click="$emit('go-packages')">Пакеты</button>
          <button type="button" class="btn btn-sm nav-link" :aria-current="teacherPage === 'play' && !resultsActive ? 'page' : null" @click="$emit('go-play')">Участие</button>
          <button type="button" class="btn btn-sm nav-link" :aria-current="resultsActive ? 'page' : null" @click="$emit('go-results')">Мои результаты</button>
        </template>
        <template v-else>
          <button type="button" class="btn btn-sm nav-link" :aria-current="!resultsActive ? 'page' : null" @click="$emit('go-battles')">Батл</button>
          <button type="button" class="btn btn-sm nav-link" :aria-current="resultsActive ? 'page' : null" @click="$emit('go-results')">Результаты</button>
        </template>
      </div>
      <div v-if="me" class="topbar-account">
        <span class="topbar-name text-muted" :title="me.name">{{ me.name }}</span>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="$emit('logout')"><AppIcon name="leave" />Выйти</button>
      </div>
    </div>
  </nav>
</template>

<script setup>
import AppIcon from './AppIcon.vue'
defineProps({
  me: { type: Object, default: null },
  isTeacher: { type: Boolean, default: false },
  resultsActive: Boolean,
  teacherPage: { type: String, default: 'battles' }
})

defineEmits(['go-battles', 'go-packages', 'go-play', 'go-results', 'logout'])
</script>

<style scoped>
.app-topbar > .topbar-layout { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 1.5rem; max-width: 1200px; min-height: 48px; }
.app-brand { margin: 0; font-size: 1.125rem; letter-spacing: -.025em; }
.topbar-links, .topbar-account { display: flex; align-items: center; gap: .5rem; }
.topbar-links { justify-content: flex-end; min-width: 0; }
.topbar-links .nav-link { padding: .5rem .75rem; color: var(--app-muted); white-space: nowrap; border: 0; }
.topbar-links .nav-link:hover { background: var(--app-bg); color: var(--app-ink); }
.topbar-links .nav-link[aria-current=page] { color: var(--app-brand); background: #eef2fc; }
.topbar-account { gap: 1rem; }
.topbar-name { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .8125rem; }
@media (max-width: 1199px) { .topbar-name { display: none; } .app-topbar > .topbar-layout { gap: 1rem; } }
@media (max-width: 767px) {
  .app-topbar > .topbar-layout { grid-template-columns: 1fr auto; gap: .75rem; padding: .25rem 1rem; }
  .topbar-links { grid-row: 2; grid-column: 1 / -1; justify-content: stretch; gap: .25rem; }
  .topbar-links .nav-link { flex: 1; padding: .5rem; font-size: .75rem; }
  .topbar-account { grid-column: 2; grid-row: 1; }
}
@media (max-width: 359px) {
  .topbar-links { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
