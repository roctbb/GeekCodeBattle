<template>
  <section aria-label="Статистика учеников">
    <div v-if="error" class="notice notice-warning mb-3" role="alert">
      {{ error }}
      <button class="btn btn-sm btn-outline-secondary" @click="reload">
        Повторить
      </button>
    </div>
    <p v-if="loading" role="status">Загружаем статистику…</p>
    <template v-if="data">
      <div class="report-metrics mb-4">
        <article>
          <span>Участников</span
          ><strong>{{ data.summary.participants }}</strong>
        </article>
        <article>
          <span>Задач в батле</span><strong>{{ data.summary.tasks }}</strong>
        </article>
        <article>
          <span>Решено учениками</span
          ><strong>{{ data.summary.solved }}</strong>
        </article>
        <article>
          <span>Посылок</span><strong>{{ data.summary.attempts }}</strong
          ><small v-if="data.summary.pending"
            >{{ data.summary.pending }} проверяются</small
          >
        </article>
      </div>
      <div class="report-toolbar">
        <div>
          <h2 class="h5 mb-1">Ученики и задачи</h2>
          <p class="text-muted small mb-0">
            Нажмите на ученика или задачу, чтобы открыть все его посылки.
          </p>
        </div>
        <input
          v-model="query"
          class="form-control student-search"
          aria-label="Поиск ученика"
          placeholder="Найти ученика"
          type="search"
        />
      </div>
      <div v-if="rows.length" class="table-responsive matrix-scroll">
        <table class="table report-table matrix-table mb-0">
          <thead>
            <tr>
              <th class="matrix-name">Ученик</th>
              <th>Очки</th>
              <th>Решено</th>
              <th>Не решено</th>
              <th>Посылки</th>
              <th v-for="(task, index) in data.tasks" :key="task.id">
                <span :title="task.title"
                  >{{ index + 1 }}. {{ task.title }}</span
                >
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="student in rows" :key="student.user_id">
              <th class="matrix-name">
                <button
                  class="student-link"
                  @click="$emit('open-student', { studentId: student.user_id })"
                >
                  <small class="text-muted me-2">{{ student.place }}</small
                  >{{ student.name }}
                </button>
              </th>
              <td>
                <strong>{{ student.points }}</strong>
              </td>
              <td>{{ student.solved }} / {{ student.assigned }}</td>
              <td>{{ student.unsolved }}</td>
              <td>{{ student.attempts }}</td>
              <td
                v-for="task in student.tasks"
                :key="task.task_id"
                class="matrix-cell"
              >
                <button
                  :class="['matrix-value', task.state]"
                  :aria-label="`${student.name}: ${task.title}, ${stateLabel(task.state)}, посылок ${task.attempts}`"
                  @click="
                    $emit('open-student', {
                      studentId: student.user_id,
                      taskId: task.task_id,
                    })
                  "
                >
                  <span>{{
                    task.state === 'solved'
                      ? '✓'
                      : task.state === 'not_assigned'
                        ? '—'
                        : task.pending
                          ? '…'
                          : '×'
                  }}</span
                  ><small v-if="task.attempts">{{ task.attempts }}</small>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="empty-state">
        {{
          query
            ? 'По запросу никого не найдено.'
            : 'Ученики появятся после входа по инвайту, даже если ещё не отправили решения.'
        }}
      </p>
      <div class="matrix-legend">
        <span><b class="text-success">✓</b> Решена</span
        ><span><b class="text-danger">×</b> Выдана, не решена</span
        ><span>… Проверяется</span><span>— Не выдавалась</span
        ><span>Число в ячейке — посылки</span>
      </div>
    </template>
  </section>
</template>
<script setup>
import { computed, ref } from 'vue'
import { useReport } from '../../composables/useReport'
const props = defineProps({
  battleId: { type: String, required: true },
  refreshKey: Number,
})
defineEmits(['open-student'])
const { data, loading, error, reload } = useReport(
  () => `/battles/${props.battleId}/statistics`,
  () => props.refreshKey,
)
const query = ref('')
const rows = computed(() =>
  (data.value?.students || []).filter((s) =>
    s.name.toLocaleLowerCase().includes(query.value.toLocaleLowerCase()),
  ),
)
const stateLabel = (state) =>
  ({
    solved: 'решена',
    attempted: 'не решена',
    unattempted: 'нет посылок',
    not_assigned: 'не выдавалась',
  })[state]
</script>
