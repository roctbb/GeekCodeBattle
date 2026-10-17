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
          <button
            v-if="
              !teacher && ['lobby_open', 'running'].includes(data.battle.status)
            "
            class="btn btn-primary"
            @click="$emit('resume', data.battle.id)"
          >
            Продолжить батл
          </button>
          <RouterLink :to="backPath" class="btn btn-outline-secondary">{{
            teacher ? 'К статистике' : 'Все результаты'
          }}</RouterLink>
        </div>
      </header>
      <section v-if="data.standing" class="standing-context" aria-label="Положение в турнире">
        <div class="standing-heading">
          <div><span class="eyebrow">Место в турнире</span><strong class="standing-place">{{ data.standing.place }} <small>из {{ data.standing.total }}</small></strong></div>
          <p v-if="data.standing.change != null" class="standing-change" :class="{ up: data.standing.change > 0, down: data.standing.change < 0 }">
            <strong>{{ data.standing.change > 0 ? '↑' : data.standing.change < 0 ? '↓' : '—' }} {{ data.standing.change ? Math.abs(data.standing.change) : 'Без изменений' }}</strong>
            <span>относительно начала последнего завершённого раунда</span>
          </p>
          <p v-else class="text-muted small mb-0">Динамика появится после завершения первого раунда.</p>
        </div>
        <ol class="standing-neighbors" aria-label="Соседи по таблице">
          <li v-for="neighbor in data.standing.neighbors" :key="neighbor.user_id" :value="neighbor.place" :class="{ 'is-me': neighbor.user_id === student.user_id }">
            <span class="neighbor-place">{{ neighbor.place }}</span><span class="neighbor-name">{{ neighbor.name }}<small v-if="neighbor.user_id === student.user_id">{{ teacher ? 'Этот ученик' : 'Вы' }}</small></span>
            <strong>{{ neighbor.battle_points }} <small>очков</small></strong>
          </li>
        </ol>
        <p class="standing-note">Очки этого турнира; при равенстве — Elo, затем имя. В таблице учтены все допущенные участники.</p>
      </section>
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
        ответа проверяющей системы; завершённые раунды переоценивает
        преподаватель.
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
          <details
            v-if="task.score_rounds?.length"
            class="score-explanation mb-4"
          >
            <summary>Как начислены очки и рейтинг</summary>
            <p class="small text-muted mt-3">
              Победа: 100, ничья: 60, участие: 30 очков. Прогресс решения — до
              40 очков; бонусы за серии — до 30. Принятое решение после сдачи соперника — ещё +20 очков. Очки победы вместе с прогрессом и
              бонусами могут начисляться сразу за первое принятое решение.
              Ниже — сохранённые начисления, включая
              переоценки.
            </p>
            <article
              v-for="(round, i) in task.score_rounds"
              :key="round.match_id"
              class="score-round"
            >
              <strong
                >Раунд {{ round.number || i + 1 }} ·
                {{ resultLabel(round.result) }}</strong
              >
              <p v-if="!round.is_final" class="small text-muted">
                Раунд ещё идёт. Итоговые очки и рейтинг появятся после
                завершения.
              </p>
              <dl>
                <template v-for="(entry, j) in round.entries" :key="j"
                  ><dt>{{ scoreReason(entry.reason) }}</dt>
                  <dd>{{ signed(entry.points) }}</dd></template
                >
              </dl>
              <p v-if="round.rating" class="small mb-0">
                Рейтинг Elo: {{ round.rating.before }} →
                {{ round.rating.after }} ({{
                  signed(round.rating.after - round.rating.before)
                }}). Изменение зависит от результатов и рейтинга соперников.
              </p>
              <p v-else class="text-muted small mb-0">
                Рейтинг будет рассчитан после завершения раунда.
              </p>
            </article>
          </details>
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
              <div class="submission-actions mb-3">
                <button
                  type="button"
                  class="btn btn-sm btn-outline-secondary"
                  @click="copyCode(sub)"
                >
                  {{
                    copiedId === sub.id ? 'Скопировано' : 'Копировать код'
                  }}</button
                ><button
                  type="button"
                  class="btn btn-sm btn-outline-secondary"
                  @click="downloadCode(sub)"
                >
                  Скачать {{ sub.language === 'cpp' ? '.cpp' : '.py' }}</button
                ><button
                  v-if="previousSubmission(task, index)"
                  type="button"
                  class="btn btn-sm btn-outline-secondary"
                  :aria-pressed="compareId === sub.id"
                  @click="compareId = compareId === sub.id ? null : sub.id"
                >
                  {{
                    compareId === sub.id
                      ? 'Показать код'
                      : 'Сравнить с предыдущей'
                  }}</button
                ><button
                  v-if="!teacher && restoreTaskId === task.task_id"
                  type="button"
                  class="btn btn-sm btn-outline-primary"
                  @click="$emit('restore', { ...sub, taskId: task.task_id })"
                >
                  Восстановить в редакторе
                </button>
              </div>
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
                v-if="compareId !== sub.id"
                class="solution-source"
              ><code>{{ sub.source_code }}</code></pre>
              <CodeDiff
                v-else
                :before="previousSubmission(task, index)?.source_code"
                :after="sub.source_code"
                label="Изменения относительно предыдущей посылки"
              />
              <p v-if="copyError" class="text-muted small" role="status">
                {{ copyError }}
              </p>
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
import {
  battleStatus,
  difficultyLabel,
  verdictLabel,
  resultLabel,
} from '../../labels'
import MarkdownText from '../MarkdownText.vue'
import CodeDiff from '../CodeDiff.vue'
const props = defineProps({
  path: { type: String, required: true },
  refreshKey: Number,
  teacher: Boolean,
  backPath: { type: String, default: '/results' },
  taskId: String,
  restoreTaskId: String,
})
defineEmits(['resume', 'restore'])
const compareId = ref(null),
  copiedId = ref(null),
  copyError = ref('')
