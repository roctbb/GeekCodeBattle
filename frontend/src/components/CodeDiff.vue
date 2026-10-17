<template>
  <div class="code-diff" :aria-label="label">
    <div class="diff-legend">
      <span class="diff-removed">− {{ removedLabel }}</span
      ><span class="diff-added">+ {{ addedLabel }}</span
      ><label
        ><input type="checkbox" v-model="spaces" /> Пробелы и переносы</label
      >
    </div>
    <div
      v-for="(line, index) in lines"
      :key="index"
      class="diff-line"
      :class="line.kind"
    >
      <span aria-hidden="true">{{
        line.kind === 'added' ? '+' : line.kind === 'removed' ? '−' : ' '
      }}</span
      ><code>{{ visible(line) || ' ' }}</code>
    </div>
    <p v-if="!lines.length" class="text-muted small mb-0">Обе версии пустые.</p>
    <p v-if="truncated" class="text-muted small mb-0 p-2">
      Показаны первые 2 000 строк сравнения.
    </p>
  </div>
</template>
<script setup>
import { computed, ref } from 'vue'
import { diffLines } from 'diff'
const props = defineProps({
  before: { type: String, default: '' },
  after: { type: String, default: '' },
  label: { type: String, default: 'Сравнение версий кода' },
  removedLabel: { type: String, default: 'Удалено' },
  addedLabel: { type: String, default: 'Добавлено' },
})
const spaces = ref(false)
const changes = computed(() =>
  diffLines(props.before, props.after, { timeout: 200 }),
)
const allLines = computed(() =>
  (
    changes.value || [
      { removed: true, value: props.before },
      { added: true, value: props.after },
    ]
  ).flatMap((part) => {
    const lines = part.value.split('\n')
    if (lines.at(-1) === '') lines.pop()
    return lines.map((text, index) => ({
      text,
      hasBreak: index < lines.length - 1 || part.value.endsWith('\n'),
      kind: part.added ? 'added' : part.removed ? 'removed' : 'unchanged',
    }))
  }),
)
const lines = computed(() => allLines.value.slice(0, 2000)),
  truncated = computed(() => allLines.value.length > 2000)
const visible = (line) =>
  spaces.value
    ? line.text.replaceAll(' ', '·').replaceAll('\t', '→   ') +
      (line.hasBreak ? '↵' : '')
    : line.text
</script>
<style scoped>
.code-diff {
  border: 1px solid var(--app-border);
  border-radius: 5px;
  overflow: auto;
  max-height: 460px;
}
.diff-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  align-items: center;
  padding: 10px;
  font-size: 12px;
  border-bottom: 1px solid var(--app-border);
  background: var(--app-card);
}
.diff-legend label {
  margin-left: auto;
  display: flex;
  gap: 6px;
  align-items: center;
}
.diff-line {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  font:
    13px/1.7 ui-monospace,
    Consolas,
    monospace;
  padding: 0 8px;
}
.diff-line code {
  color: inherit;
  background: none;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: inherit;
  padding: 0;
}
.added {
  background: #234b344d;
  color: #c2e2ce;
}
.removed {
  background: #62333b4d;
  color: #f0bdc1;
}
.diff-added {
  color: #aad7b9;
}
.diff-removed {
  color: #f0bdc1;
}
.unchanged {
  color: var(--app-muted);
}
</style>
