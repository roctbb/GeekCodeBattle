<template>
  <section class="battle-shell card shadow-sm border-0" v-if="battle">
    <div class="card-body">
      <header class="joined-hero mb-4">
        <div class="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-3">
          <div>
            <p class="joined-eyebrow mb-1">Лобби баттла</p>
            <h2 class="h4 mb-1">{{ battle.title }}</h2>
            <p class="text-muted mb-0 d-flex flex-wrap align-items-center gap-2">
              <span class="status-pill">{{ battle.status }}</span>
              <span>ID: {{ shortId(battle.id) }}</span>
            </p>
          </div>
        </div>

        <div class="hero-metrics">
          <article class="hero-metric">
            <span class="hero-metric-label">Ваш скор</span>
            <strong class="hero-metric-value">{{ myEntry?.season_points ?? 0 }}</strong>
          </article>
          <article class="hero-metric">
            <span class="hero-metric-label">Рейтинг</span>
            <strong class="hero-metric-value">{{ myEntry?.rating ?? '—' }}</strong>
          </article>
          <article class="hero-metric">
            <span class="hero-metric-label">Участников</span>
            <strong class="hero-metric-value">{{ scoreboard.length }}</strong>
          </article>
          <article class="hero-metric">
            <span class="hero-metric-label">Ваш статус</span>
            <span class="badge" :class="statusClass(myQueueStatus)">{{ statusLabel(myQueueStatus) }}</span>
          </article>
        </div>
      </header>

      <div class="joined-actions d-flex flex-wrap gap-2 mb-3">
        <button class="btn btn-primary" @click="$emit('ready')" :disabled="myQueueStatus === 'ready'">
          <i class="bi bi-lightning-charge-fill" aria-hidden="true"></i>
          {{ myQueueStatus === 'ready' ? 'Вы уже готовы' : 'Готов к раунду' }}
        </button>
        <button class="btn btn-outline-secondary" @click="$emit('leave')">
          <i class="bi bi-box-arrow-left" aria-hidden="true"></i>
          Покинуть сражение
        </button>
      </div>

      <div class="my-ready-status mb-4" :class="myQueueStatus === 'ready' ? 'is-ready' : 'is-not-ready'">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <span class="text-muted">Ваш статус:</span>
          <span class="badge" :class="statusClass(myQueueStatus)">{{ statusLabel(myQueueStatus) }}</span>
        </div>
        <div class="my-ready-hint" v-if="myQueueStatus !== 'ready'">
          Нажмите «Готов к раунду», чтобы попасть в следующий матч.
        </div>
      </div>

      <section class="matchmaking-status mb-4" :class="`mm-${matchmakingStatus.tone}`" aria-live="polite">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-1">
          <h3 class="h6 mb-0">Матчмейкинг</h3>
          <span class="badge" :class="matchmakingStatus.badgeClass">{{ matchmakingStatus.badgeText }}</span>
        </div>
        <p class="mb-1">{{ matchmakingStatus.title }}</p>
        <small class="text-muted d-block">{{ matchmakingStatus.details }}</small>
      </section>

      <section class="bonus-rules mb-4" aria-label="Правила бонусов">
        <div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
          <h3 class="h6 mb-0">Правила бонусов</h3>
          <span class="bonus-cap">Лимит: +30 за раунд</span>
        </div>
        <ul class="bonus-rule-list mb-0">
          <li>2 победы подряд: <strong>+10</strong></li>
          <li>3 победы подряд: <strong>+20</strong></li>
          <li>4+ побед подряд: <strong>+30</strong></li>
          <li>Победа после 3+ поражений подряд: <strong>+20</strong></li>
        </ul>
      </section>

      <div class="d-flex justify-content-between align-items-center gap-2 mb-2">
        <h3 class="h6 mb-0">Таблица лобби</h3>
        <small class="text-muted">Позиция считается по очкам и рейтингу</small>
      </div>

      <div class="scoreboard-list" v-if="scoreboard.length">
        <article class="scoreboard-item" :class="{ 'is-me': p.user_id === meId }" v-for="p in scoreboard" :key="p.user_id">
          <div class="d-flex justify-content-between align-items-center gap-2 mb-1">
            <div class="d-flex align-items-center gap-2 flex-wrap">
              <span class="rank-badge">#{{ p.rank }}</span>
              <span class="fw-semibold">{{ p.name }}</span>
              <span
                class="presence-indicator"
                :title="p.is_online ? 'online' : 'offline'"
                :aria-label="p.is_online ? 'online' : 'offline'"
              >
                <span class="presence-dot" :class="p.is_online ? 'online' : 'offline'"></span>
              </span>
              <span class="badge" :class="statusClass(p.status)">{{ statusLabel(p.status) }}</span>
              <span v-if="streakBonus(p.win_streak) > 0" class="badge text-bg-warning">серия +{{ streakBonus(p.win_streak) }}</span>
            </div>
            <div class="text-end">
              <div class="fw-semibold">{{ p.season_points }} очк.</div>
              <small class="text-muted">r {{ p.rating }}</small>
            </div>
          </div>
          <div class="progress" role="progressbar" :aria-valuenow="p.progress_percent" aria-valuemin="0" aria-valuemax="100" style="height: 8px;">
            <div class="progress-bar" :style="{ width: `${p.progress_percent}%` }"></div>
          </div>
        </article>
      </div>

      <p class="text-muted mb-0" v-else>Пока нет участников в таблице.</p>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  battle: { type: Object, default: null },
  queueEntries: { type: Array, default: () => [] },
  queueMeta: { type: Object, default: null },
  meId: { type: String, default: null },
  myScore: { type: Object, default: null },
  leaderboardParticipants: { type: Array, default: () => [] }
})

