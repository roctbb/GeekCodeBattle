<template>
  <nav class="navbar navbar-expand-lg app-topbar sticky-top">
    <div class="container">
      <a class="navbar-brand fw-semibold app-brand d-flex align-items-center gap-2" href="#" @click.prevent="$emit('go-battles')">
        <span class="brand-dot" aria-hidden="true"></span>
        <span>GeekCodeBattle</span>
      </a>

      <div class="d-flex flex-wrap justify-content-end align-items-center gap-2 ms-auto" v-if="me">
        <div class="btn-group" role="group" v-if="isTeacher">
          <button
            type="button"
            class="btn btn-sm"
            :class="teacherPage === 'battles' ? 'btn-primary' : 'btn-outline-primary'"
            :aria-current="teacherPage === 'battles' ? 'page' : null"
            @click="$emit('go-battles')"
          >
            Сражения
          </button>
          <button
            type="button"
            class="btn btn-sm"
            :class="teacherPage === 'tasks' ? 'btn-primary' : 'btn-outline-primary'"
            :aria-current="teacherPage === 'tasks' ? 'page' : null"
            @click="$emit('go-packages')"
          >
            Пакеты
          </button>
          <button
            type="button"
            class="btn btn-sm"
            :class="teacherPage === 'play' && !resultsActive ? 'btn-primary' : 'btn-outline-primary'"
            :aria-current="teacherPage === 'play' && !resultsActive ? 'page' : null"
            @click="$emit('go-play')"
          >
            Участие
          </button>
        </div>

        <div v-if="!isTeacher" class="btn-group" role="group" aria-label="Навигация ученика"><button class="btn btn-sm" :class="resultsActive ? 'btn-outline-primary' : 'btn-primary'" @click="$emit('go-battles')">Батл</button><button class="btn btn-sm" :class="resultsActive ? 'btn-primary' : 'btn-outline-primary'" @click="$emit('go-results')">Результаты</button></div>
        <button v-else class="btn btn-sm" :class="resultsActive ? 'btn-primary' : 'btn-outline-secondary'" :aria-current="resultsActive ? 'page' : null" @click="$emit('go-results')">Мои результаты</button>
        <span class="text-muted small d-none d-md-inline">{{ me.name }}</span>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="$emit('logout')">Выйти</button>
      </div>
    </div>
  </nav>
</template>

<script setup>
defineProps({
  me: { type: Object, default: null },
  isTeacher: { type: Boolean, default: false },
  resultsActive: Boolean,
  teacherPage: { type: String, default: 'battles' }
})

defineEmits(['go-battles', 'go-packages', 'go-play', 'go-results', 'logout'])
</script>
