<template>
  <section v-if="selectedBattle" class="card teacher-battle">
    <div class="card-body">
      <button class="back-link" @click="$emit('back')"><AppIcon name="arrow-left" />Все батлы</button>
      <header class="teacher-battle-heading">
        <div>
          <h1 class="page-title">{{ selectedBattle.title }}</h1>
          <div class="battle-context">
            <span class="status-chip" :class="`status-${status}`">{{ battleStatus(status) }}</span>
            <button v-if="selectedBattle.invite_code && status !== 'finished'" class="invite-copy" @click="copyInvite" :aria-label="`Скопировать код ${selectedBattle.invite_code}`">
              <span class="text-muted">Код входа</span><strong class="code-like">{{ selectedBattle.invite_code }}</strong><AppIcon :name="copied ? 'check' : 'copy'" />
            </button>
            <span v-if="copyError" class="text-danger small" role="alert">{{ copyError }}</span>
            <span class="visually-hidden" role="status">{{ copied ? 'Код скопирован' : '' }}</span>
          </div>
        </div>
        <button v-if="mainAction" class="btn action-btn main-battle-action" :class="status === 'running' ? 'btn-outline-secondary' : 'btn-primary'" @click="primaryAction">
          <AppIcon :name="mainAction.icon" />{{ mainAction.label }}
        </button>
      </header>

      <nav class="staff-tabs" role="tablist" aria-label="Разделы батла">
        <button v-for="item in sections" :key="item.id" :id="`battle-tab-${item.id}`" role="tab" :aria-selected="tab === item.id"
          :aria-controls="`battle-panel-${item.id}`" :tabindex="tab === item.id ? 0 : -1"
          @click="tab = item.id" @keydown="navigateTabs($event, item.id)">{{ item.label }}</button>
      </nav>
      <div :id="`battle-panel-${tab}`" role="tabpanel" :aria-labelledby="`battle-tab-${tab}`" class="staff-tab-panel">
        <template v-if="tab === 'overview'">
          <div v-if="needsSetup && ['draft','lobby_open','stopped'].includes(status)" class="battle-preparation">
            <div><h2 class="h6 mb-1">Подготовка к старту</h2><p class="text-muted small mb-0">Укажите код входа и подключите задачи.</p></div>
            <button :class="{ done: selectedBattle.invite_code }" @click="tab = 'settings'"><AppIcon :name="selectedBattle.invite_code ? 'check' : 'plus'" />Код входа</button>
            <button :class="{ done: battleTasks.length }" @click="tab = 'settings'"><AppIcon :name="battleTasks.length ? 'check' : 'plus'" />{{ battleTasks.length ? `Задач: ${battleTasks.length}` : 'Подключить задачи' }}</button>
          </div>
          <dl class="battle-pulse" aria-label="Состояние батла">
            <div><dt>Участников</dt><dd>{{ members.length }}</dd></div>
            <div><dt>Решают</dt><dd>{{ members.filter(p => p.status === 'fighting').length }}</dd></div>
            <div><dt>Готовы к раунду</dt><dd>{{ members.filter(p => p.status === 'ready').length }}</dd></div>
            <div><dt>Задач</dt><dd>{{ battleTasks.length }}</dd></div>
          </dl>
          <div class="staff-section-heading">
            <h2 class="h6 mb-0">Участники сейчас</h2>
            <label v-if="members.length" class="staff-search"><span class="visually-hidden">Найти участника</span><input v-model="memberQuery" class="form-control" type="search" placeholder="Найти участника" /></label>
          </div>
          <div v-if="visibleMembers.length" class="table-responsive staff-table-wrap">
            <table class="table staff-table mb-0">
              <thead><tr><th>Участник</th><th>Состояние</th><th class="text-end">Очки</th></tr></thead>
              <tbody><tr v-for="person in visibleMembers.slice(0,12)" :key="person.user_id">
                <th><button class="student-link" @click="$emit('open-student', { studentId: person.user_id })"><span class="presence-dot" :class="person.is_online ? 'online' : 'offline'" :aria-label="person.is_online ? 'В сети' : 'Не в сети'"></span>{{ person.name }}</button></th>
                <td><span class="member-state" :class="person.status">{{ memberStatus(person.status) }}</span></td><td class="text-end tabular">{{ person.points }}</td>
              </tr></tbody>
            </table>
          </div>
          <p v-else class="empty-state">{{ memberQuery ? 'Участник не найден.' : 'Ученики появятся здесь после входа по коду.' }}</p>
          <div v-if="members.length" class="staff-table-footer"><small class="text-muted">{{ visibleMembers.length > 12 ? `Показаны 12 из ${visibleMembers.length}` : 'Состояние обновляется автоматически' }}</small><button class="text-action" @click="tab = 'students'">Полная статистика<AppIcon name="arrow-right" /></button></div>
        </template>

        <TeacherBattleStatistics v-else-if="tab === 'students'" :battle-id="selectedBattle.id" :refresh-key="refreshKey" @open-student="$emit('open-student', $event)" />

        <template v-else-if="tab === 'rooms'">
          <div class="staff-section-heading">
            <div class="staff-segments" role="group" aria-label="Состояние комнат"><button :aria-pressed="roomFilter === 'current'" @click="roomFilter = 'current'">Текущие</button><button :aria-pressed="roomFilter === 'completed'" @click="roomFilter = 'completed'">Завершённые</button></div>
            <label class="staff-search"><span class="visually-hidden">Найти комнату</span><input v-model="roomQuery" class="form-control" type="search" placeholder="Участник или задача" /></label>
          </div>
          <div v-if="filteredRooms.length" class="table-responsive staff-table-wrap">
            <table class="table staff-table rooms-table mb-0"><thead><tr><th>Участники и задача</th><th>Начало</th><th>Состояние</th><th><span class="visually-hidden">Действия</span></th></tr></thead>
              <tbody><tr v-for="room in filteredRooms.slice(0, roomLimit)" :key="room.room_id">
                <td><strong>{{ (room.latest_match?.participants || []).map(p => p.student?.name || p.name).filter(Boolean).join(' · ') || 'Без участников' }}</strong><small>{{ room.latest_match?.task?.title || 'Задача не назначена' }}</small></td>
                <td class="room-date">{{ formatDate(room.created_at) }}</td>
                <td><span class="member-state" :class="room.status === 'active' ? 'fighting' : ''">{{ roomStatus(room.status) }}</span></td>
                <td><button class="btn btn-sm btn-outline-secondary" @click="$emit('open-room-log', room.room_id)">Журнал<AppIcon name="chevron-right" /></button></td>
              </tr></tbody>
            </table>
          </div>
          <p v-else class="empty-state">{{ roomQuery ? 'Комнаты не найдены.' : roomFilter === 'current' ? 'Сейчас никто не решает. Новые комнаты появятся после подбора участников.' : 'Завершённых комнат пока нет.' }}</p>
          <button v-if="filteredRooms.length > roomLimit" class="btn btn-outline-secondary mt-3" @click="roomLimit += 20">Показать ещё {{ Math.min(20, filteredRooms.length - roomLimit) }}</button>
        </template>

        <template v-else>
          <BattleInviteSettings :battle-id="selectedBattle.id" :code="selectedBattle.invite_code" :disabled="status === 'finished'" @saved="$emit('invite-saved', $event)" />
          <section class="battle-package-settings">
            <div class="staff-section-heading"><div><h2 class="h6 mb-1">Задачи батла</h2><p class="text-muted small mb-0">Подключено пакетов: {{ battlePackageIds.length }} · Задач: {{ battleTasks.length }}</p></div><button class="text-action" @click="$emit('open-packages')">Библиотека<AppIcon name="arrow-right" /></button></div>
            <label v-if="taskPackages.length > 6" class="staff-search mb-3"><span class="visually-hidden">Найти пакет</span><input v-model="packageQuery" class="form-control" type="search" placeholder="Найти пакет" /></label>
            <div v-if="filteredPackages.length" class="package-options">
              <label v-for="pack in filteredPackages" :key="pack.id" class="package-option">
                <input type="checkbox" :checked="battlePackageIds.includes(pack.id)" :disabled="status === 'finished'" @change="togglePackage($event, pack.id)" />
                <span><strong>{{ pack.name }}</strong><small>{{ pack.task_count ?? 0 }} задач</small></span>
              </label>
            </div>
            <p v-else class="empty-state">{{ packageQuery ? 'Пакеты не найдены.' : 'Создайте пакет в библиотеке и вернитесь сюда.' }}</p>
          </section>
          <details class="battle-completion"><summary>{{ status === 'finished' ? 'Архив и хранение' : 'Завершение батла' }}</summary>
            <p class="text-muted small mt-3">{{ status === 'finished' ? 'История начислений нужна для пересчёта рейтинга. Удалить можно только батл без начисленных очков.' : 'Завершение закрывает батл окончательно. Чтобы продолжить позже, используйте паузу в шапке.' }}</p>
            <button v-if="status !== 'finished'" class="btn btn-outline-danger" @click="$emit('finish')"><AppIcon name="stop" />Завершить батл</button>
            <button v-if="canDelete" class="btn btn-outline-danger" @click="$emit('delete-battle')"><AppIcon name="trash" />Удалить батл</button>
          </details>
        </template>
      </div>
    </div>
  </section>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from '../AppIcon.vue'