defineEmits(['ready', 'leave'])

const scoreboard = computed(() => {
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
      status: queueRow.status || 'not_ready',
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

const myEntry = computed(() => {
  if (!props.myScore?.user_id) return props.myScore || null
  return scoreboard.value.find((item) => item.user_id === props.myScore.user_id) || props.myScore
})

const myQueueStatus = computed(() => {
  if (!props.meId) return 'not_ready'
  const row = (props.queueEntries || []).find((item) => item.user_id === props.meId)
  return row?.status || 'not_ready'
})

const matchmakingStatus = computed(() => {
  const meta = props.queueMeta || {}
  const reason = String(meta.reason || '')
  const readyEligible = Number(meta.ready_eligible || 0)
  const minPlayers = Math.max(2, Number(meta.min_players_to_start || 2))
  const activeTotal = Math.max(0, Number(meta.active_total || 0))
  const waitLeft = Math.max(0, Number(meta.wait_left_seconds || 0))
  const needMore = Math.max(0, minPlayers - readyEligible)

  if (myQueueStatus.value === 'fighting') {
    return {
      tone: 'active',
      badgeClass: 'text-bg-primary',
      badgeText: 'В матче',
      title: 'Раунд уже идет, ждите завершения.',
      details: `Активных раундов сейчас: ${activeTotal}.`,
    }
  }

  if (myQueueStatus.value !== 'ready') {
    return {
      tone: 'idle',
      badgeClass: 'text-bg-secondary',
      badgeText: 'Не в поиске',
      title: 'Поиск матча не запущен.',
      details: 'Нажмите «Готов к раунду», чтобы начать подбор соперников.',
    }
  }

  if (reason === 'battle_not_running') {
    return {
      tone: 'paused',
      badgeClass: 'text-bg-dark',
      badgeText: 'Ожидание старта',
      title: 'Баттл еще не в статусе running.',
      details: 'Матчи начнутся после команды «Запустить» от учителя.',
    }
  }

  if (reason === 'not_enough_ready') {
    return {
      tone: 'search',
      badgeClass: 'text-bg-info',
      badgeText: 'Поиск игроков',
      title: `Готовых сейчас ${readyEligible}/${minPlayers}.`,
      details: `Нужно еще участников: ${needMore}.`,
    }
  }

  if (reason === 'waiting_delay') {
    return {
      tone: 'balance',
      badgeClass: 'text-bg-warning',
      badgeText: 'Балансировка',
      title: 'Подбор уже идет, формируем комнату.',
      details: `Ожидаем запуск: ${formatMmSeconds(waitLeft)}.`,
    }
  }

  if (reason === 'ready_to_match') {
    return {
      tone: 'launch',
      badgeClass: 'text-bg-success',
      badgeText: 'Почти старт',
      title: 'Комната готовится к запуску.',
      details: `Готовых для старта: ${readyEligible}/${minPlayers}.`,
    }
  }

  return {
    tone: 'search',
    badgeClass: 'text-bg-info',
    badgeText: 'Поиск',
    title: 'Идет подбор соперников.',
    details: `Готовых: ${readyEligible}/${minPlayers}.`,
  }
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

function streakBonus(streakRaw) {
  const streak = Number(streakRaw || 0)
  if (streak >= 4) return 30
  if (streak === 3) return 20
  if (streak === 2) return 10
  return 0
}

function formatMmSeconds(totalSeconds) {
  const sec = Math.max(0, Number(totalSeconds || 0))
  const mm = Math.floor(sec / 60)
  const ss = sec % 60
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}

function shortId(id) {
  return String(id || '').slice(0, 8)
}
</script>

<style scoped>
.battle-shell {
  overflow: hidden;
}

.joined-hero {
  border: 1px solid #d9e5fd;
  border-radius: 16px;
  background:
    radial-gradient(circle at 10% -10%, rgba(43, 95, 255, 0.14), rgba(43, 95, 255, 0) 45%),
    radial-gradient(circle at 100% 0%, rgba(14, 165, 164, 0.14), rgba(14, 165, 164, 0) 38%),
    linear-gradient(145deg, #f9fbff 0%, #f4f8ff 100%);
  padding: 0.9rem;
}

.joined-eyebrow {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #4d6190;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 700;
  border: 1px solid #d6e2fc;
  background: #edf3ff;
  color: #234794;
}

.hero-metrics {
  display: grid;
  gap: 0.55rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.hero-metric {
  border: 1px solid #dbe5f9;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.85);
  padding: 0.58rem 0.66rem;
}

.hero-metric-label {
  display: block;
  font-size: 0.74rem;
  color: #62749a;
}

.hero-metric-value {
  font-size: 1.12rem;
  line-height: 1.2;
  color: #1f3568;
}

.joined-actions .btn {
  display: inline-flex;
  align-items: center;
  gap: 0.42rem;
}

.my-ready-status {
  border-radius: 12px;
  padding: 0.75rem 0.9rem;
  border: 1px solid transparent;
}

.my-ready-status.is-ready {
  background: #edf9f0;
  border-color: #c3e8cf;
}

.my-ready-status.is-not-ready {
  background: #fff4e6;
  border-color: #ffd8a8;
}

.my-ready-hint {
  margin-top: 0.35rem;
  font-weight: 600;
}

.matchmaking-status {
  border: 1px solid #dbe5f9;
  border-radius: 12px;
  background: #f8fbff;
  padding: 0.78rem 0.9rem;
}

.matchmaking-status.mm-idle {
  background: #f5f7fb;
  border-color: #d9deea;
}

.matchmaking-status.mm-search {
  background: #eef8ff;
  border-color: #c9e6ff;
}

.matchmaking-status.mm-balance {
  background: #fff8eb;
  border-color: #ffe1b0;
}

.matchmaking-status.mm-launch {
  background: #edf9f0;
  border-color: #c7ebd0;
}

.matchmaking-status.mm-active {
  background: #edf3ff;
  border-color: #ccdcff;
}

.matchmaking-status.mm-paused {
  background: #f3f4f6;
  border-color: #d4d6db;
}

.bonus-rules {
  border: 1px solid #dbe5f9;
  border-radius: 12px;
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.94) 0%, rgba(248, 252, 255, 0.94) 100%),
    radial-gradient(circle at 100% 0%, rgba(14, 165, 164, 0.13), rgba(14, 165, 164, 0) 42%);
  padding: 0.78rem 0.9rem;
}

.bonus-cap {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 700;
  border: 1px solid #d6e2fc;
  background: #edf3ff;
  color: #234794;
}

.bonus-rule-list {
  padding-left: 1.05rem;
}

.bonus-rule-list li + li {
  margin-top: 0.2rem;
}

.scoreboard-list {
  display: grid;
  gap: 0.6rem;
}

.scoreboard-item {
  border: 1px solid #dbe5f9;
  border-radius: 12px;
  background: #fbfdff;
  padding: 0.72rem;
}

.scoreboard-item.is-me {
  border-color: #b9d1ff;
  background: linear-gradient(180deg, #f8fbff 0%, #f2f7ff 100%);
  box-shadow: inset 0 0 0 1px rgba(43, 95, 255, 0.15);
}

.rank-badge {
  min-width: 32px;
  height: 22px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #d4e1fb;
  background: #edf3ff;
  color: #24499a;
  font-size: 0.74rem;
  font-weight: 700;
}

@media (max-width: 992px) {
  .hero-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .joined-actions .btn {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 576px) {
  .hero-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
