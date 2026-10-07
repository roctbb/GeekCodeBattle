<template>
  <section>
    <div v-if="error" class="notice notice-warning mb-3" role="alert">
      {{ error }}
      <button class="btn btn-sm btn-outline-secondary" @click="reload">
        Повторить
      </button>
    </div>
    <p v-if="loading" role="status">Загружаем решения…</p>
    <template v-if="data && student">
      <header class="report-page-heading">
        <div>
          <p class="eyebrow">
            {{ teacher ? 'Результаты ученика' : 'Мои результаты' }}
          </p>
          <h1>{{ data.battle.title }}</h1>
          <p class="text-muted mb-0">
            {{ student.name }} <span class="mx-1">·</span>
            {{ battleStatus(data.battle.status) }}
          </p>
        </div>
        <div class="d-flex flex-wrap gap-2">
          <button v-if="!teacher && ['lobby_open', 'running'].includes(data.battle.status)" class="btn btn-primary" @click="$emit('resume', data.battle.id)">Продолжить батл</button>
          <RouterLink :to="backPath" class="btn btn-outline-secondary">{{
            teacher ? 'К статистике' : 'Все результаты'
          }}</RouterLink>
        </div>
      </header>
      <div class="report-metrics mb-4">
        <article>
          <span>Решено задач</span
          ><strong>{{ student.solved }} / {{ student.assigned }}</strong>
        </article>
        <article>
          <span>Не решено из выданных</span
          ><strong>{{ student.unsolved }}</strong>
        </article>
        <article>
          <span>Отправлено посылок</span><strong>{{ student.attempts }}</strong>
        </article>
        <article>
          <span>Очки за батл</span><strong>{{ student.points }}</strong
          ><small
            >Рейтинг {{ student.rating_delta >= 0 ? '+' : ''
            }}{{ student.rating_delta }}</small
          >
        </article>
      </div>
      <div v-if="student.pending" class="notice notice-warning mb-3">
        Проверяются посылки: {{ student.pending }}. История обновится после
        ответа проверяющей системы; завершённые раунды переоценивает преподаватель.
      </div>
      <div class="report-toolbar">
        <h2 class="h5 mb-0">Задачи и решения</h2>
        <label class="d-flex align-items-center gap-2 small"
          >Показать
          <select v-model="filter" class="form-select form-select-sm">
            <option value="all">Все задачи</option>
            <option value="solved">Решённые</option>
            <option value="unsolved">Нерешённые</option>
            <option value="not_assigned">Не выдавались</option>
          </select></label
        >
      </div>
      <p v-if="student.not_assigned" class="text-muted small">
        Не выдавались в раундах: {{ student.not_assigned }}. Такие задачи не
        учитываются как нерешённые.
      </p>
      <details
        v-for="task in filteredTasks"
        :key="task.task_id"
        class="card result-task mb-3"
        :open="openedTask === task.task_id"
        @toggle="onToggle(task.task_id, $event)"
      >
        <summary>
          <span
            ><strong>{{ task.title }}</strong
            ><small class="text-muted d-block"
              >Посылок: {{ task.attempts }} ·
              {{ difficultyLabel(task.difficulty) }}</small
            ></span
          ><span class="result-state" :class="task.state">{{
            taskState(task.state)
          }}</span>
        </summary>
        <div class="card-body border-top">
          <MarkdownText :source="task.statement_md" class="mb-4" />
          <details v-if="task.public_tests?.length" class="mb-4">
            <summary class="small">Примеры</summary>
            <div
              v-for="(test, i) in task.public_tests"
              :key="i"
              class="result-example"
            >
              <div>
                <small>Ввод {{ i + 1 }}</small>
                <pre>{{ test.input || '(пусто)' }}</pre>
              </div>
              <div>
                <small>Вывод</small>
                <pre>{{ test.expected }}</pre>
              </div>
            </div>
          </details>
          <h3 class="h6 mb-3">
            {{ teacher ? 'Посылки ученика' : 'Мои посылки' }}
          </h3>
          <p v-if="!task.submissions.length" class="text-muted mb-0">
            {{
              task.assigned
                ? 'Решение не было отправлено.'
                : 'Задача не выдавалась в раундах.'
            }}
          </p>
          <details
            v-for="(sub, index) in task.submissions"
            :key="sub.id"
            class="submission-item"
            :open="index === 0"
          >
            <summary>
              <span
                class="result-state"
                :class="
                  sub.verdict === 'accepted'
                    ? 'solved'
                    : sub.verdict === 'queued'
                      ? 'pending'
                      : 'attempted'
                "
                >{{ verdictLabel(sub.verdict) }}</span
              ><span class="small text-muted"
                >{{ formatDate(sub.created_at) }} ·
                {{ sub.language === 'cpp' ? 'C++' : 'Python'
                }}<span v-if="sub.after_round">
                  · перепроверка после раунда</span
                ></span
              >
            </summary>
            <div class="submission-body">
              <div class="small text-muted mb-2">
                Пройдено: {{ Math.round(sub.progress * 100) }}%<span
                  v-if="sub.visible_tests_total != null"
                >
                  · Публичные тесты: {{ sub.visible_tests_passed ?? '—' }}/{{
                    sub.visible_tests_total
                  }}</span
                >
              </div>
              <pre
                class="solution-source"
              ><code>{{ sub.source_code }}</code></pre>
              <pre v-if="sub.comment" class="checker-feedback">{{
                sub.comment
              }}</pre>
            </div>
          </details>
        </div>
      </details>
      <p v-if="!filteredTasks.length" class="empty-state">
        Нет задач для этого фильтра.
      </p>
    </template>
  </section>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import { useReport } from '../../composables/useReport'
import { battleStatus, difficultyLabel, verdictLabel } from '../../labels'
import MarkdownText from '../MarkdownText.vue'
const props = defineProps({
  path: { type: String, required: true },
  refreshKey: Number,
  teacher: Boolean,
  backPath: { type: String, default: '/results' },
  taskId: String,
})
defineEmits(['resume'])
const { data, loading, error, reload } = useReport(
  () => props.path,
  () => props.refreshKey,
)
const student = computed(() => data.value?.students?.[0])
const filter = ref('all'),
  openedTask = ref(props.taskId || null)
watch(
  () => props.path,
  () => {
    filter.value = 'all'
    openedTask.value = props.taskId || null
  },
)
watch(
  () => props.taskId,
  (id) => {
    openedTask.value = id || null
    filter.value = 'all'
  },
)
const filteredTasks = computed(() =>
  (student.value?.tasks || []).filter(
    (t) =>
      filter.value === 'all' ||
      (filter.value === 'unsolved'
        ? t.assigned && t.state !== 'solved'
        : t.state === filter.value),
  ),
)
function onToggle(id, event) {
  if (event.target.open) openedTask.value = id
  else if (openedTask.value === id) openedTask.value = null
}
const taskState = (state) =>
  ({
    solved: 'Решена',
    attempted: 'Не решена',
    unattempted: 'Нет посылок',
    not_assigned: 'Не выдавалась',
  })[state]
const formatDate = (value) =>
  value ? new Date(value).toLocaleString('ru-RU') : '—'
</script>
