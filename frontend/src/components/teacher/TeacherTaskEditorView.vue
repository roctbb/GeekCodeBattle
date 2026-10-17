<template>
  <section class="card teacher-task-editor" @keydown="keyboardSave">
    <div class="card-body">
      <header class="task-editor-heading">
        <div><button class="back-link" @click="$emit('back')"><AppIcon name="arrow-left" />{{ packageName }}</button><h1 class="page-title mb-0">Редактор задачи</h1></div>
        <button v-if="hasTask" class="btn btn-primary save-task" :disabled="!canSave" @click="$emit('save')" title="Сохранить · Ctrl/Cmd+S"><AppIcon name="save" />{{ saving ? 'Сохраняем…' : 'Сохранить задачу' }}</button>
      </header>
      <template v-if="hasTask">
        <section class="task-metadata" aria-label="Параметры задачи">
          <div class="task-name"><label class="form-label" for="task-title">Название</label><input id="task-title" class="form-control" v-model="packageTaskForm.title" /></div>
          <div><label class="form-label" for="task-difficulty">Сложность</label><select id="task-difficulty" class="form-select" v-model="packageTaskForm.difficulty"><option value="easy">Лёгкая</option><option value="medium">Средняя</option><option value="hard">Сложная</option></select></div>
          <div><label class="form-label" for="task-check">Проверка</label><select id="task-check" class="form-select" v-model="packageTaskForm.check_type"><option value="tests">По тестам</option><option value="gpt">Нейросетью</option></select></div>
        </section>
        <div class="staff-segments mobile-statement-tabs" role="group" aria-label="Вид условия"><button :aria-pressed="mobilePanel === 'edit'" @click="mobilePanel = 'edit'">Условие</button><button :aria-pressed="mobilePanel === 'preview'" @click="mobilePanel = 'preview'">Предпросмотр</button></div>
        <div class="task-editor-grid" :class="`mobile-${mobilePanel}`">
          <section class="statement-panel statement-source" aria-label="Редактор условия">
            <header><label for="task-statement">Условие</label><small>Markdown</small></header>
            <textarea id="task-statement" class="form-control" v-model="packageTaskForm.statement_md" spellcheck="false" placeholder="Опишите задачу, формат ввода и вывода…"></textarea>
          </section>
          <section class="statement-panel statement-preview" aria-label="Предпросмотр условия">
            <header><h2>Предпросмотр</h2><small>Вид для ученика</small></header>
            <div class="statement-preview-body" tabindex="0"><MarkdownText :source="packageTaskForm.statement_md || 'Добавьте условие задачи.'" /></div>
          </section>
        </div>
        <section class="task-tests" aria-label="Тесты задачи">
          <header class="staff-section-heading"><div><h2 class="h6 mb-1">Тесты <span class="text-muted">{{ testsError ? '' : tests.length }}</span></h2></div><div class="task-test-actions"><button class="text-action" :aria-pressed="raw" @click="raw = !raw">{{ raw ? 'К списку тестов' : 'JSON' }}</button><button class="btn btn-sm btn-outline-secondary" :disabled="Boolean(testsError)" @click="addTest"><AppIcon name="plus" />Добавить тест</button></div></header>
          <template v-if="raw"><label class="visually-hidden" for="task-tests-json">Тесты JSON</label><textarea id="task-tests-json" class="form-control code-like" v-model="packageTaskForm.tests_json" rows="12" spellcheck="false"></textarea></template>
          <template v-else>
            <div v-if="tests.length" class="test-case-list">
              <details v-for="item in pagedTests" :key="item.index" class="test-case" :open="activeTest === item.index" @toggle="onTestToggle($event, item.index)">
                <summary><AppIcon name="chevron-right" /><strong>Тест {{ item.index + 1 }}</strong><small>{{ item.test.hidden ? 'Скрытый' : 'Виден ученику' }}</small></summary>
                <div class="test-case-body"><div class="test-editor-row"><div><label class="form-label" :for="`input-${item.index}`">Ввод</label><textarea :id="`input-${item.index}`" class="form-control code-like" rows="3" :value="item.test.input" @input="updateTest(item.index, 'input', $event.target.value)"></textarea></div><div><label class="form-label" :for="`expected-${item.index}`">Ожидаемый вывод</label><textarea :id="`expected-${item.index}`" class="form-control code-like" rows="3" :value="item.test.expected" @input="updateTest(item.index, 'expected', $event.target.value)"></textarea></div></div><button class="text-action text-danger remove-test" :aria-label="`Удалить тест ${item.index + 1}`" @click="removeTest(item.index)"><AppIcon name="trash" />Удалить тест</button></div>
              </details>
            </div>
            <p v-else class="empty-state">Добавьте первый тест: входные данные и ожидаемый ответ.</p>
            <nav v-if="tests.length > pageSize" class="test-pagination" aria-label="Страницы тестов"><span>{{ shownPage * pageSize + 1 }}–{{ Math.min((shownPage + 1) * pageSize, tests.length) }} из {{ tests.length }}</span><button class="btn btn-sm btn-outline-secondary" :disabled="shownPage === 0" aria-label="Предыдущие тесты" @click="changePage(-1)"><AppIcon name="arrow-left" /></button><button class="btn btn-sm btn-outline-secondary" :disabled="(shownPage + 1) * pageSize >= tests.length" aria-label="Следующие тесты" @click="changePage(1)"><AppIcon name="arrow-right" /></button></nav>
          </template>
          <p v-if="testsError" class="text-danger small mt-3" role="alert">{{ testsError }}</p>
        </section>
        <details class="task-removal"><summary>Дополнительно</summary><button class="btn btn-sm btn-outline-danger mt-3" @click="$emit('remove')"><AppIcon name="trash" />Удалить задачу из пакета</button></details>
      </template>
      <p v-else class="text-muted mb-0">Задача не найдена в пакете.</p>
    </div>
  </section>
