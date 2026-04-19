<template>
  <section class="card shadow-sm border-0">
    <div class="card-body">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <div>
          <h2 class="h5 mb-1">Редактор задачи</h2>
          <p class="text-muted mb-0">{{ packageName || 'Пакет' }}</p>
        </div>
        <button class="btn btn-outline-secondary" @click="$emit('back')">К задачам пакета</button>
      </div>

      <div v-if="hasTask" class="row g-3">
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
          <textarea class="form-control editor-textarea" v-model="packageTaskForm.statement_md" rows="6"></textarea>
        </div>
        <div class="col-12">
          <label class="form-label">Тесты (JSON массив)</label>
          <textarea class="form-control editor-textarea code-like" v-model="packageTaskForm.tests_json" rows="8"></textarea>
          <div class="form-text">Формат: массив объектов с входом и ожидаемым результатом.</div>
        </div>
        <div class="col-12 d-flex flex-wrap gap-2">
          <button class="btn btn-primary action-btn" title="Сохранить" @click="$emit('save')">
            <i class="bi bi-check2" aria-hidden="true"></i>
            <span>Сохранить</span>
          </button>
          <button class="btn btn-outline-danger action-btn" title="Удалить" @click="$emit('remove')">
            <i class="bi bi-trash-fill" aria-hidden="true"></i>
            <span>Удалить</span>
          </button>
        </div>
      </div>

      <p class="text-muted mb-0" v-else>Задача не найдена в пакете.</p>
    </div>
  </section>
</template>

<script setup>
defineProps({
  hasTask: { type: Boolean, default: false },
  packageName: { type: String, default: '' },
  packageTaskForm: { type: Object, required: true }
})

defineEmits(['back', 'save', 'remove'])
</script>
