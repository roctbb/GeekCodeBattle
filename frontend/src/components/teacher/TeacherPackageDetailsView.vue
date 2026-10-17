<template>
  <section class="card" v-if="selectedTaskPackage">
    <div class="card-body">
      <button class="package-back" @click="$emit('back')"><AppIcon name="arrow-left" />Все пакеты</button>
      <div class="catalog-heading">
        <div>

          <h1 class="page-title">{{ selectedTaskPackage.package.name }}</h1>
          <p v-if="selectedTaskPackage.package.description" class="text-muted small mb-0">{{ selectedTaskPackage.package.description }}</p>
        </div>
        <div class="d-flex flex-wrap gap-2">
          <button class="btn btn-primary" title="Добавить задачу" @click="$emit('open-panel', 'create_task_in_package')"><AppIcon name="plus" />Новая задача</button>
          <details class="package-actions"><summary class="btn btn-outline-secondary">Ещё<AppIcon name="chevron-down" /></summary><div><button @click="$emit('export')"><AppIcon name="download" />Экспорт JSON</button><button class="text-danger" @click="$emit('delete-package')"><AppIcon name="trash" />Удалить пакет</button></div></details>
        </div>
      </div>

      <section class="border rounded p-3 mb-3 elevated-panel" v-if="taskActionPanel === 'create_task_in_package'">
        <h3 class="h6 mb-3">Новая задача</h3>
        <div class="row g-3">
          <div class="col-12 col-md-6">
            <label class="form-label" for="new-task-title">Название</label>
            <input id="new-task-title" class="form-control" v-model="packageTaskForm.title" />
          </div>
          <div class="col-12 col-md-3">
            <label class="form-label" for="new-task-difficulty">Сложность</label>
            <select id="new-task-difficulty" class="form-select" v-model="packageTaskForm.difficulty">
              <option value="easy">Лёгкая</option>
              <option value="medium">Средняя</option>
              <option value="hard">Сложная</option>
            </select>
          </div>
          <div class="col-12 col-md-3">
            <label class="form-label" for="new-task-check_type">Проверка</label>
            <select id="new-task-check_type" class="form-select" v-model="packageTaskForm.check_type">
              <option value="tests">По тестам</option>
              <option value="gpt">Нейросетью</option>
            </select>
          </div>
          <div class="col-12">
            <label class="form-label" for="new-task-statement_md">Условие</label>
            <textarea id="new-task-statement_md" class="form-control" v-model="packageTaskForm.statement_md" rows="5"></textarea>
          </div>
          <div class="col-12">
            <label class="form-label" for="new-task-tests_json">Тесты (JSON массив)</label>
            <textarea id="new-task-tests_json" class="form-control" v-model="packageTaskForm.tests_json" rows="5"></textarea>
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
      <div class="list-group catalog-list" v-if="selectedTaskPackage.tasks.length">
        <button
          class="list-group-item list-group-item-action catalog-row"
          v-for="t in selectedTaskPackage.tasks"
          :key="t.id"
          @click="$emit('open-task', t)"
        >
          <span class="catalog-row-content">
            <strong class="catalog-row-title">{{ t.title }}</strong>
            <small class="text-muted d-flex flex-wrap align-items-center gap-2">
              <span class="status-chip" :class="`difficulty-${t.difficulty}`">{{ difficultyLabel(t.difficulty) }}</span>
              <span>{{ t.check_type === 'tests' ? 'Проверка тестами' : 'Проверка ИИ' }}</span>
            </small>
          </span>
          <span class="catalog-row-action"><span>Открыть</span><AppIcon name="chevron-right" /></span>
        </button>
      </div>
      <div class="empty-state" v-else>
        В пакете пока нет задач. Нажмите «Новая задача», чтобы добавить первую.
      </div>
    </div>
  </section>
</template>

<script setup>
import AppIcon from '../AppIcon.vue'
import { difficultyLabel } from '../../labels'
defineProps({
  selectedTaskPackage: { type: Object, default: null },
  taskActionPanel: { type: String, default: null },
  packageTaskForm: { type: Object, required: true }
})

defineEmits(['back', 'open-panel', 'close-panel', 'export', 'delete-package', 'create-task', 'open-task'])
</script>

<style scoped>
.package-back { display:inline-flex; align-items:center; gap:8px; padding:0; margin-bottom:20px; border:0; background:none; color:var(--app-muted); font-size:12px; }
.package-actions { position:relative; }
.package-actions summary { list-style:none; }
.package-actions summary::-webkit-details-marker { display:none; }
.package-actions > div { position:absolute; z-index:10; right:0; top:calc(100% + 8px); width:190px; padding:6px; background:var(--app-card); border:1px solid var(--app-border); border-radius:8px; box-shadow:var(--app-popover-shadow); }
.package-actions button { display:flex; align-items:center; gap:10px; width:100%; padding:12px; border:0; background:transparent; color:var(--app-ink); font-size:12px; text-align:left; }
.package-actions button:hover { background:var(--app-bg-soft); }
</style>
