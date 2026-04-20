<template>
  <section class="card shadow-sm border-0" v-if="roomLog">
    <div class="card-body">
      <header class="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-4">
        <div>
          <h2 class="h5 mb-1 d-flex align-items-center gap-2">
            Комната {{ shortId(roomLog.room.room_id) }}
            <span class="badge" :class="roomStatusClass(roomLog.room.status)">{{ roomLog.room.status }}</span>
          </h2>
          <p class="text-muted mb-0">Детальный журнал по раундам, участникам и отправкам решений.</p>
        </div>
        <button class="btn btn-outline-secondary action-btn" @click="$emit('back')">
          <i class="bi bi-arrow-left" aria-hidden="true"></i>
          <span>Назад к логу сражения</span>
        </button>
      </header>

      <section class="room-overview mb-4">
        <article class="overview-tile">
          <div class="overview-value">{{ roomSummary.rounds }}</div>
          <div class="overview-label">Раундов</div>
        </article>
        <article class="overview-tile">
          <div class="overview-value">{{ roomSummary.submissions }}</div>
          <div class="overview-label">Посылок</div>
        </article>
        <article class="overview-tile">
          <div class="overview-value">{{ roomSummary.accepted }}</div>
          <div class="overview-label">Принятых</div>
        </article>
        <article class="overview-tile">
          <div class="overview-value">{{ roomSummary.participants }}</div>
          <div class="overview-label">Участников</div>
        </article>
      </section>

      <div class="empty-state" v-if="!matches.length">
        В этой комнате пока нет раундов.
      </div>

      <section class="d-flex flex-column gap-3" v-else>
        <article class="round-card" v-for="(match, index) in matches" :key="match.match_id">
          <div class="round-header mb-3">
            <div>
              <p class="round-eyebrow mb-1">Раунд {{ index + 1 }}</p>
              <h3 class="h6 mb-1">{{ match.task?.title || `ID ${shortId(match.match_id)}` }}</h3>
              <p class="text-muted mb-0 d-flex flex-wrap align-items-center gap-2">
                <span class="badge difficulty-badge" :class="`difficulty-${match.task?.difficulty || 'unknown'}`">{{ match.task?.difficulty || 'unknown' }}</span>
                <span>{{ formatDate(match.created_at) }}</span>
              </p>
            </div>
            <div class="round-stats">
              <span class="badge text-bg-light border">Посылок: {{ match.submissions?.length || 0 }}</span>
              <span class="badge text-bg-light border">Accepted: {{ acceptedCount(match) }}</span>
            </div>
          </div>

          <section class="task-statement mb-3" v-if="match.task?.statement_md">
            <div class="task-statement-label">Условие задачи</div>
            <pre class="task-statement-text">{{ match.task.statement_md }}</pre>
          </section>

          <div class="mb-3" v-if="match.participants?.length">
            <strong class="d-block mb-2">Участники</strong>
            <div class="participants-grid">
              <article class="participant-card" v-for="p in match.participants" :key="`${match.match_id}-${p.student.id}`">
                <div class="d-flex justify-content-between align-items-center gap-2 mb-1">
                  <span class="d-flex align-items-center gap-2">
                    <strong>{{ p.student.name }}</strong>
                    <span
                      class="presence-indicator"
                      :title="isParticipantOffline(p) ? 'offline' : 'online'"
                      :aria-label="isParticipantOffline(p) ? 'offline' : 'online'"
                    >
                      <span class="presence-dot" :class="isParticipantOffline(p) ? 'offline' : 'online'"></span>
                    </span>
                  </span>
                  <div class="d-flex align-items-center gap-1">
                    <span class="badge" :class="resultClass(p.result_type)">{{ p.result_type || 'pending' }}</span>
                  </div>
                </div>
                <div class="progress-track">
                  <div class="progress-bar" :style="{ width: `${progressPercent(p.progress)}%` }"></div>
                </div>
                <small class="text-muted">{{ progressPercent(p.progress) }}%</small>
                <small class="text-muted d-block">посылок: {{ participantSubmissionsCount(match, p.student.id) }}</small>
              </article>
            </div>
          </div>

          <div class="submissions-stack" v-if="match.submissions?.length">
            <article class="submission-item" v-for="s in match.submissions" :key="s.submission_id">
              <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                <div class="d-flex flex-wrap align-items-center gap-2">
                  <strong>{{ s.student.name }}</strong>
                  <span class="badge text-bg-light border">{{ s.language || '—' }}</span>
                  <span class="badge" :class="verdictClass(s.verdict)">{{ s.verdict || 'unknown' }}</span>
                </div>
                <small class="text-muted">{{ formatDate(s.created_at) }} · тесты {{ testsText(s) }}</small>
              </div>
              <div class="d-flex justify-content-end mb-2">
                <button
                  class="btn btn-sm btn-outline-primary action-btn action-btn-sm"
                  :disabled="isRechecking(s.submission_id)"
                  @click="$emit('recheck-submission', { matchId: match.match_id, submissionId: s.submission_id })"
                >
                  <span v-if="isRechecking(s.submission_id)">Отправляем...</span>
                  <span v-else>Отправить на перепроверку</span>
                </button>
              </div>
              <details class="code-details">
                <summary>Показать код</summary>
                <pre class="code-view mt-2 mb-0">{{ s.source_code || '' }}</pre>
              </details>
            </article>
          </div>

          <div class="text-muted" v-else>Посылок в этом раунде не было.</div>
        </article>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  roomLog: { type: Object, default: null },
  recheckingSubmissionIds: { type: Array, default: () => [] }
})

