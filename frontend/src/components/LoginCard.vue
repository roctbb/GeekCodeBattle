<template>
  <section class="card shadow-sm border-0 login-card">
    <div class="card-body p-4">
      <h2 class="h4 mb-2">Вход</h2>

      <template v-if="devLoginEnabled">
        <p class="text-muted mb-3">Тестовый вход (доступен только в dev-режиме).</p>
        <div class="d-flex flex-wrap gap-2 mb-3">
          <span class="badge role-hint">student</span>
          <span class="badge role-hint">teacher</span>
          <span class="badge role-hint">admin</span>
        </div>
        <div class="row g-3 mb-3">
          <div class="col-12 col-md-4">
            <label class="form-label">Имя</label>
            <input class="form-control" v-model="loginForm.name" placeholder="Например, Мария" autocomplete="name" />
          </div>
          <div class="col-12 col-md-4">
            <label class="form-label">External ID</label>
            <input class="form-control" v-model="loginForm.external_id" placeholder="student-1" autocapitalize="none" autocomplete="username" spellcheck="false" />
          </div>
          <div class="col-12 col-md-4">
            <label class="form-label">Роль</label>
            <select class="form-select" v-model="loginForm.role">
              <option value="student">student</option>
              <option value="teacher">teacher</option>
              <option value="admin">admin</option>
            </select>
          </div>
        </div>
        <button class="btn btn-outline-secondary" @click="$emit('dev-login')">Тестовый вход</button>
      </template>
      <p class="text-muted mb-0" v-else>Перенаправляем в GeekClass для входа...</p>
    </div>
  </section>
</template>

<script setup>
defineProps({
  loginForm: { type: Object, required: true },
  devLoginEnabled: { type: Boolean, default: false }
})

defineEmits(['dev-login'])
</script>

<style scoped>
.login-card {
  max-width: 920px;
  margin: 0 auto;
}

.role-hint {
  background: rgba(43, 95, 255, 0.1);
  color: #1f4ae0;
  border: 1px solid rgba(43, 95, 255, 0.2);
  font-weight: 600;
}
</style>
