<template>
  <section class="card mb-4 battles-hero-card">
    <div class="card-body battle-list-heading">
      <div>
        <p class="hero-eyebrow">Панель батлов</p>
        <h2 class="page-title">Сражения <span class="battle-count" :aria-label="`Всего батлов: ${battles.length}`">{{ battles.length }}</span></h2>
        <p class="text-muted small mb-0">Управляйте раундами, лобби и подключёнными пакетами задач.</p>
      </div>

      <button class="btn btn-primary action-btn" title="Добавить сражение" aria-label="Добавить сражение" @click="$emit('toggle-create')">
        <AppIcon :name="showCreateBattleForm ? 'close' : 'plus'" />
        <span>{{ showCreateBattleForm ? 'Скрыть форму' : 'Новый батл' }}</span>
      </button>
    </div>

    <div class="hero-stats" v-if="battles.length">
      <span>Черновики <strong>{{ draftCount }}</strong></span>
      <span>В процессе <strong>{{ activeCount }}</strong></span>
      <span>Прошедшие <strong>{{ finishedCount }}</strong></span>
    </div>
  </section>

  <section class="card mb-4" v-if="showCreateBattleForm">
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

  <section class="card">
    <div class="card-body">
      <div class="battle-list-toolbar">
        <h3 class="h6 mb-0">Список сражений</h3>
        <div class="btn-group btn-group-sm" role="group" aria-label="Период батлов"><button class="btn" :class="filter === 'current' ? 'btn-primary' : 'btn-outline-primary'" @click="filter='current'">Текущие</button><button class="btn" :class="filter === 'past' ? 'btn-primary' : 'btn-outline-primary'" @click="filter='past'">Прошедшие</button><button class="btn" :class="filter === 'all' ? 'btn-primary' : 'btn-outline-primary'" @click="filter='all'">Все</button></div>
      </div>

      <div class="battle-grid" v-if="filteredBattles.length">
        <article class="battle-tile" v-for="b in filteredBattles" :key="b.id">
          <div class="battle-tile-heading">
            <div class="battle-tile-title">
              <h4 class="h6 mb-2">{{ b.title }}</h4>
              <small class="status-chip" :class="`status-${b.status}`">{{ battleStatus(b.status) }}</small>
            </div>
            <span v-if="b.invite_code" class="battle-id">{{ b.invite_code }}</span><span v-else class="battle-no-invite">Без инвайта</span>
          </div>

          <button class="btn btn-outline-primary w-100 action-btn" @click="$emit('open-battle', b.id)">
            <span>{{ ['stopped','finished'].includes(b.status) ? 'Результаты и статистика' : 'Управление и статистика' }}</span>
            <AppIcon name="chevron-right" />
          </button>
        </article>
      </div>

      <div class="empty-state" v-else>
        {{ battles.length ? 'Нет батлов в этом разделе.' : 'Создайте батл, подключите задачи и задайте инвайт для учеников.' }}
      </div>
    </div>
  </section>
</template>

<script setup>
import AppIcon from '../AppIcon.vue'
import { battleStatus } from '../../labels'
import { computed, ref } from 'vue'

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

const filter = ref('current')
const filteredBattles = computed(() => props.battles.filter(b => filter.value === 'all' || (filter.value === 'past' ? ['stopped','finished'].includes(b.status) : !['stopped','finished'].includes(b.status))))

const draftCount = computed(() => (props.battles || []).filter((b) => b?.status === 'draft').length)
const activeCount = computed(() => (props.battles || []).filter((b) => ['running', 'lobby_open'].includes(b?.status)).length)
const finishedCount = computed(() => (props.battles || []).filter((b) => ['stopped', 'finished'].includes(b?.status)).length)
</script>

<style scoped>
.battle-list-heading, .battle-list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}
.battle-list-toolbar { margin-bottom: 1.5rem; }
.battle-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.75rem;
  height: 1.75rem;
  margin-left: .5rem;
  padding: 0 .5rem;
  border-radius: 6px;
  background: var(--app-bg);
  color: var(--app-muted);
  font-size: .875rem;
  font-weight: 600;
  vertical-align: middle;
}
.hero-stats {
  display: flex;
  flex-wrap: wrap;
  gap: .75rem 1.5rem;
  margin: 0 var(--app-panel-padding) var(--app-panel-padding);
  color: var(--app-muted);
  font-size: .8125rem;
}
.hero-stats strong { margin-left: .375rem; color: var(--app-ink); font-variant-numeric: tabular-nums; }
.package-chips { display: flex; flex-wrap: wrap; gap: .5rem; }
.package-chip { border: 1px solid var(--app-border); border-radius: 8px; padding: .5rem .75rem; margin: 0; }
.battle-grid { display: grid; gap: 1rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.battle-tile {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.25rem;
  border: 1px solid var(--app-border);
  border-radius: 10px;
  transition: border-color 140ms ease;
}
.battle-tile:hover { border-color: #a9b8df; }
.battle-tile-heading { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: .75rem; }
.battle-tile-title { flex: 1; min-width: 140px; overflow-wrap: anywhere; }
.battle-tile > .btn { margin-top: auto; justify-content: space-between; text-align: left; }
.battle-id { font-family: ui-monospace, monospace; font-size: .75rem; color: var(--app-muted); background: var(--app-bg); border-radius: 5px; padding: .25rem .5rem; overflow-wrap: anywhere; max-width: 100%; }
.battle-no-invite { font-size: .8125rem; color: var(--app-muted); }
@media (max-width: 767px) {
  .battle-grid { grid-template-columns: 1fr; }
  .battle-list-heading > .btn { width: 100%; }
  .battle-tile { padding: 1rem; }
}
</style>