defineEmits(['back', 'recheck-submission'])

const matches = computed(() => (props.roomLog?.matches || []))
const roomSummary = computed(() => {
  const summary = { rounds: matches.value.length, submissions: 0, accepted: 0, participants: 0 }
  const participantIds = new Set()
  for (const match of matches.value) {
    const submissions = match?.submissions || []
    summary.submissions += submissions.length
    summary.accepted += submissions.filter((s) => s.verdict === 'accepted').length
    for (const p of match?.participants || []) {
      if (p?.student?.id) participantIds.add(p.student.id)
    }
  }
  summary.participants = participantIds.size
  return summary
})

function shortId(id) {
  return String(id || '').slice(0, 8)
}

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString()
}

function acceptedCount(match) {
  return (match?.submissions || []).filter((s) => s.verdict === 'accepted').length
}

function verdictClass(verdict) {
  if (verdict === 'accepted') return 'text-bg-success'
  if (verdict === 'wrong_answer') return 'text-bg-danger'
  if (verdict === 'queued') return 'text-bg-secondary'
  if (verdict === 'internal_error') return 'text-bg-warning'
  if (verdict === 'surrendered') return 'text-bg-dark'
  return 'text-bg-secondary'
}

function resultClass(resultType) {
  if (resultType === 'accepted') return 'text-bg-success'
  if (resultType === 'wrong_answer') return 'text-bg-danger'
  if (resultType === 'surrendered') return 'text-bg-dark'
  return 'text-bg-secondary'
}

function roomStatusClass(status) {
  if (status === 'active') return 'text-bg-primary'
  if (status === 'finished') return 'text-bg-success'
  if (status === 'cancelled') return 'text-bg-danger'
  return 'text-bg-secondary'
}

function testsText(s) {
  if (Number.isInteger(s.visible_tests_passed) && Number.isInteger(s.visible_tests_total)) {
    return `${s.visible_tests_passed}/${s.visible_tests_total}`
  }
  return '—'
}

function progressPercent(value) {
  const raw = Number(value ?? 0)
  if (!Number.isFinite(raw)) return 0
  return Math.max(0, Math.min(100, Math.round(raw * 1000) / 10))
}

function participantSubmissionsCount(match, studentId) {
  return (match?.submissions || []).filter((s) => s?.student?.id === studentId).length
}

function isParticipantOffline(participant) {
  if (participant?.is_online === false) return true
  return Boolean(participant?.is_disconnected)
}

function isRechecking(submissionId) {
  return props.recheckingSubmissionIds.includes(submissionId)
}
</script>

<style scoped>
.room-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.65rem;
}

.overview-tile {
  border: 1px solid #d9e2f6;
  border-radius: 12px;
  background: linear-gradient(180deg, #f9fbff 0%, #f4f8ff 100%);
  padding: 0.75rem;
}

.overview-value {
  font-size: 1.35rem;
  font-weight: 800;
  color: #203565;
  line-height: 1.1;
}

.overview-label {
  color: #607191;
  font-size: 0.82rem;
}

.round-card {
  border: 1px solid #dbe4f8;
  border-radius: 14px;
  background: #fbfdff;
  padding: 0.95rem;
}

.round-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.round-eyebrow {
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #607191;
  font-weight: 700;
}

.round-stats {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.task-statement {
  border: 1px solid #dce4f7;
  border-radius: 10px;
  background: #f8fbff;
  padding: 0.55rem 0.65rem;
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
  max-height: 160px;
  overflow: auto;
  font-size: 0.84rem;
  line-height: 1.35;
  color: #2a3f69;
}

.difficulty-badge {
  text-transform: lowercase;
}

.difficulty-easy {
  background: #e7f8ee;
  color: #1f7a40;
  border: 1px solid #c7e9d4;
}

.difficulty-medium {
  background: #fff8e8;
  color: #8c6100;
  border: 1px solid #f1dfb6;
}

.difficulty-hard {
  background: #ffeef0;
  color: #a12938;
  border: 1px solid #f8d0d5;
}

.difficulty-unknown {
  background: #eef2f8;
  color: #55627d;
  border: 1px solid #d7dfec;
}

.participants-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem;
}

.participant-card {
  border: 1px solid #dbe4f8;
  border-radius: 10px;
  background: #fff;
  padding: 0.55rem;
}

.progress-track {
  height: 7px;
  border-radius: 999px;
  background: #e8eefb;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2b5fff 0%, #0ea5a4 100%);
  transition: width 220ms ease-out;
}

.submissions-stack {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.submission-item {
  border: 1px solid #dfe7f8;
  border-radius: 10px;
  background: #fff;
  padding: 0.65rem;
}

.code-details summary {
  cursor: pointer;
  color: #2b5fff;
  font-weight: 600;
}

.code-view {
  max-height: 240px;
  overflow: auto;
  padding: 0.7rem;
  border-radius: 10px;
  background: #0f1727;
  color: #e3ecff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem;
}

@media (max-width: 992px) {
  .room-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .participants-grid {
    grid-template-columns: 1fr;
  }
}
</style>
