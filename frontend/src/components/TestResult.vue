<template>
  <article class="test-result" :class="{ 'test-passed': test.passed === true, 'test-failed': test.passed === false }">
    <div class="test-result-heading">
      <span class="test-indicator" aria-hidden="true">{{ pending ? '…' : test.passed === true ? '✓' : test.passed === false ? '×' : '·' }}</span>
      <strong>{{ custom ? 'Вывод программы' : `Пример ${index + 1}` }}</strong>
      <span class="test-status">{{ pending ? 'Проверяется' : test.passed === true ? 'Пройден' : test.passed === false ? 'Ошибка' : 'Нет оценки' }}</span>
    </div>
    <pre v-if="custom" class="run-output">{{ test.actual ?? (pending ? 'Ожидаем результат…' : 'Проверяющая система не вернула вывод.') }}</pre>
    <details v-else-if="!pending" :open="test.passed === false" class="test-output-details">
      <summary>{{ test.passed === false ? 'Разобрать ошибку' : 'Ввод и вывод' }}</summary>
      <CodeDiff v-if="test.passed !== true && test.actual != null && test.expected != null"
        :before="test.expected" :after="test.actual" label="Ожидаемый и фактический вывод"
        removed-label="Ожидалось" added-label="Получено" />
      <label v-else-if="test.actual != null">Вывод<pre>{{ test.actual || '(пусто)' }}</pre></label>
      <p v-else class="text-muted mb-0">Проверяющая система не вернула вывод.</p>
      <label>Ввод<pre>{{ test.input || '(пусто)' }}</pre></label>
    </details>
  </article>
</template>
<script setup>
import CodeDiff from './CodeDiff.vue'
defineProps({ test: { type: Object, required: true }, index: { type: Number, default: 0 }, pending: Boolean, custom: Boolean })
</script>
<style scoped>
.test-result { margin-top: 8px; border: 1px solid var(--app-border); border-radius: 4px; font-size: 13px; }
.test-result-heading { display:flex; align-items:center; gap:9px; padding:10px 12px; }
.test-result-heading strong { font-size:13px; font-weight:500; }
.test-indicator { font-size:16px; line-height:1; color:var(--app-muted); }
.test-status { margin-left:auto; color:var(--app-muted); font-size:12px; }
.test-passed { border-color:var(--app-success-border); background:var(--app-success-bg); }
.test-passed .test-indicator, .test-passed .test-status { color:var(--app-success); }
.test-failed { border-color:var(--app-danger-border); }
.test-failed .test-indicator, .test-failed .test-status { color:var(--app-danger); }
.test-output-details { padding:0 12px 10px; }
.test-output-details summary { cursor:pointer; color:var(--app-muted); font-size:12px; }
.test-output-details label { display:block; color:var(--app-muted); margin:12px 0; font-size:12px; }
pre { margin:6px 0 0; padding:10px; background:var(--app-bg); color:var(--app-ink); font-size:13px; white-space:pre-wrap; overflow-wrap:anywhere; }
.run-output { margin:0 12px 12px; }
</style>
