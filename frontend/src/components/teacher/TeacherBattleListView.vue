<template>
  <section class="card">
    <div class="card-body">
      <header class="staff-section-heading mb-4">
        <h1 class="page-title mb-0">Батлы</h1>
        <button class="btn btn-primary action-btn" :aria-expanded="showCreateBattleForm" aria-controls="create-battle" @click="$emit('toggle-create')"><AppIcon :name="showCreateBattleForm ? 'close' : 'plus'" />{{ showCreateBattleForm ? 'Закрыть' : 'Новый батл' }}</button>
      </header>
      <form v-if="showCreateBattleForm" id="create-battle" class="create-battle" @submit.prevent="$emit('create-battle')">
        <label for="new-battle-title" class="form-label">Название батла</label>
        <div class="create-battle-row">
          <input id="new-battle-title" ref="titleInput" class="form-control" :value="newBattleTitle" @input="$emit('update:new-battle-title', $event.target.value)" placeholder="Например, Циклы · 8А" required />
          <button class="btn btn-primary" :disabled="!newBattleTitle.trim()">Создать</button>
        </div>
        <details v-if="taskPackages.length" class="mt-3">
          <summary>Подключить задачи <span class="text-muted">{{ newBattlePackageIds.length ? `· ${newBattlePackageIds.length}` : '· можно позже' }}</span></summary>
          <div class="package-options mt-3">
            <label v-for="p in taskPackages" :key="p.id"><input type="checkbox" :checked="newBattlePackageIds.includes(p.id)" @change="$emit('toggle-new-battle-package', p.id)" /><span>{{ p.name }} <small class="text-muted">· {{ p.task_count ?? 0 }} задач</small></span></label>
          </div>
        </details>
      </form>
      <div class="staff-section-heading battle-list-toolbar">
        <div class="staff-segments" role="group" aria-label="Период батлов">
          <button v-for="item in filters" :key="item.value" :aria-pressed="filter === item.value" @click="filter = item.value">{{ item.label }} <span>{{ count(item.value) }}</span></button>
        </div>
        <input v-model="query" type="search" class="form-control staff-search" aria-label="Найти батл" placeholder="Название или инвайт" />
      </div>
      <div v-if="filteredBattles.length" class="battle-list">
        <button v-for="b in filteredBattles" :key="b.id" class="battle-row" @click="$emit('open-battle', b.id)">
          <span class="battle-row-name"><strong>{{ b.title }}</strong><small>{{ b.invite_code || 'Инвайт не задан' }}</small></span>
          <span class="status-chip" :class="`status-${b.status}`">{{ battleStatus(b.status) }}</span><AppIcon name="chevron-right" />
        </button>
      </div>
      <p v-else class="empty-state mb-0">{{ query ? 'По запросу ничего не найдено.' : battles.length ? 'В этом разделе пока нет батлов.' : 'Создайте первый батл и подключите задачи.' }}</p>
    </div>
  </section>
</template>
<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import AppIcon from '../AppIcon.vue'
import { battleStatus } from '../../labels'
const props = defineProps({ showCreateBattleForm: Boolean, newBattleTitle: { type:String, default:'' }, newBattlePackageIds: { type:Array, default:()=>[] }, taskPackages: { type:Array, default:()=>[] }, battles: { type:Array, default:()=>[] } })
defineEmits(['toggle-create', 'update:new-battle-title', 'toggle-new-battle-package', 'create-battle', 'open-battle'])
const filter = ref('current'), query = ref(''), titleInput = ref()
const filters = [{ value:'current', label:'Текущие' }, { value:'past', label:'Прошедшие' }, { value:'all', label:'Все' }]
const inPeriod = (battle, period) => period === 'all' || (period === 'past' ? ['stopped','finished'].includes(battle.status) : !['stopped','finished'].includes(battle.status))
const count = period => props.battles.filter(b => inPeriod(b, period)).length
const filteredBattles = computed(() => props.battles.filter(b => inPeriod(b, filter.value) && `${b.title} ${b.invite_code || ''}`.toLocaleLowerCase('ru-RU').includes(query.value.trim().toLocaleLowerCase('ru-RU'))))
watch(() => props.showCreateBattleForm, async shown => { if (shown) { await nextTick(); titleInput.value?.focus() } })
</script>
<style scoped>
.battle-list-toolbar { gap:16px; margin-bottom:20px; }
.battle-list { border:1px solid var(--app-border); border-radius:8px; overflow:hidden; }
.battle-row { display:flex; align-items:center; gap:20px; width:100%; padding:20px; background:transparent; border:0; border-bottom:1px solid var(--app-border); color:var(--app-ink); text-align:left; }
.battle-row:last-child { border-bottom:0; }
.battle-row:hover { background:var(--app-bg-soft); }
.battle-row-name { display:grid; gap:6px; flex:1; min-width:0; overflow-wrap:anywhere; }
.battle-row-name strong { font-size:15px; font-weight:600; }
.battle-row-name small { font-size:11px; color:var(--app-muted); }
.battle-row > .app-icon { width:10px; color:var(--app-muted); flex-shrink:0; }
.create-battle { margin-bottom:24px; padding:20px; background:var(--app-bg-soft); border:1px solid var(--app-border); border-radius:8px; }
.create-battle-row { display:flex; gap:12px; }
.package-options { display:grid; gap:10px; max-height:240px; overflow-y:auto; font-size:13px; }
.package-options label { display:flex; align-items:center; gap:10px; }
.package-options input { accent-color:var(--app-brand); }
.create-battle summary { font-size:12px; }
.staff-segments span { margin-left:4px; opacity:.65; font-variant-numeric:tabular-nums; }
@media(max-width:575px) { .battle-row { padding:16px 12px; gap:10px; } .battle-row-name strong { font-size:13px; } .battle-row .status-chip { font-size:9px; } .staff-segments { width:100%; } .staff-segments button { flex:1; padding:9px 6px; } }
</style>
