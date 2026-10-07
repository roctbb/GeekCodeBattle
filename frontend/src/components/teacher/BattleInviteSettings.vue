<template>
  <section class="invite-settings mb-4" aria-label="Инвайт батла">
    <div>
      <h3 class="h6 mb-1">Инвайт для участников</h3>
      <p class="text-muted small mb-0">
        {{
          code
            ? 'Передайте код ученикам. Уже вошедшие сохранят доступ к истории при смене кода.'
            : 'Привяжите код, чтобы открыть лобби и запустить батл.'
        }}
      </p>
    </div>
    <form class="invite-settings-form" @submit.prevent="save(false)">
      <label class="visually-hidden" for="teacher-invite">Инвайт батла</label
      ><input
        id="teacher-invite"
        v-model="draft"
        class="form-control code-like text-uppercase"
        placeholder="PYTHON-7A"
        maxlength="32"
        autocomplete="off"
        :disabled="disabled || saving"
      /><button
        v-if="!disabled"
        class="btn btn-primary"
        :disabled="
          saving || !draft.trim() || draft.trim().toUpperCase() === code
        "
      >
        Сохранить</button
      ><button
        v-if="!disabled"
        type="button"
        class="btn btn-outline-secondary"
        :disabled="saving"
        @click="save(true)"
      >
        Сгенерировать</button
      ><button
        v-if="code"
        type="button"
        class="btn btn-outline-secondary"
        @click="copy"
      >
        {{ copied ? 'Скопировано' : 'Копировать' }}
      </button>
    </form>
    <p v-if="error" class="text-danger small mb-0" role="alert">{{ error }}</p>
    <span class="visually-hidden" role="status">{{ notice }}</span>
  </section>
</template>
<script setup>
import { ref, watch } from 'vue'
import api from '../../api'
const props = defineProps({ battleId: String, code: String, disabled: Boolean })
const emit = defineEmits(['saved'])
const draft = ref(props.code || ''),
  saving = ref(false),
  error = ref(''),
  copied = ref(false),
  notice = ref('')
watch(
  () => props.code,
  (code) => {
    draft.value = code || ''
  },
)
watch(
  () => props.battleId,
  () => {
    draft.value = props.code || ''
    error.value = ''
    copied.value = false
  },
)
async function save(generate) {
  if (saving.value) return
  saving.value = true
  error.value = ''
  try {
    const { data } = await api.put(
      `/battles/${props.battleId}/invite`,
      generate ? { generate: true } : { code: draft.value },
    )
    draft.value = data.invite_code
    notice.value = 'Инвайт сохранён'
    copied.value = false
    emit('saved', data.invite_code)
  } catch (e) {
    error.value =
      e.response?.data?.error?.message || 'Не удалось сохранить инвайт.'
  } finally {
    saving.value = false
  }
}
async function copy() {
  try {
    await navigator.clipboard.writeText(props.code)
    copied.value = true
  } catch {
    error.value = 'Выделите и скопируйте код из поля.'
  }
}
</script>
