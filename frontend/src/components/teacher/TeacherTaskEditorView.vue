<template>
  <section class="card">
    <div class="card-body">
      <header
        class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4"
      >
        <div>
          <p class="text-muted small mb-1">{{ packageName }}</p>
          <h1 class="h4 mb-0">Редактор задачи</h1>
        </div>
        <button class="btn btn-outline-secondary" @click="$emit('back')">
          К задачам
        </button>
      </header>
      <div v-if="hasTask">
        <div class="row g-3 mb-4">
          <div class="col-md-6">
            <label class="form-label" for="task-title">Название</label
            ><input
              id="task-title"
              class="form-control"
              v-model="packageTaskForm.title"
            />
          </div>
          <div class="col-md-3">
            <label class="form-label" for="task-difficulty">Сложность</label
            ><select
              id="task-difficulty"
              class="form-select"
              v-model="packageTaskForm.difficulty"
            >
              <option value="easy">Лёгкая</option>
              <option value="medium">Средняя</option>
              <option value="hard">Сложная</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label" for="task-check">Проверка</label
            ><select
              id="task-check"
              class="form-select"
              v-model="packageTaskForm.check_type"
            >
              <option value="tests">По тестам</option>
              <option value="gpt">Нейросетью</option>
            </select>
          </div>
        </div>
        <div class="task-editor-grid mb-4">
          <div>
            <label class="form-label" for="task-statement"
              >Условие · Markdown</label
            ><textarea
              id="task-statement"
              class="form-control editor-textarea"
              v-model="packageTaskForm.statement_md"
              rows="12"
            ></textarea>
          </div>
          <section aria-label="Предпросмотр условия">
            <h2 class="h6 mb-3">Так увидит ученик</h2>
            <MarkdownText
              :source="
                packageTaskForm.statement_md || 'Добавьте условие задачи.'
              "
            />
          </section>
        </div>
        <div
          class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3"
        >
          <h2 class="h6 mb-0">Тесты</h2>
          <button class="btn btn-sm btn-outline-secondary" @click="raw = !raw">
            {{ raw ? 'Обычный редактор' : 'Редактировать JSON' }}
          </button>
        </div>
        <template v-if="raw"
          ><label class="visually-hidden" for="task-tests">Тесты JSON</label
          ><textarea
            id="task-tests"
            class="form-control code-like mb-3"
            v-model="packageTaskForm.tests_json"
            rows="8"
          ></textarea>
        </template>
        <template v-else
          ><div
            v-for="(test, index) in tests"
            :key="index"
            class="test-editor-row mb-3"
          >
            <div>
              <label class="form-label" :for="`input-${index}`"
                >Ввод {{ index + 1 }}{{ test.hidden ? ' · скрытый тест' : '' }}</label
              ><textarea
                :id="`input-${index}`"
                class="form-control code-like"
                rows="2"
                :value="test.input"
                @input="updateTest(index, 'input', $event.target.value)"
              ></textarea>
            </div>
            <div>
              <label class="form-label" :for="`expected-${index}`"
                >Ожидаемый вывод</label
              ><textarea
                :id="`expected-${index}`"
                class="form-control code-like"
                rows="2"
                :value="test.expected"
                @input="updateTest(index, 'expected', $event.target.value)"
              ></textarea>
            </div>
            <button
              class="btn btn-outline-secondary"
              :aria-label="`Удалить тест ${index + 1}`"
              @click="removeTest(index)"
            >
              <AppIcon name="close" />
            </button>
          </div>
          <button class="btn btn-sm btn-outline-primary mb-3" @click="addTest">
            Добавить тест
          </button></template
        >
        <p v-if="testsError" class="text-danger" role="alert">
          {{ testsError }}
        </p>
        <footer
          class="d-flex justify-content-between align-items-center gap-3 pt-3 border-top"
        >
          <button
            class="btn btn-primary"
            :disabled="
              !!testsError ||
              !packageTaskForm.title.trim() ||
              !packageTaskForm.statement_md.trim()
            "
            @click="$emit('save')"
          >
            Сохранить задачу</button
          ><button class="btn btn-outline-danger" @click="$emit('remove')">
            Удалить
          </button>
        </footer>
      </div>
      <p class="text-muted mb-0" v-else>Задача не найдена в пакете.</p>
    </div>
  </section>
</template>
<script setup>
import AppIcon from '../AppIcon.vue'
import { computed, ref } from 'vue'
import MarkdownText from '../MarkdownText.vue'
const props = defineProps({
  hasTask: Boolean,
  packageName: String,
  packageTaskForm: { type: Object, required: true },
})
defineEmits(['back', 'save', 'remove'])
const raw = ref(false)
const testsError = computed(() => {
  try {
    const rows = JSON.parse(props.packageTaskForm.tests_json || '[]')
    if (
      !Array.isArray(rows) ||
      rows.some(
        (t) =>
          !t || typeof t !== 'object' || !('input' in t) || !('expected' in t),
      )
    )
      return 'У каждого теста должны быть поля input и expected.'
    return ''
  } catch {
    return 'Некорректный JSON тестов.'
  }
})
const tests = computed(() =>
  testsError.value ? [] : JSON.parse(props.packageTaskForm.tests_json || '[]'),
)
function saveTests(rows) {
  props.packageTaskForm.tests_json = JSON.stringify(rows, null, 2)
}
function updateTest(index, key, value) {
  saveTests(
    tests.value.map((t, i) => (i === index ? { ...t, [key]: value } : t)),
  )
}
function removeTest(index) {
  saveTests(tests.value.filter((_, i) => i !== index))
}
function addTest() {
  saveTests([...tests.value, { input: '', expected: '' }])
}
</script>
<style scoped>
.task-editor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}
.task-editor-grid > section {
  padding: 1rem;
  border: 1px solid var(--app-border);
  border-radius: 8px;
  background: var(--app-bg);
}
.test-editor-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 1rem;
  align-items: end;
}
@media (max-width: 760px) {
  .task-editor-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  .test-editor-row {
    grid-template-columns: 1fr;
  }
  .test-editor-row button {
    justify-self: end;
  }
}
</style>
