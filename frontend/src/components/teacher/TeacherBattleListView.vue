<template>
  <section class="card shadow-sm border-0 mb-3 battles-hero-card">
    <div class="card-body d-flex flex-wrap align-items-start justify-content-between gap-3">
      <div>
        <p class="hero-eyebrow mb-1">Панель баттлов</p>
        <h2 class="h4 mb-1">Сражения</h2>
        <p class="text-muted small mb-0">Управляйте раундами, лобби и подключёнными пакетами задач.</p>
      </div>

      <div class="hero-meta ms-auto">
        <div class="hero-count">{{ battles.length }}</div>
        <div class="hero-count-label">всего баттлов</div>
      </div>

      <button class="btn btn-primary action-btn" title="Добавить сражение" aria-label="Добавить сражение" @click="$emit('toggle-create')">
        <i class="bi bi-plus-lg" aria-hidden="true"></i>
        <span>{{ showCreateBattleForm ? 'Скрыть форму' : 'Новый батл' }}</span>
      </button>
    </div>

    <div class="hero-stats" v-if="battles.length">
      <span class="hero-stat-chip">Черновики: {{ draftCount }}</span>
      <span class="hero-stat-chip">В процессе: {{ activeCount }}</span>
      <span class="hero-stat-chip">Завершено: {{ finishedCount }}</span>
    </div>
  </section>

  <section class="card shadow-sm border-0 mb-3" v-if="showCreateBattleForm">
    <div class="card-body">
      <h3 class="h6 mb-3">Новое сражение</h3>
      <div class="create-panel">
        <div class="row g-3 align-items-end">
          <div class="col-12 col-lg-8">
            <label class="form-label">Название</label>
            <input class="form-control" :value="newBattleTitle" @input="$emit('update:new-battle-title', $event.target.value)" placeholder="Например, Весенний батл" />
          </div>
          <div class="col-12 col-lg-4">
            <button class="btn btn-primary w-100" @click="$emit('create-battle')">Создать батл</button>
          </div>
        </div>

        <div class="mt-3" v-if="taskPackages.length">
          <label class="form-label mb-2">Пакеты задач для нового сражения</label>
          <div class="package-chips">
            <label class="form-check package-chip" v-for="p in taskPackages" :key="`new-battle-package-${p.id}`">
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
    </div>
  </section>

  <section class="card shadow-sm border-0">
    <div class="card-body">
      <div class="d-flex align-items-center justify-content-between mb-3">
        <h3 class="h6 mb-0">Список сражений</h3>
        <span class="text-muted small">{{ battles.length }}</span>
      </div>

      <div class="battle-grid" v-if="battles.length">
        <article class="battle-tile" v-for="b in battles" :key="b.id">
          <div class="d-flex justify-content-between align-items-start gap-2 mb-2">
            <div>
              <strong class="d-block mb-1">{{ b.title }}</strong>
              <small class="status-chip" :class="`status-${b.status}`">{{ b.status }}</small>
            </div>
            <span class="battle-id">{{ shortId(b.id) }}</span>
          </div>

          <button class="btn btn-outline-primary btn-sm w-100 action-btn action-btn-sm" @click="$emit('open-battle', b.id)">
            <span>Открыть батл</span>
            <i class="bi bi-chevron-right" aria-hidden="true"></i>
          </button>
        </article>
      </div>

      <div class="empty-state" v-else>
        Пока нет сражений. Создайте первое, чтобы открыть лобби для учеников.
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
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

const draftCount = computed(() => (props.battles || []).filter((b) => b?.status === 'draft').length)
const activeCount = computed(() => (props.battles || []).filter((b) => b?.status === 'running' || b?.status === 'lobby_open' || b?.status === 'stopped').length)
const finishedCount = computed(() => (props.battles || []).filter((b) => b?.status === 'finished').length)

function shortId(id) {
  return String(id || '').slice(0, 8)
}
</script>

<style scoped>
.battles-hero-card {
  overflow: hidden;
}

.hero-eyebrow {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #4d6190;
}

.hero-meta {
  text-align: right;
  padding: 0.4rem 0.7rem;
  border: 1px solid #d8e4fb;
  border-radius: 12px;
  background: linear-gradient(180deg, #fbfdff 0%, #f3f8ff 100%);
}

.hero-count {
  font-size: 1.25rem;
  line-height: 1.1;
  font-weight: 800;
  color: #1d3465;
}

.hero-count-label {
  font-size: 0.74rem;
  color: #62749a;
}

.hero-stats {
  margin: 0 1.2rem 1.1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.hero-stat-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.25rem 0.62rem;
  border: 1px solid #d8e3fb;
  background: #f3f7ff;
  color: #2a4d97;
  font-size: 0.76rem;
  font-weight: 700;
}

.create-panel {
  border: 1px solid #dbe5f8;
  border-radius: 12px;
  background: linear-gradient(180deg, #f9fbff 0%, #f5f9ff 100%);
  padding: 0.9rem;
}

.package-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.package-chip {
  border: 1px solid #d8e4fb;
  border-radius: 999px;
  padding: 0.4rem 0.78rem;
  margin: 0;
  background: #fbfdff;
}

.battle-grid {
  display: grid;
  gap: 0.7rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.battle-tile {
  border: 1px solid #dbe5f9;
  border-radius: 12px;
  background: linear-gradient(180deg, #fbfdff 0%, #f8fbff 100%);
  padding: 0.8rem;
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
}

.battle-tile:hover {
  transform: translateY(-1px);
  border-color: #c6d8fb;
  box-shadow: 0 10px 22px rgba(35, 60, 117, 0.1);
}

.battle-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: #687ba4;
  border: 1px solid #d9e4fb;
  background: #eff4ff;
  border-radius: 999px;
  padding: 0.12rem 0.46rem;
}

@media (max-width: 992px) {
  .battle-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-meta {
    order: 2;
    margin-left: 0;
    text-align: left;
  }

  .battles-hero-card .action-btn {
    width: 100%;
    justify-content: center;
  }

  .hero-stats {
    margin-left: 1rem;
    margin-right: 1rem;
  }
}
</style>
