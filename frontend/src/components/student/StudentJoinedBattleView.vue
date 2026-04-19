<template>
  <section class="card shadow-sm border-0" v-if="battle">
    <div class="card-body">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <div>
          <h2 class="h5 mb-1">{{ battle.title }}</h2>
          <p class="text-muted mb-0">Статус: {{ battle.status }}</p>
        </div>
      </div>

      <div class="d-flex flex-wrap gap-2 mb-3">
        <button class="btn btn-primary" @click="$emit('ready')">Готов</button>
        <button class="btn btn-outline-secondary" @click="$emit('leave')">Покинуть сражение</button>
      </div>

      <div class="alert alert-primary py-2 px-3 mb-3">
        <strong>Ваш скор:</strong>
        {{ myEntry?.season_points ?? 0 }}
        <span class="text-muted">· рейтинг: {{ myEntry?.rating ?? '—' }}</span>
      </div>

      <h3 class="h6 mb-2">Таблица лобби</h3>
      <div class="list-group list-group-flush">
        <div class="list-group-item px-0" v-for="p in scoreboard" :key="p.user_id">
          <div class="d-flex justify-content-between align-items-center gap-2 mb-1">
            <div class="d-flex align-items-center gap-2">
              <span class="fw-semibold">#{{ p.rank }} {{ p.name }}</span>
              <span
                class="presence-indicator"
                :title="p.is_online ? 'online' : 'offline'"
                :aria-label="p.is_online ? 'online' : 'offline'"
              >
                <span class="presence-dot" :class="p.is_online ? 'online' : 'offline'"></span>
              </span>
              <span class="badge" :class="statusClass(p.status)">{{ statusLabel(p.status) }}</span>
              <span v-if="p.win_streak >= 2" class="badge text-bg-warning">бонус x{{ p.win_streak }}</span>
            </div>
            <div class="text-end">
              <div class="fw-semibold">{{ p.season_points }} очк.</div>
              <small class="text-muted">r {{ p.rating }}</small>
            </div>
          </div>
          <div class="progress" role="progressbar" :aria-valuenow="p.progress_percent" aria-valuemin="0" aria-valuemax="100" style="height: 8px;">
            <div class="progress-bar" :style="{ width: `${p.progress_percent}%` }"></div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  battle: { type: Object, default: null },
  queueEntries: { type: Array, default: () => [] },
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
</script>
