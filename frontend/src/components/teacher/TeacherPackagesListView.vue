<template>
  <section class="card shadow-sm border-0">
    <div class="card-body">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <div>
          <h2 class="h5 mb-1">Пакеты задач</h2>
          <p class="text-muted small mb-0">Собирайте тематические наборы и переиспользуйте их в сражениях.</p>
        </div>
        <div class="d-flex flex-wrap gap-2">
          <button class="btn btn-primary" title="Новый пакет" @click="$emit('open-panel', 'create_package')"><i class="bi bi-plus-lg me-1" aria-hidden="true"></i>Новый пакет</button>
        </div>
      </div>

      <section class="border rounded p-3 mb-3 elevated-panel" v-if="taskActionPanel === 'create_package'">
        <h3 class="h6 mb-3">Создать пакет</h3>
        <div class="row g-3">
          <div class="col-12 col-md-6">
            <label class="form-label">Название</label>
            <input class="form-control" v-model="packageForm.name" placeholder="Например, Базовый C++" />
          </div>
          <div class="col-12 col-md-6">
            <label class="form-label">Описание</label>
            <input class="form-control" v-model="packageForm.description" placeholder="Необязательно" />
          </div>
          <div class="col-12">
            <label class="form-label">JSON с задачами (опционально)</label>
            <input class="form-control" type="file" accept="application/json,.json" @change="$emit('file-selected', $event)" />
            <div class="form-text">Можно загрузить export в формате `task-package-v1` — задачи добавятся в новый пакет.</div>
          </div>
          <div class="col-12 d-flex gap-2">
            <button class="btn btn-primary" @click="$emit('create-package')">Создать</button>
            <button class="btn btn-outline-secondary" @click="$emit('close-panel')">Скрыть</button>
          </div>
        </div>
      </section>

      <p class="text-muted" v-if="importSummary">
        Создание{{ importSummary.package?.name ? ` (${importSummary.package.name})` : '' }}:
        создано {{ importSummary.created_ids?.length || 0 }}, ошибок {{ importSummary.errors?.length || 0 }}
      </p>

      <div class="list-group" v-if="taskPackages.length">
        <button
          v-for="p in taskPackages"
          :key="p.id"
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center app-list-item"
          @click="$emit('open-package', p.id)"
        >
          <span>
            <strong class="d-block">{{ p.name }}</strong>
            <small class="text-muted">{{ p.task_count ?? 0 }} задач</small>
          </span>
          <span class="text-primary small d-flex align-items-center gap-1">Открыть <i class="bi bi-chevron-right" aria-hidden="true"></i></span>
        </button>
      </div>
      <div class="empty-state" v-else>
        Пакетов пока нет. Создайте первый пакет и добавьте в него задачи.
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  taskPackages: { type: Array, default: () => [] },
  taskActionPanel: { type: String, default: null },
  packageForm: { type: Object, required: true },
  importSummary: { type: Object, default: null }
})

defineEmits(['open-panel', 'close-panel', 'file-selected', 'create-package', 'open-package'])
</script>
