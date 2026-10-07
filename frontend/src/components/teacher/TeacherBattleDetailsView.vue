<template>
  <section class="battle-detail-shell card" v-if="selectedBattle">
    <div class="card-body">
      <header class="battle-hero">
        <div class="battle-heading">
          <div>
            <p class="hero-eyebrow">{{ status === 'finished' ? 'Результаты батла' : 'Управление батлом' }}</p>
            <h2 class="page-title">{{ selectedBattle.title }}</h2>
            <p class="text-muted mb-0 d-flex flex-wrap align-items-center gap-2">
              <span class="status-chip" :class="`status-${selectedBattle.status}`">{{ battleStatus(selectedBattle.status) }}</span>
              <span v-if="selectedBattle.invite_code && status !== 'finished'">Инвайт: <strong class="code-like">{{ selectedBattle.invite_code }}</strong></span>
            </p>
          </div>
          <button class="btn btn-outline-secondary action-btn battle-back" @click="$emit('back')">
            <AppIcon name="arrow-left" />
            <span>К списку</span>
          </button>
        </div>
      <div v-if="status !== 'finished'" class="d-flex flex-wrap gap-2 action-ribbon">
        <button
          v-if="showOpenLobby"
          class="btn btn-outline-primary action-btn"
          :disabled="!selectedBattle.invite_code"
          title="Открыть лобби"
          @click="$emit('open-lobby')"
        >
          <AppIcon name="door" />
          <span>Открыть лобби</span>
        </button>
        <button
          v-if="showStart"
          class="btn btn-primary action-btn"
          :disabled="!selectedBattle.invite_code || !battleTasks.length"
          title="Запустить"
          @click="$emit('start')"
        >
          <AppIcon name="play" />
          <span>Запустить</span>
        </button>
        <button
          v-if="showStop"
          class="btn btn-outline-warning action-btn"
          title="Остановить"
          @click="$emit('stop')"
        >
          <AppIcon name="pause" />
          <span>Остановить</span>
        </button>
        <button
          v-if="showFinish"
          class="btn btn-outline-danger action-btn"
          title="Завершить"
          @click="$emit('finish')"
        >
          <AppIcon name="stop" />
          <span>Завершить</span>
        </button>
      </div>
      </header>

      <details v-if="status !== 'finished'" class="battle-settings" :open="status === 'draft' || !selectedBattle.invite_code"><summary><AppIcon name="chevron-down" />Инвайт и пакеты задач</summary>
        <BattleInviteSettings :battle-id="selectedBattle.id" :code="selectedBattle.invite_code" @saved="$emit('invite-saved', $event)" />
        <div class="package-heading">
          <h3 class="h6 mb-0">Пакеты задач</h3>
          <small class="text-muted">Отмеченные пакеты участвуют в жеребьёвке раундов</small>
        </div>
        <div class="package-grid" v-if="taskPackages.length">
          <article class="package-card" v-for="p in taskPackages" :key="`battle-package-${p.id}`">
            <div>
              <strong class="d-block mb-1">{{ p.name }}</strong>
              <small class="text-muted">{{ p.task_count ?? 0 }} задач</small>
            </div>
            <div class="d-flex align-items-center gap-2">
              <span class="badge" :class="battlePackageIds.includes(p.id) ? 'text-bg-success' : 'text-bg-light border text-dark'">
                {{ battlePackageIds.includes(p.id) ? 'Подключен' : 'Не подключен' }}
              </span>
            <button
              v-if="!battlePackageIds.includes(p.id)"
              class="btn btn-sm btn-outline-primary action-btn action-btn-sm"
              title="Добавить пакет"
              @click="$emit('add-package', p.id)"
            >
              <AppIcon name="plus" />
              <span>Добавить</span>
            </button>
            <button
              v-else
              class="btn btn-sm btn-outline-danger action-btn action-btn-sm"
              title="Убрать пакет"
              @click="$emit('remove-package', p.id)"
            >
              <AppIcon name="minus" />
              <span>Убрать</span>
            </button>
            </div>
          </article>
        </div>
        <div class="empty-state" v-else>
          Нет доступных пакетов. Добавьте пакет в разделе «Пакеты», затем вернитесь сюда.
        </div>
      </details>

      <div class="battle-section-tabs" role="group" aria-label="Раздел батла"><button :aria-pressed="tab === 'statistics'" @click="tab='statistics'"><AppIcon name="chart" />Статистика учеников</button><button :aria-pressed="tab === 'rooms'" @click="tab='rooms'"><AppIcon name="users" />Лобби и комнаты</button></div>
      <TeacherBattleStatistics v-if="tab === 'statistics'" :battle-id="selectedBattle.id" :refresh-key="refreshKey" @open-student="$emit('open-student', $event)" />
      <div v-else>
      <section class="row g-3">
        <div class="col-12 col-lg-6">
          <div class="soft-panel h-100">
            <h4 class="h6 mb-3">Участники лобби</h4>
            <ul class="list-group list-group-flush" v-if="queueEntries.length">
              <li class="list-group-item px-0 d-flex justify-content-between align-items-center" v-for="e in queueEntries" :key="e.user_id">
                <span class="d-flex align-items-center gap-2">
                  <span class="fw-semibold">{{ e.name }}</span>
                  <span
                    class="presence-indicator"
                    :title="e.is_online === false ? 'offline' : 'online'"
                    :aria-label="e.is_online === false ? 'offline' : 'online'"
                  >
                    <span class="presence-dot" :class="e.is_online === false ? 'offline' : 'online'"></span>
                  </span>
                </span>
                <span class="badge" :class="statusClass(e.status)">{{ statusLabel(e.status) }}</span>
              </li>
            </ul>
            <p class="text-muted small mb-0" v-else>Пока нет участников.</p>
          </div>
        </div>

        <div class="col-12 col-lg-6">
          <div class="soft-panel h-100">
            <h4 class="h6 mb-3">Таблица результатов</h4>
            <ul class="list-group list-group-flush" v-if="scoreboardRows.length">
              <li class="list-group-item px-0" v-for="p in scoreboardRows" :key="p.user_id">
                <div class="d-flex justify-content-between align-items-center gap-2 mb-1">
                  <span class="d-flex align-items-center gap-2">
                    <span class="rank-pill">#{{ p.rank }}</span>
                    <span class="fw-semibold">{{ p.name }}</span>
                    <span
                      class="presence-indicator"
                      :title="p.is_online ? 'online' : 'offline'"
                      :aria-label="p.is_online ? 'online' : 'offline'"
                    >
                      <span class="presence-dot" :class="p.is_online ? 'online' : 'offline'"></span>
                    </span>
                    <span v-if="p.win_streak >= 2" class="badge text-bg-warning">бонус x{{ p.win_streak }}</span>
                  </span>
                  <small class="text-muted">pts {{ p.season_points }} · r {{ p.rating }}</small>
                </div>
                <div class="progress" role="progressbar" :aria-valuenow="p.progress_percent" aria-valuemin="0" aria-valuemax="100" style="height: 8px;">
                  <div class="progress-bar" :style="{ width: `${p.progress_percent}%` }"></div>
                </div>
              </li>
            </ul>
            <p class="text-muted small mb-0" v-else>Рейтинг появится после первых завершённых раундов.</p>
          </div>
        </div>
      </section>

      <section class="mt-4">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
          <h4 class="h6 mb-0">Лог комнат</h4>
          <div class="room-filter-wrap">
            <div class="btn-group btn-group-sm room-filter-toggle" role="group" aria-label="Фильтр лога комнат">
              <button
                type="button"
                class="btn"
                :class="roomLogFilter === 'current' ? 'btn-primary' : 'btn-outline-primary'"
                @click="roomLogFilter = 'current'"
              >
                Текущие
              </button>
              <button
                type="button"
                class="btn"
                :class="roomLogFilter === 'completed' ? 'btn-primary' : 'btn-outline-primary'"
                @click="roomLogFilter = 'completed'"
              >
                Завершённые
              </button>
            </div>
          </div>
        </div>
        <p class="room-filter-hint text-muted mb-2">
          Кто с кем играл, состояние комнаты и переход к детальному журналу.
        </p>

        <div class="rooms-grid" v-if="filteredBattleLogs.length">
          <article class="room-card" v-for="room in filteredBattleLogs" :key="room.room_id">
            <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
              <div>
                <div class="fw-semibold">room {{ shortId(room.room_id) }}</div>
                <small class="text-muted">{{ room.created_at ? formatDate(room.created_at) : '—' }}</small>
              </div>
              <span class="badge" :class="roomStatusClass(room.status)">{{ room.status || 'unknown' }}</span>
            </div>

            <p class="mb-1" v-if="room.latest_match?.participants?.length">
              {{ room.latest_match.participants.map((p) => p.student.name).join(' vs ') }}
            </p>
            <p class="mb-1 text-muted" v-else>Нет участников</p>

            <p class="text-muted small mb-3">
              <span v-if="room.latest_match?.task">
                {{ room.latest_match.task.title }} · {{ room.latest_match.task.difficulty || 'unknown' }}
              </span>
              <span v-else>Задача не назначена</span>
              <span class="mx-1">·</span>
              <span>Раундов: {{ room.matches_count ?? 0 }}</span>
            </p>

            <button class="btn btn-sm btn-outline-primary action-btn action-btn-sm w-100" @click="$emit('open-room-log', room.room_id)">
              <AppIcon name="file" />
              <span>Открыть журнал комнаты</span>
            </button>
          </article>
        </div>
        <div class="empty-state" v-else>
          {{ roomLogFilter === 'current' ? 'Текущих комнат пока нет.' : 'Завершённых комнат пока нет.' }}
        </div>
      </section>
      </div>
      <details v-if="canDelete" class="mt-4 small text-muted">
        <summary>Управление архивом</summary>
        <p class="mt-3">Удалить можно только батл без начисленных очков. История начислений сохраняется для пересчёта рейтинга.</p>
        <button class="btn btn-sm btn-outline-danger" @click="$emit('delete-battle')">Удалить батл</button>
      </details>
    </div>
  </section>
