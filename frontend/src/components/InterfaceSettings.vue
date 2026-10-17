<template>
  <component :is="embedded ? 'div' : 'details'" ref="menu" class="interface-settings" :class="{ embedded }" @keydown.esc="onEscape">
    <summary v-if="!embedded" class="topbar-icon-control" aria-label="Настройки интерфейса" title="Тема, звук и анимации">
      <AppIcon name="settings" />
    </summary>
    <div class="interface-settings-panel">
      <fieldset>
        <legend>Тема оформления</legend>
        <div class="theme-options">
          <label v-for="option in themes" :key="option.value" :class="{ selected: themePreference === option.value }">
            <input type="radio" name="interface-theme" :value="option.value" :checked="themePreference === option.value"
              @change="$emit('update:themePreference', option.value)" />
            <AppIcon :name="option.icon" /><span>{{ option.label }}</span>
          </label>
        </div>
      </fieldset>
      <fieldset class="experience-options">
        <legend>Звук и движение</legend>
        <label><input type="checkbox" :checked="audioEnabled" @change="$emit('toggle-audio')" /> Звуки событий</label>
        <label>Громкость {{ Math.round(audioVolume * 100) }}%
          <input type="range" min="0" max="1" step=".05" :value="audioVolume"
            @input="$emit('update:audioVolume', Number($event.target.value))" />
        </label>
        <label><input type="checkbox" :checked="animationEnabled" @change="$emit('update:animationEnabled', $event.target.checked)" /> Анимации событий</label>
        <small v-if="reducedMotion" class="text-muted">Движение уменьшено настройкой системы.</small>
      </fieldset>
    </div>
  </component>
</template>
<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import AppIcon from './AppIcon.vue'
const props = defineProps({ embedded: Boolean, themePreference: String, audioEnabled: Boolean, audioVolume: Number, animationEnabled: Boolean, reducedMotion: Boolean })
defineEmits(['update:themePreference', 'toggle-audio', 'update:audioVolume', 'update:animationEnabled'])
const themes = [{ value: 'light', label: 'Светлая', icon: 'sun' }, { value: 'dark', label: 'Тёмная', icon: 'moon' }, { value: 'system', label: 'Системная', icon: 'monitor' }]
const menu = ref()
function close(focus) { if (menu.value) { menu.value.open = false; if (focus) menu.value.querySelector('summary')?.focus() } }
function outside(event) { if (!props.embedded && !menu.value?.contains(event.target)) close(false) }
function onEscape(event) { if (!props.embedded) { event.preventDefault(); close(true) } }
onMounted(() => document.addEventListener('pointerdown', outside))
onUnmounted(() => document.removeEventListener('pointerdown', outside))
</script>
<style scoped>
.interface-settings { position:relative; font-size:13px; }
.embedded .interface-settings-panel { position:static; width:auto; padding:12px; border:0; box-shadow:none; }
.interface-settings-panel { position:absolute; z-index:1060; top:calc(100% + 12px); right:0; width:min(300px, calc(100vw - 24px)); padding:20px; border:1px solid var(--app-border); border-radius:10px; background:var(--app-card); color:var(--app-ink); box-shadow:var(--app-popover-shadow); }
fieldset { margin:0; padding:0; border:0; min-width:0; }
legend { float:none; width:auto; font-size:12px; font-weight:700; margin:0 0 12px; }
.theme-options { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:6px; }
.theme-options label { position:relative; display:flex; flex-direction:column; align-items:center; gap:8px; padding:12px 3px; border:1px solid var(--app-border); border-radius:6px; cursor:pointer; font-size:10px; }
.theme-options label.selected { color:var(--app-brand); background:var(--app-brand-soft); border-color:var(--app-brand); }
.theme-options input { position:absolute; opacity:0; width:100%; height:100%; inset:0; cursor:pointer; margin:0; }
.theme-options label:focus-within { outline:2px solid var(--app-brand); outline-offset:2px; }
.theme-options .app-icon { font-size:17px; }
.experience-options { margin-top:20px; padding-top:18px; border-top:1px solid var(--app-border); display:grid; gap:13px; }
.experience-options legend { float:left; width:100%; margin-bottom:2px; }
.experience-options label { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
input[type='range'] { width:100%; accent-color:var(--app-brand); }
input[type='checkbox'] { accent-color:var(--app-brand); }
</style>