import { battleStatus } from '../../labels'
import BattleInviteSettings from './BattleInviteSettings.vue'
import TeacherBattleStatistics from './TeacherBattleStatistics.vue'
const props = defineProps({
  section: { type: String, default: 'overview' }, refreshKey: Number,
  selectedBattle: { type: Object, default: null },
  battleTasks: { type: Array, default: () => [] }, taskPackages: { type: Array, default: () => [] },
  battlePackageIds: { type: Array, default: () => [] }, queueEntries: { type: Array, default: () => [] },
  leaderboardParticipants: { type: Array, default: () => [] }, battleLogs: { type: Array, default: () => [] }, canDelete: Boolean,
})
const emit = defineEmits(['update:section', 'invite-saved', 'open-student', 'back', 'open-lobby', 'start', 'stop', 'finish', 'delete-battle', 'add-package', 'remove-package', 'open-room-log', 'open-packages'])
const sections = [{ id:'overview', label:'Обзор' }, { id:'students', label:'Ученики' }, { id:'rooms', label:'Комнаты' }, { id:'settings', label:'Настройки' }]
const tab = computed({ get: () => sections.some(s => s.id === props.section) ? props.section : 'overview', set: value => emit('update:section', value) })
const status = computed(() => props.selectedBattle?.status || 'draft')
const needsSetup = computed(() => !props.selectedBattle?.invite_code || !props.battleTasks.length)
const mainAction = computed(() => status.value === 'finished' ? null : status.value === 'running' ? { label:'Приостановить', icon:'pause', event:'stop' } : needsSetup.value ? { label:'Настроить батл', icon:'settings' } : status.value === 'draft' ? { label:'Открыть лобби', icon:'door', event:'open-lobby' } : { label:status.value === 'stopped' ? 'Продолжить' : 'Запустить', icon:'play', event:'start' })
function primaryAction() { if (mainAction.value.event) emit(mainAction.value.event); else tab.value = 'settings' }
function navigateTabs(event, id) {
  const index = sections.findIndex(s => s.id === id)
  const next = event.key === 'ArrowRight' ? (index + 1) % sections.length : event.key === 'ArrowLeft' ? (index + sections.length - 1) % sections.length : event.key === 'Home' ? 0 : event.key === 'End' ? sections.length - 1 : -1
  if (next < 0) return
  event.preventDefault(); tab.value = sections[next].id
  event.currentTarget.parentElement.querySelectorAll('[role=tab]')[next]?.focus()
}
const copied = ref(false), copyError = ref(''), memberQuery = ref(''), roomQuery = ref(''), packageQuery = ref(''), roomFilter = ref('current'), roomLimit = ref(20)
watch(() => props.selectedBattle?.id, () => { copied.value = false; copyError.value = ''; memberQuery.value = ''; roomQuery.value = ''; packageQuery.value = ''; roomFilter.value = 'current' })
watch([roomQuery, roomFilter], () => { roomLimit.value = 20 })
async function copyInvite() { try { await navigator.clipboard.writeText(props.selectedBattle.invite_code); copied.value = true; copyError.value = '' } catch { copyError.value = 'Не удалось скопировать код. Он доступен в настройках.' } }
function togglePackage(event, id) { const checked = event.target.checked; event.target.checked = props.battlePackageIds.includes(id); emit(checked ? 'add-package' : 'remove-package', id) }
const members = computed(() => {
  const queue = new Map(props.queueEntries.map(p => [p.user_id, p])), board = new Map(props.leaderboardParticipants.map(p => [p.user_id, p]))
  return [...new Set([...queue.keys(), ...board.keys()])].map(id => {
    const q = queue.get(id), b = board.get(id)
    return { user_id:id, name:q?.name || b?.name || 'Участник', status:q?.status || 'away', is_online:q?.is_online ?? b?.is_online ?? false, points:Number(b?.battle_points ?? b?.season_points ?? 0) }
  }).sort((a,b) => (({fighting:0,ready:1,not_ready:2,away:3})[a.status] ?? 2) - (({fighting:0,ready:1,not_ready:2,away:3})[b.status] ?? 2) || a.name.localeCompare(b.name, 'ru'))
})
const visibleMembers = computed(() => members.value.filter(p => p.name.toLocaleLowerCase().includes(memberQuery.value.trim().toLocaleLowerCase())))
const filteredPackages = computed(() => props.taskPackages.filter(p => p.name.toLocaleLowerCase().includes(packageQuery.value.trim().toLocaleLowerCase())))
const filteredRooms = computed(() => props.battleLogs.filter(room => {
  const completed = ['finished','cancelled'].includes(room.status)
  const text = [room.latest_match?.task?.title, ...(room.latest_match?.participants || []).map(p => p.student?.name || p.name)].join(' ').toLocaleLowerCase()
  return (roomFilter.value === 'completed' ? completed : !completed) && text.includes(roomQuery.value.trim().toLocaleLowerCase())
}))
const memberStatus = value => ({ fighting:'Решает', ready:'Готов', not_ready:'Не готов', away:'Не в лобби' })[value] || 'Ожидает'
const roomStatus = value => ({ active:'Идёт решение', finished:'Завершена', cancelled:'Отменена', waiting_ready:'Ожидает старта' })[value] || 'Ожидает'
const formatDate = value => value ? new Date(value).toLocaleString('ru-RU', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' }) : '—'
</script>
<style scoped>
.back-link { display:inline-flex; align-items:center; gap:8px; border:0; background:none; color:var(--app-muted); padding:0; margin-bottom:20px; font-size:12px; }
.teacher-battle-heading { display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:20px; margin-bottom:28px; }
.teacher-battle-heading > div { min-width:0; flex:1 1 320px; }
.page-title { font-size:clamp(22px,3vw,30px); overflow-wrap:anywhere; margin-bottom:12px; }
.battle-context { display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.invite-copy { display:inline-flex; align-items:center; gap:8px; border:0; padding:0; background:none; font-size:12px; color:var(--app-brand); }
.invite-copy .app-icon { font-size:12px; }
.main-battle-action { flex:none; }
.staff-tab-panel { padding-top:24px; min-height:260px; }
.battle-pulse { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:20px; padding-bottom:24px; margin:0 0 28px; border-bottom:1px solid var(--app-border); }
.battle-pulse dt { font-size:12px; font-weight:400; color:var(--app-muted); }
.battle-pulse dd { font-size:26px; font-weight:700; margin:6px 0 0; font-variant-numeric:tabular-nums; }
.battle-preparation { display:flex; align-items:center; flex-wrap:wrap; gap:16px; background:var(--app-bg-soft); border-radius:8px; padding:20px; margin-bottom:24px; }
.battle-preparation > div { flex:1 1 200px; }
.battle-preparation button { display:inline-flex; align-items:center; gap:8px; padding:8px 12px; border:1px solid var(--app-outline); border-radius:6px; color:var(--app-ink); background:var(--app-card); font-size:12px; }
.battle-preparation .done { color:var(--app-success); border-color:var(--app-success-border); }
.staff-table .student-link { display:inline-flex; align-items:center; gap:10px; font-size:13px; }
.staff-table .presence-dot { width:6px; height:6px; flex:none; }
.staff-table-footer { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; padding-top:16px; font-size:12px; }
.rooms-table td:first-child { min-width:220px; white-space:normal; }
.rooms-table td:first-child strong { font-weight:500; overflow-wrap:anywhere; }
.rooms-table small { display:block; color:var(--app-muted); margin-top:5px; }
.room-date { font-size:12px; color:var(--app-muted); white-space:nowrap; }
.battle-package-settings { padding-top:20px; border-top:1px solid var(--app-border); }
.package-options { border:1px solid var(--app-border); border-radius:8px; }
.package-option { display:flex; align-items:center; gap:14px; padding:16px; cursor:pointer; }
.package-option + .package-option { border-top:1px solid var(--app-border); }
.package-option input { width:18px; height:18px; flex:none; accent-color:var(--app-brand); }
.package-option span { display:grid; gap:4px; min-width:0; overflow-wrap:anywhere; }
.package-option strong { font-size:13px; font-weight:500; }
.package-option small { color:var(--app-muted); font-size:11px; }
.battle-completion { border-top:1px solid var(--app-border); margin-top:32px; padding-top:20px; font-size:13px; }
.battle-completion summary { cursor:pointer; color:var(--app-muted); }
@media(max-width:600px) { .battle-pulse { grid-template-columns:repeat(2,minmax(0,1fr)); gap:20px; }.main-battle-action { width:100%; }.teacher-battle-heading { margin-bottom:20px; }.battle-preparation { padding:16px; } }
</style>
