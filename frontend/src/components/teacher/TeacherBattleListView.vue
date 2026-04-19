<template>
  <section class="card shadow-sm border-0 mb-3">
    <div class="card-body d-flex flex-wrap align-items-center justify-content-between gap-2">
      <div>
        <h2 class="h5 mb-1">Сражения</h2>
        <p class="text-muted small mb-0">Управляйте раундами, лобби и подключёнными пакетами задач.</p>
      </div>
      <button class="btn btn-primary action-btn" title="Добавить сражение" aria-label="Добавить сражение" @click="$emit('toggle-create')">
        <i class="bi bi-plus-lg" aria-hidden="true"></i>
        <span>Новый батл</span>
      </button>
    </div>
  </section>

  <section class="card shadow-sm border-0 mb-3" v-if="showCreateBattleForm">
    <div class="card-body">
      <h3 class="h6 mb-3">Новое сражение</h3>
      <div class="row g-3 align-items-end elevated-panel">
        <div class="col-12 col-lg-6">
          <label class="form-label">Название</label>
          <input class="form-control" :value="newBattleTitle" @input="$emit('update:new-battle-title', $event.target.value)" placeholder="Например, Весенний батл" />
        </div>
        <div class="col-12 col-lg-3">
          <button class="btn btn-primary w-100" @click="$emit('create-battle')">Создать</button>
        </div>
      </div>

      <div class="mt-3" v-if="taskPackages.length">
        <label class="form-label mb-2">Пакеты задач для нового сражения</label>
        <div class="d-flex flex-wrap gap-2">
          <label class="form-check border rounded px-3 py-2 mb-0" v-for="p in taskPackages" :key="`new-battle-package-${p.id}`">
            <input
              class="form-check-input me-2"
              type="checkbox"
              :checked="newBattlePackageIds.includes(p.id)"
              @change="$emit('toggle-new-battle-package', p.id)"
            />
            <span class="form-check-label">{{ p.name }} <span class="text-muted">({{ p.task_count ?? 0 }})</span></span>
          </label>
        </div>
      </div>
    </div>
  </section>

  <section class="card shadow-sm border-0">
    <div class="card-body">
      <div class="d-flex align-items-center justify-content-between mb-3">
        <h3 class="h6 mb-0">Список сражений</h3>
        <span class="text-muted small">{{ battles.length }}</span>
      </div>

      <div class="list-group battle-list" v-if="battles.length">
        <button
          v-for="b in battles"
          :key="b.id"
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center app-list-item"
          @click="$emit('open-battle', b.id)"
        >
          <span>
            <strong class="d-block">{{ b.title }}</strong>
            <small class="status-chip" :class="`status-${b.status}`">{{ b.status }}</small>
          </span>
          <span class="text-primary small d-flex align-items-center gap-1">Открыть <i class="bi bi-chevron-right" aria-hidden="true"></i></span>
        </button>
      </div>
      <div class="empty-state" v-else>
        Пока нет сражений. Создайте первое, чтобы открыть лобби для учеников.
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  showCreateBattleForm: { type: Boolean, default: false },
  newBattleTitle: { type: String, default: '' },
  newBattlePackageIds: { type: Array, default: () => [] },
  taskPackages: { type: Array, default: () => [] },
  battles: { type: Array, default: () => [] }
})

defineEmits([
  'toggle-create',
  'update:new-battle-title',
  'toggle-new-battle-package',
  'create-battle',
  'open-battle'
])
</script>