const signed = (value) => `${value >= 0 ? '+' : ''}${value}`
const scoreReason = (reason) =>
  reason === 'match_surrender_solve_bonus'
    ? 'Решение после сдачи соперника'
    : reason === 'match_instant_win'
    ? 'Победа, прогресс и бонусы: раннее начисление'
    : reason === 'match_finalize:win'
      ? 'Итог победы с учётом раннего начисления'
      : reason === 'match_finalize:draw'
        ? 'Ничья и прогресс'
        : reason === 'match_finalize:loss'
          ? 'Участие и прогресс'
          : reason === 'match_finalize:no_result'
            ? 'Без результата'
            : 'Корректировка начислений'
const previousSubmission = (task, index) =>
  task.submissions
    .slice(index + 1)
    .find((sub) => sub.language === task.submissions[index].language)
async function copyCode(sub) {
  try {
    await navigator.clipboard.writeText(sub.source_code)
    copiedId.value = sub.id
    copyError.value = ''
  } catch {
    copyError.value = 'Копирование недоступно. Выделите код или скачайте файл.'
  }
}
function downloadCode(sub) {
  const url = URL.createObjectURL(
    new Blob([sub.source_code], { type: 'text/plain;charset=utf-8' }),
  )
  const link = document.createElement('a')
  link.href = url
  link.download = `solution-${sub.id}.${sub.language === 'cpp' ? 'cpp' : 'py'}`
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
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
<style scoped>
.standing-context { margin:20px 0; border:1px solid var(--app-border); border-top:2px solid var(--app-brand); padding:20px; background:var(--app-card); }
.standing-heading { display:flex; align-items:center; justify-content:space-between; gap:20px; flex-wrap:wrap; margin-bottom:18px; }
.standing-place { display:block; color:var(--app-brand); font-size:32px; line-height:1.4; font-weight:700; }
.standing-place small { color:var(--app-muted); font-size:16px; font-weight:400; }
.standing-change { display:grid; gap:4px; margin:0; max-width:260px; font-size:13px; color:var(--app-muted); }
.standing-change strong { font-size:18px; color:var(--app-ink); }
.standing-change.up strong { color:#afdabd; }.standing-change.down strong { color:#efb0b8; }
.standing-neighbors { display:grid; gap:6px; margin:0; padding:0; list-style:none; }
.standing-neighbors li { display:flex; align-items:center; gap:14px; padding:11px 14px; background:var(--app-bg-soft); border:1px solid transparent; font-size:13px; }
.standing-neighbors li.is-me { background:#332d21; border-color:#75613e; }
.neighbor-place { width:22px; color:var(--app-muted); font-variant-numeric:tabular-nums; }
.neighbor-name { flex:1; min-width:0; overflow-wrap:anywhere; }.neighbor-name small { margin-left:8px; color:var(--app-brand); }
.standing-neighbors li > strong { flex:none; font-variant-numeric:tabular-nums; }.standing-neighbors strong small { font-size:11px; font-weight:400; color:var(--app-muted); }
.standing-note { margin:12px 0 0; font-size:11px; color:var(--app-muted); }
@media(max-width:540px) { .standing-context { padding:14px; }.standing-neighbors li { padding:10px; gap:8px; } }
.submission-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.score-explanation {
  padding: 16px;
  border: 1px solid var(--app-border);
  border-left: 2px solid var(--app-brand);
}
.score-explanation > summary {
  cursor: pointer;
  color: var(--app-brand);
  font-size: 13px;
}
.score-round {
  padding: 14px 0;
  border-top: 1px solid var(--app-border);
}
.score-round > strong {
  font-size: 13px;
  font-weight: 500;
}
.score-round dl {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  margin: 14px 0;
  font-size: 12px;
}
.score-round dt {
  color: var(--app-muted);
  font-weight: 400;
}
.score-round dd {
  color: var(--app-brand);
  margin: 0;
}
</style>
