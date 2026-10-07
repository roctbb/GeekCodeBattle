<template>
  <section class="invite-page">
    <div class="invite-intro">
      <p class="eyebrow">GeekCodeBattle</p>
      <h1>Готовы к новому раунду?</h1>
      <p class="text-muted">
        Получите инвайт у преподавателя, войдите в батл и подтвердите готовность
        в лобби.
      </p>
    </div>
    <form class="card invite-card" @submit.prevent="join">
      <div class="card-body p-4">
        <span class="invite-icon" aria-hidden="true"
          ><i class="bi bi-door-open"></i
        ></span>
        <h2 class="h4 mt-3">Войти в батл</h2>
        <label class="form-label text-muted mt-2" for="battle-invite"
          >Инвайт преподавателя</label
        >
        <input
          id="battle-invite"
          v-model="code"
          class="form-control form-control-lg invite-input"
          placeholder="Например, PYTHON-7A"
          maxlength="32"
          autocomplete="off"
          autocapitalize="characters"
          spellcheck="false"
          :disabled="loading"
          aria-describedby="invite-help"
        />
        <p id="invite-help" class="small text-muted mt-2">
          Регистр букв не важен.
        </p>
        <p v-if="error" class="text-danger small" role="alert">{{ error }}</p>
        <button
          class="btn btn-primary w-100 mt-2"
          :disabled="loading || !code.trim()"
        >
          {{ loading ? 'Подключаемся…' : 'Войти в батл' }}
        </button>
      </div>
    </form>
    <RouterLink class="invite-results-link" to="/results"
      ><i class="bi bi-clock-history" aria-hidden="true"></i> Мои результаты и
      решения <i class="bi bi-arrow-right" aria-hidden="true"></i
    ></RouterLink>
  </section>
</template>
<script setup>
import { ref } from 'vue'
import api from '../../api'
const emit = defineEmits(['joined'])
const code = ref(''),
  error = ref(''),
  loading = ref(false)
async function join() {
  if (loading.value || !code.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.post('/battles/join', { code: code.value })
    emit('joined', data)
  } catch (e) {
    error.value =
      e.response?.data?.error?.message ||
      'Не удалось войти. Проверьте соединение и повторите.'
  } finally {
    loading.value = false
  }
}
</script>
<style scoped>
.invite-page {
  max-width: 520px;
  margin: clamp(1rem, 6vh, 4rem) auto;
}
.invite-intro {
  text-align: center;
  margin-bottom: 2rem;
}
.invite-intro h1 {
  font-size: clamp(1.6rem, 3vw, 2.25rem);
  letter-spacing: -0.04em;
}
.invite-intro p {
  line-height: 1.7;
}
.invite-card {
  max-width: 440px;
  margin: auto;
}
.invite-icon {
  display: inline-grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #eef2fc;
  color: var(--app-brand);
  font-size: 1.4rem;
}
.invite-input {
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-family: ui-monospace, monospace;
}
.invite-input::placeholder {
  text-transform: none;
  letter-spacing: 0;
  font-family: inherit;
  font-size: 0.95rem;
}
.invite-results-link {
  display: flex;
  justify-content: center;
  gap: 0.7rem;
  margin-top: 1.8rem;
  font-size: 0.9rem;
  text-decoration: none;
}
</style>
