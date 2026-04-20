<template>
  <section class="card shadow-sm border-0">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h2 class="h5 mb-0">Текущий раунд</h2>
        <span class="badge text-bg-primary">{{ roomStatus || 'in_progress' }}</span>
      </div>
      <p class="text-muted">Сражение: {{ activeBattleTitle || '—' }} · room: {{ roomId }}</p>
      <div class="d-flex flex-wrap gap-2 mb-3">
        <div v-if="roundTimer.label" class="badge text-bg-dark px-3 py-2">
          {{ roundTimer.label }}: {{ roundTimer.value }}
        </div>
        <div v-if="graceTimer.label" class="badge text-bg-warning px-3 py-2">
          {{ graceTimer.label }}: {{ graceTimer.value }}
        </div>
      </div>

      <div v-if="task" class="mb-3">
        <div class="d-flex align-items-center gap-2 mb-2">
          <h3 class="h6 mb-0">{{ task.title }}</h3>
          <span class="badge" :class="difficultyClass">{{ task.difficulty || 'unknown' }}</span>
        </div>
        <pre class="task-pre">{{ task.statement_md }}</pre>
      </div>
      <div class="empty-state mb-3" v-else>
        Задача появится после распределения раунда.
      </div>

      <div class="mb-3" v-if="publicTests.length">
        <h3 class="h6 mb-2">Публичные тесты</h3>
        <div class="table-responsive">
          <table class="table table-sm table-bordered align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 60px;">#</th>
                <th>Вход</th>
                <th>Ожидаемый вывод</th>
                <th>Фактический вывод</th>
                <th style="width: 140px;">Результат</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(t, idx) in publicTests" :key="`pub-test-${idx}`">
                <td>{{ idx + 1 }}</td>
                <td><pre class="mb-0 small">{{ t.input }}</pre></td>
                <td><pre class="mb-0 small">{{ t.expected }}</pre></td>
                <td><pre class="mb-0 small">{{ testActualOutput(t) }}</pre></td>
                <td>
                  <span v-if="t.passed === true" class="badge text-bg-success">Пройден</span>
                  <span v-else-if="t.passed === false" class="badge text-bg-danger">Не пройден</span>
                  <span v-else class="badge text-bg-secondary">Нет данных</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="mb-3" v-if="opponents.length">
        <div class="alert alert-info py-2 px-3 mb-0">
          <strong>{{ opponents.length === 1 ? 'Соперник' : 'Соперники' }}:</strong>
          {{ opponents.map((p) => p.name || shortId(p.student_id)).join(', ') }}
        </div>
      </div>
      <div class="mb-3" v-if="grace?.winner_student_id">
        <div class="alert py-2 px-3 mb-0" :class="grace.is_active ? 'alert-warning' : 'alert-secondary'">
          <strong>Победитель уже найден:</strong>
          {{ grace.winner_name || shortId(grace.winner_student_id) }}.
          <span v-if="grace.is_active">Можно дорешать еще {{ grace.seconds_left }} сек.</span>
          <span v-else>Переход к следующему раунду скоро.</span>
        </div>
      </div>
      <transition name="opponent-pop">
        <div v-if="opponentActivity?.active" class="opponent-activity mb-3" :class="`opponent-${opponentActivity.kind || 'pending'}`">
          <div class="emoji-row">
            <span class="emoji-lg" v-if="opponentActivity.kind === 'pending'">🤔</span>
            <template v-else-if="opponentActivity.kind === 'success'">
              <span class="emoji-fly">✅</span>
              <span class="emoji-fly delay-1">✅</span>
              <span class="emoji-fly delay-2">✅</span>
            </template>
            <template v-else-if="opponentActivity.kind === 'fail'">
              <span class="emoji-fly">❌</span>
              <span class="emoji-fly delay-1">❌</span>
              <span class="emoji-fly delay-2">❌</span>
            </template>
            <template v-else>
              <span class="emoji-fly">⚠️</span>
            </template>
          </div>
          <div class="small">{{ opponentActivity.message }}</div>
        </div>
      </transition>

      <div class="row g-2 mb-3">
        <div class="col-12 col-md-6" v-for="p in participants" :key="p.student_id">
          <div class="participant-tile h-100">
            <div class="d-flex align-items-center gap-2">
              <strong class="d-block">{{ p.student_id === meId ? 'Вы' : (p.name || shortId(p.student_id)) }}</strong>
              <span
                class="presence-indicator"
                :title="isParticipantOffline(p) ? 'offline' : 'online'"
                :aria-label="isParticipantOffline(p) ? 'offline' : 'online'"
              >
                <span class="presence-dot" :class="isParticipantOffline(p) ? 'offline' : 'online'"></span>
              </span>
            </div>
            <small class="text-muted">progress: {{ progressPercent(p.progress) }}% · result: {{ p.result_type || '-' }} · посылок: {{ p.submissions_count ?? 0 }}</small>
          </div>
        </div>
      </div>
      <div class="empty-state mb-3" v-if="!participants.length">
        Список участников скоро появится.
      </div>

      <div class="mb-3" v-if="submissionFeedbackText">
        <div class="alert py-2 px-3 mb-0" :class="submissionFeedbackClass">
          <strong>{{ submissionFeedbackTitle }}:</strong>
          <pre class="mb-0 mt-1 small">{{ submissionFeedbackText }}</pre>
        </div>
      </div>

      <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
        <select
          class="form-select w-auto"
          :value="submitLanguage"
          :disabled="isChecking"
          @change="$emit('update:submit-language', $event.target.value)"
        >
          <option value="python">python</option>
          <option value="cpp">cpp</option>
        </select>
        <button class="btn btn-primary" :disabled="isChecking" @click="$emit('submit')">
          {{ isChecking ? 'Проверяется...' : 'Отправить решение' }}
        </button>
        <button
          v-if="grace?.winner_student_id"
          class="btn btn-outline-danger"
          :disabled="!grace?.can_surrender || isChecking"
          @click="$emit('surrender')"
        >
          Сдаться и ждать следующий раунд
        </button>
        <span class="text-muted small" v-if="isChecking">Идет проверка, повторная отправка недоступна</span>
      </div>

      <Codemirror
        :model-value="submitCode"
        @update:model-value="$emit('update:submit-code', $event)"
        class="code-editor"
        :extensions="codeExtensions"
        :style="{ height: '320px' }"
        placeholder="Введите код"
      />
    </div>
  </section>