</template>

<script setup>
import AppIcon from '../AppIcon.vue'
import { battleStatus } from '../../labels'
import { computed, ref } from 'vue'
import BattleInviteSettings from './BattleInviteSettings.vue'
import TeacherBattleStatistics from './TeacherBattleStatistics.vue'
const tab = ref('statistics')

const props = defineProps({
  refreshKey: Number,
  selectedBattle: { type: Object, default: null },
  battleTasks: { type: Array, default: () => [] },
  taskPackages: { type: Array, default: () => [] },
  battlePackageIds: { type: Array, default: () => [] },
  queueEntries: { type: Array, default: () => [] },
  leaderboardParticipants: { type: Array, default: () => [] },
  canDelete: { type: Boolean, default: false },
  battleLogs: { type: Array, default: () => [] }
})

defineEmits([
  'invite-saved',
  'open-student',
  'back',
  'open-lobby',
  'start',
  'stop',
  'finish',
  'delete-battle',
  'add-package',
  'remove-package',
  'open-room-log'
])

const status = computed(() => props.selectedBattle?.status || 'draft')
const showOpenLobby = computed(() => status.value === 'draft' || status.value === 'stopped')
const showStart = computed(() => status.value === 'draft' || status.value === 'lobby_open' || status.value === 'stopped')
const showStop = computed(() => status.value === 'running')
const showFinish = computed(() => status.value !== 'finished')
const roomLogFilter = ref('current')
const filteredBattleLogs = computed(() => {
  if (roomLogFilter.value === 'completed') {
    return (props.battleLogs || []).filter((room) => isCompletedRoomStatus(room?.status))
  }
  return (props.battleLogs || []).filter((room) => !isCompletedRoomStatus(room?.status))
})
const scoreboardRows = computed(() => {
  const queueMap = new Map((props.queueEntries || []).map((e) => [e.user_id, e]))
  const boardMap = new Map((props.leaderboardParticipants || []).map((p) => [p.user_id, p]))
  const userIds = Array.from(new Set([...queueMap.keys(), ...boardMap.keys()]))
  const rows = userIds.map((userId) => {
    const queueRow = queueMap.get(userId) || {}
    const boardRow = boardMap.get(userId) || {}
    return {
      user_id: userId,
      name: queueRow.name || boardRow.name || String(userId).slice(0, 8),
      season_points: Number(boardRow.season_points || 0),
      rating: Number(boardRow.rating || queueRow.rating || 0),
      win_streak: Number(boardRow.win_streak || 0),
      is_online: queueRow.is_online ?? boardRow.is_online ?? false,
    }
  })
  rows.sort((a, b) => (b.season_points - a.season_points) || (b.rating - a.rating) || a.name.localeCompare(b.name))
  const leaderPoints = rows.length ? Math.max(1, rows[0].season_points) : 1
  return rows.map((row, index) => ({
    ...row,
    rank: index + 1,
    progress_percent: Math.max(0, Math.min(100, Math.round((row.season_points / leaderPoints) * 100))),
  }))
})