</template>
<script setup>
import AppIcon from '../AppIcon.vue'
import { computed, nextTick, ref, watch } from 'vue'
import MarkdownText from '../MarkdownText.vue'
const props = defineProps({ hasTask: Boolean, packageName: String, saving: Boolean, packageTaskForm: { type:Object, required:true } })
const emit = defineEmits(['back', 'save', 'remove'])
const raw = ref(false), mobilePanel = ref('edit'), page = ref(0), activeTest = ref(0), pageSize = 6
const testsError = computed(() => {
  try {
    const rows = JSON.parse(props.packageTaskForm.tests_json || '[]')
    if (!Array.isArray(rows) || rows.some(t => !t || typeof t !== 'object' || !('input' in t) || !('expected' in t))) return 'У каждого теста должны быть поля input и expected.'
    return ''
  } catch { return 'Некорректный JSON тестов.' }
})
const tests = computed(() => testsError.value ? [] : JSON.parse(props.packageTaskForm.tests_json || '[]'))
const canSave = computed(() => !props.saving && !testsError.value && Boolean(props.packageTaskForm.title.trim() && props.packageTaskForm.statement_md.trim()))
const shownPage = computed(() => Math.min(page.value, Math.max(0, Math.ceil(tests.value.length / pageSize) - 1)))
const pagedTests = computed(() => tests.value.slice(shownPage.value * pageSize, (shownPage.value + 1) * pageSize).map((test, index) => ({ test, index:shownPage.value * pageSize + index })))
watch(testsError, value => { if (value) raw.value = true }, { immediate:true })
function changePage(direction) { page.value = shownPage.value + direction; activeTest.value = page.value * pageSize }
function onTestToggle(event, index) { if (event.target.open) activeTest.value = index; else if (activeTest.value === index) activeTest.value = -1 }
function saveTests(rows) { props.packageTaskForm.tests_json = JSON.stringify(rows, null, 2) }
function updateTest(index, key, value) { saveTests(tests.value.map((t,i) => i === index ? { ...t, [key]:value } : t)) }
function removeTest(index) { saveTests(tests.value.filter((_,i) => i !== index)); activeTest.value = Math.min(index, tests.value.length - 1) }
async function addTest() { const index = tests.value.length; saveTests([...tests.value, { input:'', expected:'' }]); raw.value = false; page.value = Math.floor(index / pageSize); activeTest.value = index; await nextTick(); document.getElementById(`input-${index}`)?.focus() }
function keyboardSave(event) { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') { event.preventDefault(); if (canSave.value) emit('save') } }
</script>
<style scoped>
.task-editor-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:24px; flex-wrap:wrap; margin-bottom:32px; }
.task-editor-heading > div { min-width:0; }
.back-link { display:inline-flex; align-items:center; gap:8px; border:0; padding:0; margin-bottom:12px; background:none; color:var(--app-muted); font-size:12px; text-align:left; }
.task-editor-heading h1 { font-size:26px; line-height:1.3; }
.task-metadata { display:grid; grid-template-columns:minmax(0,2fr) repeat(2,minmax(0,1fr)); gap:20px; margin-bottom:24px; }
.form-label { font-size:12px; color:var(--app-muted); margin-bottom:8px; }
.task-editor-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:20px; }
.statement-panel { display:flex; flex-direction:column; min-width:0; height:clamp(360px,56dvh,600px); border:1px solid var(--app-border); border-radius:8px; overflow:hidden; background:var(--app-field); }
.statement-panel > header { display:flex; align-items:center; justify-content:space-between; gap:12px; min-height:46px; padding:12px 16px; border-bottom:1px solid var(--app-border); background:var(--app-card); }
.statement-panel > header :is(label,h2) { font-size:12px; font-weight:600; line-height:1.4; margin:0; }
.statement-panel > header small { font-size:11px; color:var(--app-muted); }
.statement-source textarea { flex:1; min-height:0; width:100%; resize:none; border:0; border-radius:0; padding:16px; font-size:13px; line-height:1.7; }
.statement-source:focus-within { border-color:var(--app-brand); box-shadow:0 0 0 2px var(--app-focus-ring); }
.statement-source textarea:focus { border:0; box-shadow:none; outline:0; }
.statement-preview-body { flex:1; overflow:auto; min-height:0; padding:16px; font-size:13px; background:var(--app-card); }
.statement-preview-body :deep(.markdown-text h1), .statement-preview-body :deep(.markdown-text h2) { font-size:17px; }
.task-tests { margin-top:32px; padding-top:24px; border-top:1px solid var(--app-border); }
.task-tests h2 span { margin-left:8px; font-weight:400; font-variant-numeric:tabular-nums; }
.task-test-actions { display:flex; align-items:center; gap:20px; }
.test-case-list { border:1px solid var(--app-border); border-radius:8px; overflow:hidden; }
.test-case + .test-case { border-top:1px solid var(--app-border); }
.test-case > summary { display:flex; align-items:center; gap:12px; padding:14px 16px; cursor:pointer; list-style:none; font-size:12px; }
.test-case > summary::-webkit-details-marker { display:none; }
.test-case > summary .app-icon { color:var(--app-muted); width:8px; transition:transform 120ms; }
.test-case[open] > summary .app-icon { transform:rotate(90deg); }
.test-case > summary strong { font-weight:500; }
.test-case > summary small { color:var(--app-muted); margin-left:auto; }
.test-case-body { padding:4px 16px 16px; }
.test-editor-row { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:20px; }
.test-editor-row textarea { font-size:12px; }
.remove-test { margin-top:12px; font-size:11px; }
.test-pagination { display:flex; align-items:center; justify-content:flex-end; gap:8px; margin-top:16px; }
.test-pagination > span { margin-right:8px; color:var(--app-muted); font-size:12px; font-variant-numeric:tabular-nums; }
.task-removal { margin-top:28px; padding-top:20px; border-top:1px solid var(--app-border); font-size:12px; color:var(--app-muted); }
.task-removal summary { cursor:pointer; }
.mobile-statement-tabs { display:none; }
@media(max-width:850px) { .task-editor-grid { grid-template-columns:1fr; }.mobile-statement-tabs { display:inline-flex; margin-bottom:12px; }.mobile-edit .statement-preview, .mobile-preview .statement-source { display:none; } }
@media(max-width:600px) { .task-metadata { grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }.task-name { grid-column:1/-1; }.task-editor-heading { margin-bottom:24px; gap:20px; }.save-task { width:100%; }.task-editor-heading h1 { font-size:22px; }.test-editor-row { grid-template-columns:1fr; gap:12px; }.task-test-actions { gap:12px; } }
</style>
