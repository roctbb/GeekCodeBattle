<template>
  <section>
    <header class="report-page-heading">
      <div>
        <p class="eyebrow">История участия</p>
        <h1>Мои результаты</h1>
        <p class="text-muted mb-0">Батлы, задачи и все отправленные решения.</p>
      </div>
      <RouterLink :to="playPath" class="btn btn-outline-primary"
        >Войти в батл</RouterLink
      >
    </header>
    <div v-if="error" class="notice notice-warning mb-3" role="alert">
      {{ error }}
      <button class="btn btn-sm btn-outline-secondary" @click="reload">
        Повторить
      </button>
    </div>
    <p v-if="loading" role="status">Загружаем результаты…</p>
    <div v-else-if="data?.length" class="card">
      <div class="table-responsive">
        <table class="table report-table mb-0">
          <thead>
            <tr>
              <th>Батл</th>
              <th>Дата</th>
              <th>Решено</th>
              <th>Посылки</th>
              <th>Очки</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in data" :key="row.battle.id">
              <td>
                <strong>{{ row.battle.title }}</strong
                ><span
                  class="status-chip d-table mt-2"
                  :class="`status-${row.battle.status}`"
                  >{{ battleStatus(row.battle.status) }}</span
                >
              </td>
              <td class="small text-muted">
                {{
                  formatDate(
                    row.battle.finished_at ||
                      row.battle.stopped_at ||
                      row.battle.started_at ||
                      row.joined_at,
                  )
                }}
              </td>
              <td>
                {{ row.solved }} / {{ row.assigned
                }}<span class="small text-muted d-block">выданных задач</span>
              </td>
              <td>
                {{ row.attempts
                }}<span v-if="row.pending" class="small text-muted d-block"
                  >{{ row.pending }} проверяются</span
                >
              </td>
              <td>
                <strong>{{ row.points }}</strong
                ><span class="small text-muted d-block"
                  >Рейтинг {{ row.rating_delta >= 0 ? '+' : ''
                  }}{{ row.rating_delta }}</span
                >
              </td>
              <td class="text-end">
                <RouterLink
                  :to="`/results/${row.battle.id}`"
                  class="btn btn-sm btn-outline-primary"
                  >Подробнее</RouterLink
                ><button
                  v-if="['running', 'lobby_open'].includes(row.battle.status)"
                  class="btn btn-sm btn-link d-block ms-auto mt-1"
                  @click="$emit('resume', row.battle.id)"
                >
                  Продолжить
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else-if="!error" class="empty-state text-center p-5">
      <h2 class="h5">Здесь появятся ваши результаты</h2>
      <p class="mb-0">Войдите в первый батл по инвайту преподавателя.</p>
    </div>
  </section>
</template>
<script setup>
import { useReport } from '../../composables/useReport'
import { battleStatus } from '../../labels'
const props = defineProps({
  refreshKey: Number,
  playPath: { type: String, default: '/' },
})
defineEmits(['resume'])
const { data, loading, error, reload } = useReport(
  () => '/me/results',
  () => props.refreshKey,
)
const formatDate = (value) =>
  value
    ? new Date(value).toLocaleString('ru-RU', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    : '—'
</script>