</template>

<script setup>
import { Codemirror } from 'vue-codemirror'
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  roomStatus: { type: String, default: null },
  activeBattleTitle: { type: String, default: null },
  roomId: { type: String, default: null },
  task: { type: Object, default: null },
  participants: { type: Array, default: () => [] },
  meId: { type: String, default: '' },
  submitLanguage: { type: String, default: 'python' },
  submitCode: { type: String, default: '' },
  codeExtensions: { type: Array, default: () => [] },
  isChecking: { type: Boolean, default: false },
  opponentActivity: { type: Object, default: null },
  grace: { type: Object, default: null },
  round: { type: Object, default: null },
  mySubmission: { type: Object, default: null }
})

defineEmits(['update:submit-language', 'update:submit-code', 'submit', 'surrender'])

const opponents = computed(() => (props.participants || []).filter((p) => p.student_id !== props.meId))
const publicTests = computed(() => {
  const tests = props.task?.public_tests
  return Array.isArray(tests) ? tests : []
})

const difficultyClass = computed(() => {
  const level = String(props.task?.difficulty || '').toLowerCase()
  if (level === 'easy') return 'text-bg-success'
  if (level === 'medium') return 'text-bg-warning'
  if (level === 'hard') return 'text-bg-danger'
  return 'text-bg-secondary'
})

const nowMs = ref(Date.now())
let tickTimer = null