function statusLabel(status) {
  if (status === 'fighting') return 'Сражается'
  if (status === 'ready') return 'Готов'
  return 'Не готов'
}

function statusClass(status) {
  if (status === 'fighting') return 'text-bg-primary'
  if (status === 'ready') return 'text-bg-success'
  return 'text-bg-secondary'
}

function roomStatusClass(status) {
  if (status === 'active') return 'text-bg-primary'
  if (status === 'finished') return 'text-bg-success'
  if (status === 'cancelled') return 'text-bg-danger'
  if (status === 'waiting_ready') return 'text-bg-secondary'
  return 'text-bg-secondary'
}

function isCompletedRoomStatus(status) {
  return status === 'finished' || status === 'cancelled'
}

function shortId(id) {
  return String(id || '').slice(0, 8)
}

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString()
}
</script>

<style scoped>
.battle-detail-shell {
  overflow: hidden;
}

.battle-hero { display: grid; gap: 1.5rem; margin-bottom: 2rem; }
.battle-heading { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 1rem; }
.battle-heading > div { min-width: 0; flex: 1 1 280px; }
.battle-heading .page-title { overflow-wrap: anywhere; }
.battle-back { flex-shrink: 0; }
.battle-settings { margin-bottom: 2rem; }
.battle-settings > summary { display: flex; align-items: center; gap: .75rem; padding: .75rem 0; font-weight: 600; cursor: pointer; list-style: none; }
.battle-settings > summary::-webkit-details-marker { display: none; }
.battle-settings > summary .app-icon { color: var(--app-muted); width: .875em; transform: rotate(-90deg); transition: transform 140ms ease; }
.battle-settings[open] > summary { margin-bottom: 1rem; }
.battle-settings[open] > summary .app-icon { transform: rotate(0); }
.package-heading { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: .5rem 1rem; margin-bottom: 1rem; }

