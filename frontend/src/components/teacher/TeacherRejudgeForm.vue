<template>
  <div class="my-3" v-if="match.finished_at">
    <button
      v-if="!opened"
      class="btn btn-sm btn-outline-secondary"
      @click="open"
    >
      Изменить результат раунда
    </button>
    <form v-else class="elevated-panel" @submit.prevent="save">
      <h4 class="h6">Переоценка раунда</h4>
      <p class="text-muted small">
        Очки, рейтинг и последующие серии будут пересчитаны. Причина изменения
        сохранится в журнале.
      </p>
      <div class="row g-3 mb-3">
        <div v-for="row in rows" :key="row.student_id" class="col-md-6">
          <label class="form-label" :for="`result-${row.student_id}`">{{
            row.name
          }}</label
          ><select
            :id="`result-${row.student_id}`"
            class="form-select"
            v-model="row.result_type"
            :disabled="saving"
          >
            <option value="win">Победа</option>
            <option value="loss">Поражение</option>
            <option value="draw">Ничья</option>
            <option value="no_result">Без результата</option>
          </select>
        </div>
      </div>
      <label class="form-label" :for="`reason-${match.match_id}`"
        >Причина изменения</label
      ><textarea
        :id="`reason-${match.match_id}`"
        class="form-control mb-3"
        v-model="reason"
        required
        :disabled="saving"
        rows="2"
      ></textarea>
      <p v-if="error" role="alert" class="text-danger">{{ error }}</p>
      <div class="d-flex gap-2">
        <button class="btn btn-primary" :disabled="saving || !reason.trim()">
          {{ saving ? 'Пересчитываем…' : 'Сохранить результат' }}</button
        ><button
          type="button"
          class="btn btn-outline-secondary"
          :disabled="saving"
          @click="opened = false"
        >
          Отмена
        </button>
      </div>
    </form>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import api from '../../api'
const props = defineProps({ match: { type: Object, required: true } })
const emit = defineEmits(['saved'])
const opened = ref(false),
  saving = ref(false),
  reason = ref(''),
  rows = ref([]),
  error = ref('')
function open() {
  rows.value = props.match.participants.map((p) => ({
    student_id: p.student.id,
    name: p.student.name,
    result_type: p.result_type || 'no_result',
  }))
  opened.value = true
  error.value = ''
  reason.value = ''
}
async function save() {
  saving.value = true
  error.value = ''
  try {
    await api.post(`/matches/${props.match.match_id}/rejudge`, {
      reason: reason.value,
      new_results: rows.value.map(({ student_id, result_type }) => ({
        student_id,
        result_type,
      })),
    })
    opened.value = false
    emit('saved')
  } catch {
    error.value =
      'Не удалось сохранить переоценку. Проверьте соединение и повторите.'
  } finally {
    saving.value = false
  }
}
</script>
