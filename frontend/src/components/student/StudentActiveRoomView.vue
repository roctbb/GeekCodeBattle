<template>
  <section class="arena" aria-label="Текущий раунд">
    <header class="arena-heading">
      <div>
        <p class="eyebrow">{{ activeBattleTitle || 'Текущий раунд' }}</p>
        <h1>{{ task?.title || 'Подготовка задачи' }}</h1>
      </div>
      <div class="arena-clock" :class="{ urgent: remaining !== null && remaining <= 60 }">
        <span>{{
          grace?.is_active ? 'На дорешивание' : 'До конца раунда'
        }}</span
        ><strong>{{ timerText }}</strong>
      </div>
    </header>
    <div class="arena-meta">
      <span class="status-chip" :class="`difficulty-${task?.difficulty}`">{{
        difficultyLabel(task?.difficulty)
      }}</span>
      <span v-for="p in participants" :key="p.student_id" class="arena-player"
        ><span
          class="presence-dot"
          :class="p.is_disconnected ? 'offline' : 'online'"
        ></span
        >{{ p.student_id === meId ? 'Вы' : p.name }}
        <span class="text-muted"
          >·
          {{
            p.accepted_at
              ? 'Решено'
              : p.is_disconnected
                ? 'Нет связи'
                : 'Решает'
          }}</span
        ></span
      >
    </div>
    <div
      v-if="grace?.winner_student_id"
      class="notice notice-warning"
      role="status"
    >
      {{ grace.winner_name || 'Соперник' }} решил задачу первым. Можно дорешать
      и получить очки за решение.
    </div>
    <div class="workspace-toolbar">
      <div class="workspace-tabs" role="group" aria-label="Раздел раунда">
        <button :aria-pressed="tab === 'code'" @click="tab = 'code'">
          Решение
        </button>
        <button :aria-pressed="tab === 'task'" @click="tab = 'task'">
          Условие и примеры
        </button>
      </div>
      <button
        class="btn btn-sm btn-outline-secondary split-toggle"
        :aria-pressed="split"
        @click="toggleLayout"
      >
        <AppIcon name="columns" />
        {{ split ? 'Фокус на коде' : 'Рядом с кодом' }}
      </button>
    </div>
    <div
      class="arena-workspace"
      :class="{ 'is-split': split, 'show-task': tab === 'task' }"
    >
      <section class="arena-task" aria-label="Условие задачи">
        <MarkdownText v-if="task" :source="task.statement_md" />
        <p v-else class="text-muted">Загружаем условие…</p>
        <h2 class="h6 mt-4">Примеры</h2>
        <div
          v-for="(test, index) in publicTests"
          :key="index"
          class="example-row"
        >
          <div>
            <span>Ввод {{ index + 1 }}</span>
            <pre>{{ test.input || '(пусто)' }}</pre>
          </div>
          <div>
            <span>Вывод</span>
            <pre>{{ test.expected }}</pre>
          </div>
        </div>
        <p v-if="!publicTests.length" class="text-muted small">
          Для этой задачи примеры не указаны.
        </p>
      </section>
      <section class="arena-solution" aria-label="Редактор решения">
        <div class="editor-toolbar">
          <label class="d-flex align-items-center gap-2" for="solution-language"
            >Язык
            <select
              id="solution-language"
              class="form-select form-select-sm"
              :value="submitLanguage"
              :disabled="isChecking"
              @change="$emit('update:submit-language', $event.target.value)"
            >
              <option value="python">Python</option>
              <option value="cpp">C++</option>
            </select></label
          >
          <span class="draft-status" role="status">{{ draftStatus }}</span>
        </div>
        <Codemirror
          :model-value="submitCode"
          @update:model-value="$emit('update:submit-code', $event)"
          class="arena-code"
          :extensions="extensions"
          :style="{ height: 'clamp(220px, calc(100dvh - 430px), 620px)' }"
          :tab-size="4"
          aria-label="Код решения"
          placeholder="Напишите решение здесь"
        />
        <div class="submit-toolbar">
          <span class="text-muted small">{{
            mySubmission
              ? verdictLabel(mySubmission.verdict)
              : 'Решение ещё не отправлено'
          }}</span>
          <div class="d-flex flex-wrap gap-2">
            <button
              v-if="grace?.can_surrender"
              class="btn btn-outline-secondary"
              :disabled="isChecking || !canSubmit"
              @click="$emit('surrender')"
            >
              Пропустить раунд
            </button>
            <button
              class="btn btn-primary"
              :disabled="isChecking || !canSubmit || !submitCode.trim()"
              @click="$emit('submit')"
            >
              <AppIcon name="send" />
              {{ isChecking ? 'Проверяется…' : 'Отправить решение' }}
            </button>
          </div>
        </div>
        <section class="arena-results" aria-live="polite">
          <div
            class="d-flex justify-content-between align-items-center gap-2 mb-2"
          >
            <h2 class="h6 mb-0">Результаты проверки</h2>
            <span v-if="opponentActivity?.active" class="text-muted small">{{
              opponentActivity.message
            }}</span>
          </div>
          <p v-if="isChecking" class="mb-0 text-muted">
            Решение в очереди проверки. Можно продолжать редактировать код.
          </p>
          <template v-else-if="mySubmission">
            <p
              :class="
                mySubmission.verdict === 'accepted'
                  ? 'text-success'
                  : 'text-muted'
              "
            >
              {{ verdictLabel(mySubmission.verdict) }}
            </p>
            <pre v-if="mySubmission.checker_message" class="checker-feedback">{{
              mySubmission.checker_message
            }}</pre>
            <div class="table-responsive" v-if="publicTests.length">
              <table class="table table-sm mb-0">
                <thead>
                  <tr>
                    <th>Пример</th>
                    <th>Ожидается</th>
                    <th>Получено</th>
                    <th>Результат</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(test, index) in publicTests" :key="index">
                    <td>{{ index + 1 }}</td>
                    <td>
                      <pre>{{ test.expected }}</pre>
                    </td>
                    <td>
                      <pre>{{ test.actual ?? '—' }}</pre>
                    </td>
                    <td>
                      {{
                        test.passed === true
                          ? 'Пройден'
                          : test.passed === false
                            ? 'Ошибка'
                            : 'Нет данных'
                      }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
          <p v-else class="text-muted mb-0">
            Здесь появятся результат и комментарии к вашему решению.
          </p>
        </section>
      </section>
    </div>
  </section>
</template>

<script setup>
import AppIcon from '../AppIcon.vue'
import { Codemirror } from 'vue-codemirror'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { python } from '@codemirror/lang-python'
import { cpp } from '@codemirror/lang-cpp'
import { oneDark } from '@codemirror/theme-one-dark'
import MarkdownText from '../MarkdownText.vue'
import { difficultyLabel, verdictLabel } from '../../labels'
const props = defineProps({
  roomStatus: String,
  activeBattleTitle: String,
  roomId: String,
  task: Object,
  participants: { type: Array, default: () => [] },
  meId: String,
  submitLanguage: { type: String, default: 'python' },
  submitCode: { type: String, default: '' },
  isChecking: Boolean,
  opponentActivity: Object,
  grace: Object,
  round: Object,
  mySubmission: Object,
  canSubmit: { type: Boolean, default: true },
  draftStatus: { type: String, default: '' },
})
defineEmits([
  'update:submit-language',
  'update:submit-code',
  'submit',
  'surrender',
])
const tab = ref('code')
const split = ref(false)
try {
  split.value = localStorage.getItem('gcb:layout') === 'split'
} catch {}
function toggleLayout() {
  split.value = !split.value
  try {
    localStorage.setItem('gcb:layout', split.value ? 'split' : 'focus')
  } catch {}
}
const extensions = computed(() => [
  oneDark,
  props.submitLanguage === 'cpp' ? cpp() : python(),
])
const publicTests = computed(() => props.task?.public_tests || [])
const now = ref(Date.now())
let timer
const remaining = computed(() => {
  const deadline = props.grace?.is_active
    ? props.grace.deadline_at
    : props.round?.deadline_at
  if (!deadline) return null
  return Math.max(
    0,
    Math.ceil((new Date(deadline).getTime() - now.value) / 1000),
  )
})
const timerText = computed(() =>
  remaining.value === null
    ? '—:—'
    : `${String(Math.floor(remaining.value / 60)).padStart(2, '0')}:${String(remaining.value % 60).padStart(2, '0')}`,
)
onMounted(() => {
  timer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.arena-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}
.arena h1 {
  font-size: clamp(1.35rem, 2.2vw, 2rem);
  font-weight: 650;
  letter-spacing: -0.04em;
  margin: 0;
}
.eyebrow {
  font-size: 0.85rem;
  color: var(--app-muted);
  margin-bottom: 0.4rem;
}
.arena-clock {
  text-align: right;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}
.arena-clock span {
  display: block;
  font-size: 0.75rem;
  color: var(--app-muted);
}
.arena-clock strong {
  font:
    600 1.8rem ui-monospace,
    monospace;
}
.arena-clock.urgent strong {
  color: #b45309;
}
.arena-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1.1rem;
  font-size: 0.8rem;
  margin-bottom: 1.5rem;
}
.arena-player {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.workspace-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.7rem;
}
.workspace-tabs {
  display: flex;
  gap: 1.5rem;
}
.workspace-tabs button {
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  padding: 0.6rem 0;
  color: var(--app-muted);
  font-size: 0.9rem;
}
.workspace-tabs button[aria-pressed='true'] {
  border-color: var(--app-brand);
  color: var(--app-ink);
  font-weight: 600;
}
.arena-workspace {
  background: var(--app-card);
  border: 1px solid var(--app-border);
  border-radius: 12px;
  overflow: hidden;
}
.arena-task {
  padding: 1.5rem;
  display: none;
  min-width: 0;
}
.show-task .arena-task {
  display: block;
}
.show-task .arena-solution {
  display: none;
}
.arena-workspace.is-split {
  display: grid;
  grid-template-columns: minmax(280px, 38%) minmax(0, 1fr);
}
.is-split .arena-task {
  display: block;
  border-right: 1px solid var(--app-border);
}
.is-split .arena-solution {
  display: block;
}
.arena-solution {
  min-width: 0;
}
.editor-toolbar,
.submit-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.8rem 1rem;
  font-size: 0.8rem;
}
.editor-toolbar select {
  width: 110px;
}
.draft-status {
  color: var(--app-muted);
  font-size: 0.75rem;
}
.submit-toolbar {
  border-bottom: 1px solid var(--app-border);
}
.arena-code {
  background: #282c34;
}
.arena-results {
  padding: 1rem;
  font-size: 0.85rem;
}
.arena-results pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.checker-feedback {
  background: var(--app-bg);
  padding: 0.8rem;
  border-radius: 6px;
  margin-bottom: 1rem !important;
  max-height: 240px;
  overflow: auto;
}
.example-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  padding: 0.8rem;
  background: var(--app-bg);
  border-radius: 6px;
  margin: 0.75rem 0;
}
.example-row span {
  font-size: 0.75rem;
  color: var(--app-muted);
}
.example-row pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 0.4rem 0 0;
}
@media (max-width: 850px) {
  .split-toggle {
    display: none;
  }
  .arena-workspace.is-split {
    display: block;
  }
  .is-split .arena-task {
    display: none;
    border-right: 0;
  }
  .is-split.show-task .arena-task {
    display: block;
  }
  .is-split.show-task .arena-solution {
    display: none;
  }
}
@media (max-width: 540px) {
  .arena-meta {
    gap: 0.6rem;
  }
  .arena-player {
    flex-wrap: wrap;
  }
  .arena-task {
    padding: 1rem;
  }
  .submit-toolbar > div,
  .submit-toolbar .btn-primary {
    width: 100%;
  }
  .arena-clock strong {
    font-size: 1.5rem;
  }
}
</style>
