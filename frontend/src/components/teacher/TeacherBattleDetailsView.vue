<template>
  <section class="card shadow-sm border-0" v-if="selectedBattle">
    <div class="card-body">
      <header class="battle-hero mb-4">
        <div class="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-3">
          <div>
            <p class="hero-eyebrow mb-1">Управление батлом</p>
            <h2 class="h4 mb-1">{{ selectedBattle.title }}</h2>
            <p class="text-muted mb-0 d-flex flex-wrap align-items-center gap-2">
              <span class="status-chip" :class="`status-${selectedBattle.status}`">{{ selectedBattle.status }}</span>
              <span>ID: {{ shortId(selectedBattle.id) }}</span>
            </p>
          </div>
          <button class="btn btn-outline-secondary action-btn" @click="$emit('back')">
            <i class="bi bi-arrow-left" aria-hidden="true"></i>
            <span>К списку</span>
          </button>
        </div>

        <section class="hero-stats">
          <article class="hero-stat">
            <span class="hero-stat-label">Задач в пуле</span>
            <span class="hero-stat-value">{{ battleTasks.length }}</span>
          </article>
          <article class="hero-stat">
            <span class="hero-stat-label">Пакетов подключено</span>
            <span class="hero-stat-value">{{ connectedPackagesCount }}</span>
          </article>
          <article class="hero-stat">
            <span class="hero-stat-label">Участников в лобби</span>
            <span class="hero-stat-value">{{ queueEntries.length }}</span>
          </article>
          <article class="hero-stat">
            <span class="hero-stat-label">Комнат</span>
            <span class="hero-stat-value">{{ battleLogs.length }}</span>
          </article>
        </section>
      </header>

      <div class="d-flex flex-wrap gap-2 mb-4 action-ribbon">
        <button
          v-if="showOpenLobby"
          class="btn btn-outline-primary action-btn"
          title="Открыть лобби"
          @click="$emit('open-lobby')"
        >
          <i class="bi bi-door-open-fill" aria-hidden="true"></i>
          <span>Открыть лобби</span>
        </button>
        <button
          v-if="showStart"
          class="btn btn-primary action-btn"
          title="Запустить"
          @click="$emit('start')"
        >
          <i class="bi bi-play-fill" aria-hidden="true"></i>
          <span>Запустить</span>
        </button>
        <button
          v-if="showStop"
          class="btn btn-outline-warning action-btn"
          title="Остановить"
          @click="$emit('stop')"
        >
          <i class="bi bi-pause-fill" aria-hidden="true"></i>
          <span>Остановить</span>
        </button>
        <button
          v-if="showFinish"
          class="btn btn-outline-danger action-btn"
          title="Завершить"
          @click="$emit('finish')"
        >
          <i class="bi bi-stop-fill" aria-hidden="true"></i>
          <span>Завершить</span>
        </button>
        <button
          v-if="canDelete"
          class="btn btn-danger action-btn"
          title="Удалить батл"
          @click="$emit('delete-battle')"
        >
          <i class="bi bi-trash-fill" aria-hidden="true"></i>
          <span>Удалить</span>
        </button>
      </div>

      <section class="mb-4">
        <div class="d-flex justify-content-between align-items-center mb-3">
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
              <i class="bi bi-plus-lg" aria-hidden="true"></i>
              <span>Добавить</span>
            </button>
            <button
              v-else
              class="btn btn-sm btn-outline-danger action-btn action-btn-sm"
              title="Убрать пакет"
              @click="$emit('remove-package', p.id)"
            >
              <i class="bi bi-dash-lg" aria-hidden="true"></i>
              <span>Убрать</span>
            </button>
            </div>
          </article>
        </div>
        <div class="empty-state" v-else>
          Нет доступных пакетов. Добавьте пакет в разделе «Пакеты», затем вернитесь сюда.
        </div>
      </section>

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
            <h4 class="h6 mb-3">Kahoot-лидерборд</h4>
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
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h4 class="h6 mb-0">Лог комнат</h4>
          <small class="text-muted">Кто с кем играл, состояние комнаты и переход к детальному журналу</small>
        </div>

        <div class="rooms-grid" v-if="battleLogs.length">
          <article class="room-card" v-for="room in battleLogs" :key="room.room_id">
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

            <div class="task-statement" v-if="room.latest_match?.task?.statement_md">
              <div class="task-statement-label">Условие задачи</div>
              <pre class="task-statement-text">{{ room.latest_match.task.statement_md }}</pre>
            </div>

            <button class="btn btn-sm btn-outline-primary action-btn action-btn-sm w-100" @click="$emit('open-room-log', room.room_id)">
              <i class="bi bi-journal-text" aria-hidden="true"></i>
              <span>Открыть журнал комнаты</span>
            </button>
          </article>
        </div>
        <div class="empty-state" v-else>
          Комнаты пока не сформированы.
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
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
const showFinish = computed(() => status.value === 'running' || status.value === 'stopped')
const connectedPackagesCount = computed(() => props.battlePackageIds.length)
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
.battle-hero {
  padding: 0.9rem;
  border-radius: 14px;
  border: 1px solid #d9e2f6;
  background: linear-gradient(140deg, #f9fbff 0%, #f3f8ff 100%);
}

.hero-eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.72rem;
  font-weight: 700;
  color: #607191;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.55rem;
}

.hero-stat {
  border: 1px solid #dbe5f8;
  border-radius: 10px;
  background: #fff;
  padding: 0.6rem 0.7rem;
}

.hero-stat-label {
  display: block;
  font-size: 0.78rem;
  color: #637493;
}

.hero-stat-value {
  display: block;
  font-size: 1.2rem;
  font-weight: 800;
  color: #1d3465;
  line-height: 1.15;
}

.package-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.6rem;
}

.package-card {
  border: 1px solid #dce5f8;
  border-radius: 12px;
  background: #fbfdff;
  padding: 0.7rem;
  display: flex;
  justify-content: space-between;
  gap: 0.55rem;
  align-items: center;
}

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
  gap: 0.7rem;
}

.room-card {
  border: 1px solid #dde6f8;
  border-radius: 12px;
  background: #fbfdff;
  padding: 0.75rem;
}

.task-statement {
  border: 1px solid #dce4f7;
  border-radius: 10px;
  background: #f8fbff;
  padding: 0.55rem 0.6rem;
  margin-bottom: 0.7rem;
}

.task-statement-label {
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #5f7090;
  font-weight: 700;
  margin-bottom: 0.3rem;
}

.task-statement-text {
  margin: 0;
  white-space: pre-wrap;
  max-height: 110px;
  overflow: auto;
  font-size: 0.82rem;
  line-height: 1.35;
  color: #2a3f69;
}

@media (max-width: 992px) {
  .hero-stats,
  .package-grid,
  .rooms-grid {
    grid-template-columns: 1fr;
  }
}
</style>