.package-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.package-card {
  border: 1px solid var(--app-border);
  border-radius: 12px;
  background: var(--app-card);
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.package-card > div:first-child { min-width: 0; overflow-wrap: anywhere; }
.package-card > div:last-child { flex-wrap: wrap; }

.rank-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 22px;
  padding: 0 0.35rem;
  border-radius: 999px;
  background: #eef3ff;
  color: #234794;
  border: 1px solid #d6e1fa;
  font-size: 0.74rem;
  font-weight: 700;
}

.rooms-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.room-card {
  border: 1px solid #dde6f8;
  border-radius: 12px;
  background: var(--app-card);
  padding: 1rem;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.7);
  transition: transform 140ms ease, box-shadow 140ms ease;
}

.room-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(32, 58, 117, 0.1);
}

.soft-panel :deep(.list-group-item) {
  border-color: #dde7fa;
  background: transparent;
}

.soft-panel :deep(.list-group-item + .list-group-item) {
  margin-top: 0.12rem;
}

.soft-panel :deep(.progress) {
  background: #e5edff;
}

.soft-panel :deep(.progress-bar) {
  background: var(--app-brand);
}

.rooms-grid :deep(.badge),
.package-grid :deep(.badge) {
  font-weight: 700;
}

.room-filter-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
}

.room-filter-toggle {
  border-radius: 10px;
  overflow: hidden;
}

.room-filter-hint {
  font-size: 0.82rem;
}

@media (max-width: 992px) {
  .package-grid,
  .rooms-grid {
    grid-template-columns: 1fr;
  }

  .package-card {
    align-items: center;
  }

  .room-filter-wrap {
    width: 100%;
    justify-content: flex-start;
  }
}
@media (max-width: 575px) {
  .battle-hero { margin-bottom: 1.5rem; }
  .battle-back { order: -1; }
  .battle-heading > div { flex-basis: 100%; }
  .action-ribbon > .btn { flex: 1 1 auto; }
}
</style>
