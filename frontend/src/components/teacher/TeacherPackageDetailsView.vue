<template>
  <section class="card shadow-sm border-0" v-if="selectedTaskPackage">
    <div class="card-body">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <div>
          <h2 class="h5 mb-1">{{ selectedTaskPackage.package.name }}</h2>
          <p class="text-muted mb-0">{{ selectedTaskPackage.package.description || 'Без описания' }}</p>
        </div>
        <div class="d-flex flex-wrap gap-2">
          <button class="btn btn-outline-secondary" @click="$emit('back')">К списку</button>
          <button class="btn btn-primary" title="Добавить задачу" @click="$emit('open-panel', 'create_task_in_package')"><i class="bi bi-plus-lg me-1" aria-hidden="true"></i>Новая задача</button>
          <button class="btn btn-outline-primary" title="Экспорт" @click="$emit('export')"><i class="bi bi-download me-1" aria-hidden="true"></i>Экспорт</button>
          <button class="btn btn-outline-danger" title="Удалить пакет" @click="$emit('delete-package')"><i class="bi bi-trash-fill me-1" aria-hidden="true"></i>Удалить пакет</button>
        </div>
      </div>

      <section class="border rounded p-3 mb-3 elevated-panel" v-if="taskActionPanel === 'create_task_in_package'">
        <h3 class="h6 mb-3">Новая задача</h3>
        <div class="row g-3">
          <div class="col-12 col-md-6">
            <label class="form-label">Название</label>
            <input class="form-control" v-model="packageTaskForm.title" />
          </div>
          <div class="col-12 col-md-3">
            <label class="form-label">Сложность</label>
            <select class="form-select" v-model="packageTaskForm.difficulty">
              <option value="easy">easy</option>
              <option value="medium">medium</option>
              <option value="hard">hard</option>
            </select>
          </div>
          <div class="col-12 col-md-3">
            <label class="form-label">Проверка</label>
            <select class="form-select" v-model="packageTaskForm.check_type">
              <option value="tests">tests</option>
              <option value="gpt">gpt</option>
            </select>
          </div>
          <div class="col-12">
            <label class="form-label">Условие</label>
            <textarea class="form-control" v-model="packageTaskForm.statement_md" rows="5"></textarea>
          </div>
          <div class="col-12">
            <label class="form-label">Тесты (JSON массив)</label>
            <textarea class="form-control" v-model="packageTaskForm.tests_json" rows="5"></textarea>
            <div class="form-text">Поддерживается JSON-массив тест-кейсов.</div>
          </div>
          <div class="col-12 d-flex gap-2">
            <button class="btn btn-primary" @click="$emit('create-task')">Добавить</button>
            <button class="btn btn-outline-secondary" @click="$emit('close-panel')">Скрыть</button>
          </div>
        </div>
      </section>

      <div class="d-flex align-items-center justify-content-between mb-3">
        <h3 class="h6 mb-0">Задачи пакета</h3>
        <span class="text-muted small">{{ selectedTaskPackage.tasks.length }}</span>
      </div>
      <div class="list-group" v-if="selectedTaskPackage.tasks.length">
        <button
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center app-list-item"
          v-for="t in selectedTaskPackage.tasks"
          :key="t.id"
          @click="$emit('open-task', t)"
        >
          <span>
            <strong class="d-block">{{ t.title }}</strong>
            <small class="text-muted d-flex align-items-center gap-2">
              <span class="status-chip" :class="`difficulty-${t.difficulty}`">{{ t.difficulty }}</span>
              <span>{{ t.check_type }}</span>
            </small>
          </span>
          <span class="text-primary small d-flex align-items-center gap-1">Открыть <i class="bi bi-chevron-right" aria-hidden="true"></i></span>
        </button>
      </div>
      <div class="empty-state" v-else>
        В пакете пока нет задач. Нажмите «Новая задача», чтобы добавить первую.
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  selectedTaskPackage: { type: Object, default: null },
  taskActionPanel: { type: String, default: null },
  packageTaskForm: { type: Object, required: true }
})

defineEmits(['back', 'open-panel', 'close-panel', 'export', 'delete-package', 'create-task', 'open-task'])
</script>