const roundTimer = computed(() => {
  const deadline = props.round?.deadline_at
  if (!deadline) return { label: '', value: '' }
  const seconds = secondsLeft(deadline)
  return {
    label: 'До конца раунда',
    value: formatSeconds(seconds)
  }
})

const graceTimer = computed(() => {
  const deadline = props.grace?.deadline_at
  if (!deadline) return { label: '', value: '' }
  const seconds = secondsLeft(deadline)
  return {
    label: 'До конца дорешивания',
    value: formatSeconds(seconds)
  }
})

const submissionFeedbackText = computed(() => {
  const submission = props.mySubmission
  if (!submission) return ''
  if (submission.verdict === 'queued' || submission.verdict === 'accepted') return ''
  const message = submission.checker_message ? String(submission.checker_message).trim() : ''
  if (message) return message
  if (submission.verdict === 'internal_error') return 'Во время проверки произошла ошибка.'
  return ''
})

const submissionFeedbackTitle = computed(() => {
  return props.mySubmission?.verdict === 'internal_error' ? 'Ошибка проверки' : 'Комментарий проверки'
})

const submissionFeedbackClass = computed(() => {
  return props.mySubmission?.verdict === 'internal_error' ? 'alert-danger' : 'alert-secondary'
})

onMounted(() => {
  tickTimer = window.setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (tickTimer) {
    window.clearInterval(tickTimer)
    tickTimer = null
  }
})

function shortId(id) {
  return String(id || '').slice(0, 8)
}

function progressPercent(value) {
  const raw = Number(value ?? 0)
  if (!Number.isFinite(raw)) return 0
  return Math.max(0, Math.min(100, Math.round(raw * 1000) / 10))
}

function isParticipantOffline(participant) {
  if (participant?.is_online === false) return true
  return Boolean(participant?.is_disconnected)
}

function secondsLeft(deadlineIso) {
  const deadlineMs = new Date(deadlineIso).getTime()
  if (!Number.isFinite(deadlineMs)) return 0
  return Math.max(0, Math.floor((deadlineMs - nowMs.value) / 1000))
}

function formatSeconds(totalSeconds) {
  const sec = Math.max(0, Number(totalSeconds || 0))
  const minutes = Math.floor(sec / 60)
  const seconds = sec % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function testActualOutput(testRow) {
  const value = testRow?.actual
  if (value === null || value === undefined) return '—'
  const text = String(value)
  return text.length ? text : '(пусто)'
}
</script>

<style scoped>
.opponent-activity {
  border-radius: 12px;
  padding: 0.6rem 0.8rem;
  border: 1px solid #d7dfef;
  background: #f9fbff;
}

.opponent-pending {
  background: #fffaf0;
  border-color: #f3d9a5;
}

.opponent-success {
  background: #f2fff5;
  border-color: #b9ebc8;
}

.opponent-fail {
  background: #fff4f4;
  border-color: #efc6c6;
}

.emoji-row {
  min-height: 28px;
  margin-bottom: 0.2rem;
}

.emoji-lg {
  display: inline-block;
  font-size: 1.35rem;
  animation: thinker 1s ease-in-out infinite;
}

.emoji-fly {
  display: inline-block;
  font-size: 1.2rem;
  margin-right: 0.2rem;
  animation: fly 0.9s ease-out both;
}

.delay-1 {
  animation-delay: 0.1s;
}

.delay-2 {
  animation-delay: 0.2s;
}

.opponent-pop-enter-active,
.opponent-pop-leave-active {
  transition: all 180ms ease;
}

.opponent-pop-enter-from,
.opponent-pop-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@keyframes thinker {
  0% { transform: rotate(0deg) }
  50% { transform: rotate(-9deg) }
  100% { transform: rotate(0deg) }
}

@keyframes fly {
  0% { transform: translateY(8px) scale(0.85); opacity: 0 }
  35% { opacity: 1 }
  100% { transform: translateY(-6px) scale(1.05); opacity: 0.95 }
}
</style>
