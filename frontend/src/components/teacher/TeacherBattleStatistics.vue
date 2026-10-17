<template>
  <section aria-label="Статистика учеников">
    <div v-if="error" class="notice notice-warning mb-3" role="alert">{{ error }} <button class="btn btn-sm btn-outline-secondary" @click="reload">Повторить</button></div>
    <p v-if="loading" role="status">Загружаем статистику…</p>
    <template v-if="data">
      <div class="report-metrics mb-4">
        <article><span>Участников</span><strong>{{ data.summary.participants }}</strong></article>
        <article><span>Задач</span><strong>{{ data.summary.tasks }}</strong></article>
        <article><span>Решено учениками</span><strong>{{ data.summary.solved }}</strong></article>
        <article><span>Посылок</span><strong>{{ data.summary.attempts }}</strong><small v-if="data.summary.pending">{{ data.summary.pending }} проверяются</small></article>
      </div>
      <div class="staff-section-heading mb-3">
        <div class="staff-segments" role="group" aria-label="Вид статистики">
          <button :aria-pressed="mode === 'summary'" @click="mode = 'summary'">Сводка</button>
          <button :aria-pressed="mode === 'tasks'" @click="mode = 'tasks'">По задачам</button>
        </div>
        <div class="statistics-search">
          <input v-if="mode === 'tasks'" v-model="taskQuery" class="form-control staff-search" aria-label="Поиск задачи" placeholder="Найти задачу" type="search" />
          <input v-model="query" class="form-control staff-search" aria-label="Поиск ученика" placeholder="Найти ученика" type="search" />
        </div>
      </div>
      <p class="text-muted small">{{ mode === 'tasks' ? 'Нажмите на ячейку, чтобы открыть посылки по задаче.' : 'Нажмите на имя ученика, чтобы открыть его решения.' }}</p>
      <div v-if="rows.length && (mode === 'summary' || shownTasks.length)" class="table-responsive staff-table-wrap matrix-scroll">
        <table class="table report-table staff-table matrix-table mb-0">
          <thead><tr><th class="matrix-name">Ученик</th><th>Очки</th><th>Решено</th><th>Посылки</th><template v-if="mode === 'tasks'"><th v-for="task in shownTasks" :key="task.id"><span :title="task.title">{{ task.number }}. {{ task.title }}</span></th></template></tr></thead>
          <tbody>
            <tr v-for="student in rows" :key="student.user_id">
              <th class="matrix-name"><button class="student-link" @click="$emit('open-student', { studentId:student.user_id })"><small class="text-muted me-2">{{ student.place }}</small>{{ student.name }}</button></th>
              <td class="tabular"><strong>{{ student.points }}</strong></td><td class="tabular">{{ student.solved }} / {{ student.assigned }}</td><td class="tabular">{{ student.attempts }}</td>
              <template v-if="mode === 'tasks'">
                <td v-for="task in student.visibleTasks" :key="task.task_id" class="matrix-cell">
                  <button :class="['matrix-value', task.state]" :aria-label="`${student.name}: ${task.title}, ${stateLabel(task.state)}, посылок ${task.attempts}`" @click="$emit('open-student', { studentId:student.user_id, taskId:task.task_id })">
                    <span>{{ task.state === 'solved' ? '✓' : task.state === 'not_assigned' ? '—' : task.pending ? '…' : '×' }}</span><small v-if="task.attempts">{{ task.attempts }}</small>
                  </button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="empty-state">{{ !rows.length ? (query ? 'По запросу никого не найдено.' : 'Ученики появятся после входа по инвайту.') : 'По запросу задач не найдено.' }}</p>
      <div v-if="mode === 'tasks'" class="matrix-legend"><span><b class="text-success">✓</b> Решена</span><span><b class="text-danger">×</b> Выдана, не решена</span><span>… Проверяется</span><span>— Не выдавалась</span><span>Число в ячейке — посылки</span></div>
    </template>
  </section>
</template>
<script setup>
import { computed, ref } from 'vue'
import { useReport } from '../../composables/useReport'
const props = defineProps({ battleId: { type:String, required:true }, refreshKey:Number })
defineEmits(['open-student'])
const { data, loading, error, reload } = useReport(() => `/battles/${props.battleId}/statistics`, () => props.refreshKey)
const query = ref(''), taskQuery = ref(''), mode = ref('summary')
const shownTasks = computed(() => (data.value?.tasks || []).map((task, index) => ({ ...task, number:index + 1 })).filter(task => task.title.toLocaleLowerCase('ru-RU').includes(taskQuery.value.trim().toLocaleLowerCase('ru-RU'))))
const rows = computed(() => (data.value?.students || []).filter(student => student.name.toLocaleLowerCase('ru-RU').includes(query.value.trim().toLocaleLowerCase('ru-RU'))).map(student => {
  if (mode.value !== 'tasks') return student
  const tasks = new Map(student.tasks.map(task => [task.task_id, task]))
  return { ...student, visibleTasks:shownTasks.value.map(task => tasks.get(task.id) || { task_id:task.id, title:task.title, state:'not_assigned', attempts:0 }) }
}))
const stateLabel = state => ({ solved:'решена', attempted:'не решена', unattempted:'нет посылок', not_assigned:'не выдавалась' })[state] || state
</script>
<style scoped>
.statistics-search { display:flex; flex-wrap:wrap; gap:10px; }
.statistics-search .staff-search { width:210px; }
.matrix-scroll { max-height:65vh; }
@media(max-width:767px) { .statistics-search { width:100%; } .statistics-search .staff-search { flex:1; width:100%; min-width:0; } }
</style>
