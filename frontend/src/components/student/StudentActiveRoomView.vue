<template>
  <section v-if="preparing" class="match-intro" aria-label="Подготовка раунда">
    <p class="hero-eyebrow">{{ activeBattleTitle }} · Соперники найдены</p>
    <h1>Арена готова</h1>
    <div class="match-contenders">
      <article
        v-for="(p, i) in participants"
        :key="p.student_id"
        :class="i % 2 ? 'fighter-ice' : 'fighter-fire'"
      >
        <span class="fighter-monogram">{{ p.name?.[0] }}</span>
        <h2>{{ p.student_id === meId ? 'Вы' : p.name }}</h2>
        <span>{{ p.name }}</span>
      </article>
    </div>
    <div
      class="match-countdown"
      :key="startsIn"
      :class="{ animated: effectsEnabled }"
      aria-live="off"
    >
      {{ startsIn || 'К бою' }}
    </div>
    <p role="status">Задача откроется одновременно для всех после отсчёта.</p>
  </section>
  <section
    v-else
    class="arena"
    :class="{ 'is-fullscreen': fullscreen }"
    aria-label="Текущий раунд"
  >
    <header class="arena-heading">
      <div>
        <p class="hero-eyebrow">{{ activeBattleTitle || 'Текущий раунд' }}</p>
        <h1>{{ task?.title || 'Подготовка задачи' }}</h1>
        <span v-if="fullscreen && !canSubmit" class="focus-connection" role="status">Нет связи · отправка недоступна</span>
      </div>
      <div class="arena-clock">
        <span>Время решения</span
        ><strong>{{ timerText }}</strong>
      </div>
      <div v-if="fullscreen" class="focus-controls">
        <button class="btn btn-sm btn-outline-secondary" :aria-pressed="tab === 'task'"
          @click="tab = tab === 'task' ? 'code' : 'task'">{{ tab === 'task' ? 'К коду' : 'Условие' }}</button>
        <button class="btn btn-sm btn-outline-secondary" title="Свернуть · Esc" @click="fullscreen = false">Свернуть</button>
      </div>
    </header>
    <div class="arena-meta">
      <span class="status-chip" :class="`difficulty-${task?.difficulty}`">{{
        difficultyLabel(task?.difficulty)
      }}</span
      ><span
        v-for="(p, i) in participants"
        :key="p.student_id"
        class="arena-player"
        :class="i % 2 ? 'fighter-ice' : 'fighter-fire'"
        ><span
          class="presence-dot"
          :class="p.is_disconnected ? 'offline' : 'online'"
        ></span
        >{{ p.student_id === meId ? 'Вы' : p.name
        }}<span class="text-muted"
          >·
          {{
            p.accepted_at
              ? 'Решено'
              : p.surrendered_at
                ? 'Сдался'
              : p.is_disconnected
                ? 'Нет связи'
                : 'Решает'
          }}</span
        ></span
      >
    </div>
    <div
      v-if="opponentSurrendered || leader?.winner_student_id"
      class="notice notice-warning mb-3 round-notice"
      role="status"
    >
      <template v-if="opponentSurrendered">Соперник сдался. Решите задачу и получите ещё +{{ round?.surrender_solve_bonus ?? 20 }} очков. Время не ограничено.</template>
      <template v-else>{{ leader.winner_name || 'Соперник' }} решил задачу первым. Можно продолжить решение или сдаться сразу.</template>
    </div>
    <div class="workspace-toolbar">
      <div class="workspace-tabs" role="group" aria-label="Раздел раунда">
        <button :aria-pressed="tab === 'code'" @click="tab = 'code'">
          Решение</button
        ><button :aria-pressed="tab === 'task'" @click="tab = 'task'">
          Условие и примеры
        </button>
      </div>
      <div class="workspace-actions">
        <button
          type="button"
          class="btn btn-sm btn-outline-secondary split-toggle"
          :aria-pressed="split"
          @click="toggleLayout"
        >
          <AppIcon name="columns" />{{
            split ? 'Фокус на коде' : 'Рядом с кодом'
          }}</button
        ><button
          type="button"
          class="btn btn-sm btn-outline-secondary"
          :aria-pressed="fullscreen"
          @click="fullscreen = !fullscreen"
        >
          {{ fullscreen ? 'Свернуть · Esc' : 'На весь экран' }}
        </button>
      </div>
    </div>
    <div
      ref="workspace"
      class="arena-workspace"
      :class="{ 'is-split': split && !fullscreen, 'show-task': tab === 'task' }"
      :style="{
        '--task-width': settings.taskWidth + '%',
        '--console-height': settings.consoleHeight + 'px',
        '--workspace-height': workspaceHeight == null ? undefined : workspaceHeight + 'px',
      }"
    >
      <section class="arena-task" aria-label="Условие задачи">
        <MarkdownText v-if="task" :source="task.statement_md" />
        <p v-else class="text-muted">Загружаем условие…</p>
        <h2 class="h6 mt-4">Примеры</h2>
        <div
          v-for="(test, index) in publicTests"
          :key="index"
          class="example-row"
        >
          <div>
            <span>Ввод {{ index + 1 }}</span>
            <pre>{{ test.input || '(пусто)' }}</pre>
            <button
              type="button"
              class="btn btn-sm btn-link"
              @click="useExample(test.input)"
            >
              В свой ввод
            </button>
          </div>
          <div>
            <span>Вывод</span>
            <pre>{{ test.expected }}</pre>
          </div>
        </div>
        <p v-if="!publicTests.length" class="text-muted small">
          Для этой задачи примеры не указаны.
        </p>
      </section>
      <div
        class="workspace-divider"
        role="separator"
        aria-label="Ширина условия"
        aria-orientation="vertical"
        :aria-valuenow="settings.taskWidth"
        aria-valuemin="22"
        aria-valuemax="55"
        tabindex="0"
        @pointerdown="startResize($event, 'task')"
        @keydown.left.prevent="
          settings.taskWidth = Math.max(22, settings.taskWidth - 2)
        "
        @keydown.right.prevent="
          settings.taskWidth = Math.min(55, settings.taskWidth + 2)
        "
      ></div>
      <section class="arena-solution" aria-label="Редактор решения">
        <div class="editor-toolbar">
          <label for="solution-language"
            >Язык<select
              id="solution-language"
              class="form-select form-select-sm"
              :value="submitLanguage"
              @change="$emit('update:submit-language', $event.target.value)"
            >
              <option value="python">Python</option>
              <option value="cpp">C++</option>
            </select></label
          >
          <div class="editor-actions">
            <button
              type="button"
              class="editor-icon-button"
              title="Отменить · Ctrl/Cmd+Z"
              aria-label="Отменить изменение"
              @click="editor?.undo()"
            >
              ↶</button
            ><button
              type="button"
              class="editor-icon-button"
              title="Повторить · Ctrl/Cmd+Shift+Z"
              aria-label="Повторить изменение"
              @click="editor?.redo()"
            >
              ↷</button
            ><button
              type="button"
              class="editor-icon-button"
              title="Поиск и замена · Ctrl/Cmd+F"
              @click="editor?.find()"
            >
              Поиск
            </button>
            <details class="editor-settings">
              <summary>Настройки</summary>
              <div class="editor-settings-panel">
                <label
                  >Шрифт {{ settings.fontSize }} px<input
                    type="range"
                    min="12"
                    max="24"
                    v-model.number="settings.fontSize" /></label
                ><label
                  >Тема<select
                    v-model="settings.theme"
                    class="form-select form-select-sm"
                  >
                    <option value="system">Как в приложении</option>
                    <option value="dark">Тёмная</option>
                    <option value="light">Светлая</option>
                  </select></label
                ><label
                  >Отступ<select
                    v-model.number="settings.tabSize"
                    class="form-select form-select-sm"
                  >
                    <option :value="2">2 пробела</option>
                    <option :value="4">4 пробела</option>
                    <option :value="8">8 пробелов</option>
                  </select></label
                ><label class="settings-check"
                  ><input type="checkbox" v-model="settings.wrap" />Перенос
                  длинных строк</label
                >
                <p class="small text-muted mb-0">
                  Ctrl/Cmd+Enter — запуск<br />Ctrl/Cmd+Shift+Enter — отправка
                </p>
              </div>
            </details>
          </div>
        </div>
        <SolutionEditor
          ref="editor"
          :identity="`${meId}:${roomId}:${submitLanguage}`"
          :model-value="submitCode"
          :language="submitLanguage"
          :font-size="settings.fontSize"
          :theme="settings.theme === 'system' ? appTheme : settings.theme"
          :tab-size="settings.tabSize"
          :wrap="settings.wrap"
          :diagnostics="editorDiagnostics"
          @update:model-value="$emit('update:submit-code', $event)"
          @cursor="cursor = $event"
          @run="runCode"
          @submit="send"
        />
        <div class="editor-status">
          <span role="status">{{ draftStatus }}</span
          ><span
            >Стр. {{ cursor.line }}, стлб. {{ cursor.column }} · Отступ
            {{ settings.tabSize }}</span
          >
        </div>
        <div
          class="console-divider"
          role="separator"
          aria-label="Высота панели проверки"
          aria-orientation="horizontal"
          :aria-valuenow="settings.consoleHeight"
          aria-valuemin="130"
          aria-valuemax="460"
          tabindex="0"
          @pointerdown="startResize($event, 'console')"
          @keydown.up.prevent="
            settings.consoleHeight = Math.min(460, settings.consoleHeight + 20)
          "
          @keydown.down.prevent="
            settings.consoleHeight = Math.max(130, settings.consoleHeight - 20)
          "
        ></div>
        <section class="arena-console">
          <div class="console-tabs" role="group" aria-label="Панель запуска">
            <button
              :aria-pressed="consoleTab === 'examples'"
              @click="consoleTab = 'examples'"
            >
              Примеры</button
            ><button
              :aria-pressed="consoleTab === 'custom'"
              @click="consoleTab = 'custom'"
            >
              Свой ввод</button
            ><button
              :aria-pressed="consoleTab === 'verdict'"
              @click="consoleTab = 'verdict'"
            >
              Результат посылки</button
            ><RouterLink
              v-if="battleId"
              :to="`/results/${battleId}?task=${task?.id || ''}`"
              >Мои посылки</RouterLink
            >
          </div>
          <div class="console-body" aria-live="polite">
            <template v-if="consoleTab === 'custom'"
              ><label class="small" for="custom-input">Входные данные</label
              ><textarea
                id="custom-input"
                v-model="customInput"
                class="form-control custom-input"
                rows="3"
                spellcheck="false"
                maxlength="65536"
                placeholder="Введите данные для stdin"
              ></textarea>
            </template>
            <p v-if="runError" class="text-danger small" role="alert">
              {{ runError }}
            </p>
            <p v-if="running" class="text-muted small">
              Код выполняется. Можно продолжать редактирование.
            </p>
            <template v-if="consoleTab === 'verdict'"
              ><p v-if="staleSubmission" class="notice notice-warning small">Посылка относится к предыдущей версии кода.</p>
              <p
                :class="
                  mySubmission?.verdict === 'accepted'
                    ? 'text-success'
                    : 'text-muted'
                "
              >
                {{
                  mySubmission
                    ? verdictLabel(mySubmission.verdict)
                    : 'Решение ещё не отправлено'
                }}
              </p>
              <p v-if="mySubmission?.tests_total != null && mySubmission?.tests_passed != null"
                class="submission-test-count">
                Пройдено тестов: {{ mySubmission.tests_passed }} из {{ mySubmission.tests_total }} (включая скрытые)
              </p>
              <pre
                v-if="mySubmission?.checker_message"
                class="checker-feedback"
                >{{ mySubmission.checker_message }}</pre>
              <button
                v-if="errorLine && !staleSubmission"
                type="button"
                class="btn btn-sm btn-outline-secondary mb-2"
                @click="editor?.focusLine(errorLine)"
              >
                К строке {{ errorLine }}
              </button>
              <TestResult v-for="(test, i) in publicTests" :key="`${mySubmission?.id}:${i}`"
                :test="test" :index="i" :pending="mySubmission?.verdict === 'queued'" />
            </template>
            <template
              v-else-if="
                runResult &&
                runResult.kind ===
                  (consoleTab === 'custom' ? 'custom' : 'examples')
              "
              ><p v-if="staleRun" class="notice notice-warning small">
                Результат относится к предыдущей версии кода или входных данных.
              </p>
              <p v-if="runResult.error_type" class="text-danger">{{ verdictLabel(runResult.error_type) }}</p>
              <p v-if="runResult.kind === 'examples' && runResult.tests_total != null && runResult.tests_passed != null"
                class="practice-test-count">Пройдено примеров: {{ runResult.tests_passed }} из {{ runResult.tests_total }}</p>
              <pre v-if="runResult.message" class="checker-feedback">{{
                runResult.message
              }}</pre>
              <button
                v-if="practiceErrorLine && !staleRun"
                type="button"
                class="btn btn-sm btn-outline-secondary mb-2"
                @click="editor?.focusLine(practiceErrorLine)"
              >К строке {{ practiceErrorLine }}</button>
              <TestResult v-for="(test, i) in runResult.tests" :key="`${runResult.id}:${i}`"
                :test="test" :index="i" :pending="running" :custom="runResult.kind === 'custom'" />
            </template>
            <p
              v-else-if="!running && consoleTab === 'examples'"
              class="text-muted small"
            >
              {{
                publicTests.length
                  ? `Публичных примеров: ${publicTests.length}. Запуск не влияет на очки.`
                  : 'Публичных примеров нет. Используйте свой ввод.'
              }}
            </p>
          </div>
        </section>
      </section>
    </div>
    <div class="submit-toolbar">
      <div class="workspace-actions">
        <button
          type="button"
          class="btn btn-outline-secondary run-button"
          :aria-label="runLabel"
          :aria-keyshortcuts="`${shortcutKey}+Enter`"
          :title="`${runLabel} · ${shortcutModifier}+Enter`"
          :disabled="
            running ||
            !canSubmit ||
            !submitCode.trim() ||
            (consoleTab !== 'custom' && !publicTests.length)
          "
          @click="runCode"
        >
          <AppIcon name="play" />{{ runLabel }}<kbd class="shortcut-hint" aria-hidden="true">{{ shortcutModifier }} ↵</kbd></button
        ><button
          v-if="canRestoreDraft"
          type="button"
          class="btn btn-sm btn-link"
          @click="$emit('restore-draft')"
        >
          Вернуть черновик</button
        ><span v-if="opponentActivity?.active" class="text-muted small">{{
          opponentActivity.message
        }}</span>
      </div>
      <div class="workspace-actions round-actions">
        <button
          class="btn btn-outline-secondary surrender-button"
          :disabled="!surrenderUnlocked || !canSubmit"
          :title="surrenderUnlocked ? 'Завершить своё участие в раунде и вернуться в лобби' : 'Сдаться можно через 10 минут или сразу после решения соперника'"
          @click="$emit('surrender')"
        >
          {{ surrenderUnlocked ? 'Сдаться' : `Сдаться через ${formatTime(surrenderRemaining)}` }}</button
        ><button
          class="btn btn-primary send-button"
          :aria-label="isChecking ? 'Проверяется…' : 'Отправить решение'"
          :aria-keyshortcuts="`${shortcutKey}+Shift+Enter`"
          :title="`Отправить решение · ${shortcutModifier}+Shift+Enter`"
          :disabled="isChecking || !canSubmit || !submitCode.trim()"
          @click="send"
        >
          <AppIcon name="send" />{{
            isChecking ? 'Проверяется…' : 'Отправить решение'
          }}<kbd class="shortcut-hint" aria-hidden="true">{{ shortcutModifier }} ⇧ ↵</kbd>
        </button>
      </div>
    </div>
  </section>
</template>
<script setup>
import { computed, inject, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import AppIcon from '../AppIcon.vue'
import { THEME_CONTEXT } from '../../composables/useTheme'
const appTheme = inject(THEME_CONTEXT, ref('dark'))
import SolutionEditor from '../SolutionEditor.vue'
import MarkdownText from '../MarkdownText.vue'
import TestResult from '../TestResult.vue'
import { checkerDiagnostics } from '../../editorDiagnostics'
import { usePracticeRun } from '../../composables/usePracticeRun'
import { difficultyLabel, verdictLabel } from '../../labels'
const props = defineProps({
  roomStatus: String,
  activeBattleTitle: String,
  roomId: String,
  battleId: String,
  task: Object,
  participants: { type: Array, default: () => [] },
  meId: String,
  submitLanguage: { type: String, default: 'python' },
  submitCode: { type: String, default: '' },
  isChecking: Boolean,
  opponentActivity: Object,
  leader: Object,
  round: Object,
  mySubmission: Object,
  canSubmit: { type: Boolean, default: true },
  draftStatus: String,
  effectsEnabled: { type: Boolean, default: true },
  canRestoreDraft: Boolean,
})
const emit = defineEmits([
  'update:submit-language',
  'update:submit-code',
  'submit',
  'surrender',
  'round-start',
  'restore-draft',
  'countdown',
])
const editor = ref(),
  workspace = ref(),
  workspaceHeight = ref(null),
  tab = ref('code'),
  split = ref(true),
  fullscreen = ref(false),
  consoleTab = ref('examples'),
  customInput = ref(''),
  cursor = ref({ line: 1, column: 1 })
const settings = reactive({
  fontSize: 15,
  theme: 'system',
  tabSize: 4,
  wrap: false,
  taskWidth: 34,
  consoleHeight: 190,
})
try {
  split.value = localStorage.getItem('gcb:layout') !== 'focus'
  Object.assign(
    settings,
    JSON.parse(localStorage.getItem('codebattle:editor') || '{}'),
  )
} catch {}
settings.fontSize = Math.max(12, Math.min(24, Number(settings.fontSize) || 15))
settings.taskWidth = Math.max(
  22,
  Math.min(55, Number(settings.taskWidth) || 34),
)
settings.consoleHeight = Math.max(
  130,
  Math.min(460, Number(settings.consoleHeight) || 190),
)
if (![2, 4, 8].includes(settings.tabSize)) settings.tabSize = 4
if (!['light', 'dark', 'system'].includes(settings.theme)) settings.theme = 'system'
settings.wrap = settings.wrap === true
watch(settings, () => {
  try {
    localStorage.setItem('codebattle:editor', JSON.stringify(settings))
  } catch {}
})
function toggleLayout() {
  split.value = !split.value
  try {
    localStorage.setItem('gcb:layout', split.value ? 'split' : 'focus')
  } catch {}
}
const {
  result: runResult,
  running,
  error: runError,
  run,
} = usePracticeRun(() => props.roomId)
const staleRun = computed(
  () =>
    runResult.value &&
    (runResult.value.source_code !== props.submitCode ||
      runResult.value.language !== props.submitLanguage ||
      (runResult.value.kind === 'custom' && runResult.value.tests?.[0]?.input !== customInput.value)),
)
const staleSubmission = computed(() => Boolean(props.mySubmission &&
  (props.mySubmission.source_code !== props.submitCode || props.mySubmission.language !== props.submitLanguage)))
const editorDiagnostics = computed(() => {
  const candidates = [runResult.value, props.mySubmission].filter(item => item &&
    item.source_code === props.submitCode && item.language === props.submitLanguage)
    .sort((a, b) => (Date.parse(b.created_at) || 0) - (Date.parse(a.created_at) || 0))
  const snapshot = candidates[0]
  return snapshot ? { source_code: snapshot.source_code, language: snapshot.language,
    items: snapshot.verdict === 'queued' ? [] : checkerDiagnostics(snapshot.message || snapshot.checker_message, snapshot.source_code, snapshot.language) } : null
})
const isMac = /Mac|iPhone|iPad/.test(navigator.platform || '')
const shortcutModifier = isMac ? '⌘' : 'Ctrl'
const shortcutKey = isMac ? 'Meta' : 'Control'
const runLabel = computed(() => running.value ? 'Выполняется…' : consoleTab.value === 'custom' ? 'Запустить свой ввод' : 'Проверить примеры')
function runCode() {
  if (!props.canSubmit || !props.submitCode.trim() || running.value) return
  const kind = consoleTab.value === 'custom' ? 'custom' : 'examples'
  consoleTab.value = kind === 'custom' ? 'custom' : 'examples'
  if (kind === 'examples' && !publicTests.value.length) return
  run({
    kind,
    language: props.submitLanguage,
    source_code: props.submitCode,
    input: customInput.value,
  })
}
function send() {
  if (props.canSubmit && !props.isChecking && props.submitCode.trim()) {
    consoleTab.value = 'verdict'
    emit('submit')
  }
}
function useExample(input) {
  customInput.value = input || ''
  consoleTab.value = 'custom'
  tab.value = 'code'
}
const publicTests = computed(() => props.task?.public_tests || [])
const errorLine = computed(() => {
  const text = props.mySubmission?.checker_message || ''
  const match = text.match(/line\s+(\d+)|:(\d+):/i)
  return match ? Number(match[1] || match[2]) : null
})
const practiceErrorLine = computed(() => {
  const match = runResult.value?.message?.match(/line\s+(\d+)|:(\d+):/i)
  return match ? Number(match[1] || match[2]) : null
})
const now = ref(Date.now()),
  offset = ref(0)
watch(
  () => props.round?.server_now,
  (value) => {
    if (value) offset.value = new Date(value).getTime() - Date.now()
  },
  { immediate: true },
)
const startsIn = computed(() =>
  Math.max(
    0,
    Math.ceil(
      (new Date(props.round?.started_at || 0).getTime() -
        now.value -
        offset.value) /
        1000,
    ),
  ),
)
const preparing = computed(() => props.round?.is_preparing)
let nextStartRefresh = 0,
  startRefreshAttempts = 0,
  timer,
  cleanupDrag = () => {}
watch(
  () => [props.roomId, props.round?.started_at],
  () => {
    nextStartRefresh = 0
    startRefreshAttempts = 0
  },
)
watch(
  () => props.roomId,
  () => {
    tab.value = 'code'
    consoleTab.value = 'examples'
    customInput.value = ''
  },
)
watch(startsIn, (value, old) => {
  if (preparing.value && value > 0 && value !== old) emit('countdown')
})
function refreshRoundStart() {
  if (!preparing.value || startsIn.value !== 0) return
  if (Date.now() >= nextStartRefresh) {
    // Keep the server lock until it clears, retrying a request that reached
    // the server just before the start or failed during a reconnect.
    nextStartRefresh = Date.now() + Math.min(500 * 2 ** startRefreshAttempts++, 5000)
    emit('round-start')
  }
}
watch([preparing, startsIn], refreshRoundStart)
const opponentSurrendered = computed(() => props.participants.some(p => p.student_id !== props.meId && p.surrendered_at))
const opponentSolved = computed(() => props.participants.some(p => p.student_id !== props.meId && p.accepted_at && !p.surrendered_at))
const elapsed = computed(() => props.round?.started_at
  ? Math.max(0, Math.floor((now.value + offset.value - Date.parse(props.round.started_at)) / 1000)) : null)
const surrenderRemaining = computed(() => props.round?.surrender_available_at
  ? Math.max(0, Math.ceil((Date.parse(props.round.surrender_available_at) - now.value - offset.value) / 1000)) : null)
const surrenderUnlocked = computed(() => Boolean(props.round?.is_active &&
  !props.participants.some(p => p.student_id === props.meId && (p.accepted_at || p.surrendered_at)) &&
  (props.round.can_surrender || opponentSolved.value || surrenderRemaining.value === 0)))
function formatTime(seconds) {
  if (seconds == null) return '—:—'
  const minutes = Math.floor(seconds / 60), rest = seconds % 60
  return minutes < 60 ? `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
    : `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}
const timerText = computed(() => formatTime(elapsed.value))
function startResize(event, kind) {
  if (event.button !== 0) return
  event.preventDefault()
  cleanupDrag()
  const bounds = workspace.value.getBoundingClientRect(),
    start = event.clientY,
    height = settings.consoleHeight
  const move = (e) => {
    if (kind === 'task')
      settings.taskWidth = Math.max(
        22,
        Math.min(
          55,
          Math.round(((e.clientX - bounds.left) / bounds.width) * 100),
        ),
      )
    else
      settings.consoleHeight = Math.max(
        130,
        Math.min(460, height + start - e.clientY),
      )
  }
  const end = () => cleanupDrag()
  cleanupDrag = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', end)
    window.removeEventListener('pointercancel', end)
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', end)
  window.addEventListener('pointercancel', end)
}
function escape(event) {
  if (event.key === 'Escape' && !event.defaultPrevented) fullscreen.value = false
}
let layoutObserver
function fitWorkspace() {
  if (!workspace.value || fullscreen.value || window.innerWidth <= 850) {
    workspaceHeight.value = null
    return
  }
  const top = workspace.value.getBoundingClientRect().top + window.scrollY
  const actions = workspace.value.closest('.arena')?.querySelector('.submit-toolbar')
  workspaceHeight.value = Math.max(430, Math.floor(window.innerHeight - top - (actions?.getBoundingClientRect().height || 0) - 24))
}
watch(workspace, element => {
  layoutObserver?.disconnect()
  if (element && typeof ResizeObserver !== 'undefined') {
    layoutObserver = new ResizeObserver(fitWorkspace)
    layoutObserver.observe(element.closest('main') || element.parentElement)
  }
  fitWorkspace()
}, { flush: 'post' })
let previousOverflow, previousFullscreenFocus
watch(fullscreen, value => {
  nextTick(fitWorkspace)
  if (value) {
    previousOverflow = document.body.style.overflow
    previousFullscreenFocus = document.activeElement
    document.body.style.overflow = 'hidden'
    if (tab.value === 'code') nextTick(() => editor.value?.focus?.())
  } else if (previousOverflow !== undefined) {
    document.body.style.overflow = previousOverflow
    previousOverflow = undefined
    nextTick(() => { if (previousFullscreenFocus?.isConnected) previousFullscreenFocus.focus() })
  }
})
onMounted(() => {
  timer = setInterval(() => {
    now.value = Date.now()
    refreshRoundStart()
  }, 200)
  window.addEventListener('keydown', escape)
  window.addEventListener('resize', fitWorkspace)
  fitWorkspace()
  refreshRoundStart()
})
onUnmounted(() => {
  if (previousOverflow !== undefined) document.body.style.overflow = previousOverflow
  clearInterval(timer)
  cleanupDrag()
  layoutObserver?.disconnect()
  window.removeEventListener('keydown', escape)
  window.removeEventListener('resize', fitWorkspace)
})
</script>
<style scoped>
.arena-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}
.arena h1 {
  font:
    700 clamp(24px, 3vw, 34px)/1.2 var(--app-font-heading);
  margin: 0;
}
.arena-clock {
  text-align: right;
  flex-shrink: 0;
}
.arena-clock span {
  display: block;
  font-size: 11px;
  color: var(--app-muted);
}
.arena-clock strong {
  font:
    700 30px var(--app-font-heading);
  color: var(--app-brand);
  font-variant-numeric: tabular-nums;
}
.arena-meta,
.arena-player,
.workspace-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.arena-meta {
  margin-bottom: 16px;
  font-size: 12px;
}
.arena-player {
  gap: 6px;
  padding-bottom: 4px;
  border-bottom: 2px solid var(--app-fire);
}
.arena-player.fighter-ice {
  border-color: var(--app-ice);
}
.workspace-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.workspace-tabs {
  display: flex;
  gap: 20px;
}
.workspace-tabs button,
.console-tabs button {
  background: none;
  border: 0;
  border-bottom: 2px solid transparent;
  padding: 9px 0;
  color: var(--app-muted);
  font-size: 13px;
}
.workspace-tabs button[aria-pressed='true'],
.console-tabs button[aria-pressed='true'] {
  color: var(--app-brand);
  border-color: var(--app-brand);
}
.arena-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  height: var(--workspace-height, calc(100dvh - 300px));
  min-height: 430px;
  border: 1px solid var(--app-border);
  background: var(--app-card);
}
.arena-task {
  padding: 22px;
  display: none;
  min-width: 0;
  overflow: auto;
}
.show-task .arena-task {
  display: block;
}
.show-task .arena-solution {
  display: none;
}
.arena-workspace.is-split {
  grid-template-columns: minmax(0, var(--task-width)) 9px minmax(0, 1fr);
}
.is-split .arena-task,
.is-split .arena-solution {
  display: flex;
}
.is-split .arena-task {
  display: block;
}
.workspace-divider {
  display: none;
  background: var(--app-bg);
  border-inline: 1px solid var(--app-border);
  cursor: col-resize;
  touch-action: none;
}
.is-split .workspace-divider {
  display: block;
}
.workspace-divider:hover,
.console-divider:hover {
  background: var(--app-brand);
}
.arena-solution {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.arena-solution :deep(.solution-editor) { min-height:140px; }
.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border-bottom: 1px solid var(--app-border);
}
.editor-toolbar > label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.editor-toolbar select {
  width: auto;
}
.editor-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}
.editor-icon-button {
  border: 0;
  background: none;
  color: var(--app-muted);
  padding: 5px 6px;
  font-size: 13px;
}
.editor-settings {
  position: relative;
  font-size: 12px;
}
.editor-settings summary {
  cursor: pointer;
  padding: 5px;
}
.editor-settings-panel {
  position: absolute;
  right: 0;
  top: 34px;
  z-index: 10;
  width: 260px;
  padding: 16px;
  background: var(--app-card);
  border: 1px solid var(--app-border);
  box-shadow: var(--app-popover-shadow);
  display: grid;
  gap: 12px;
}
.editor-settings-panel label {
  display: grid;
  gap: 5px;
}
.editor-settings-panel .settings-check {
  display: flex;
  align-items: center;
  gap: 8px;
}
.editor-status {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  padding: 5px 14px;
  font-size: 12px;
  color: var(--app-muted);
  background: var(--app-bg);
}
.console-divider {
  height: 7px;
  flex: none;
  background: var(--app-bg);
  cursor: row-resize;
  touch-action: none;
  border-block: 1px solid var(--app-border);
}
.arena-console {
  height: var(--console-height);
  max-height: 45%;
  min-height: 130px;
  flex: none;
  display: flex;
  flex-direction: column;
}
.console-tabs {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  padding: 0 14px;
  border-bottom: 1px solid var(--app-border);
}
.console-tabs button,
.console-tabs a {
  font-size: 12px;
}
.console-tabs a {
  align-self: center;
  color: var(--app-brand);
}
.console-body {
  overflow: auto;
  padding: 12px 14px;
  min-height: 0;
}
.custom-input {
  font:
    13px/1.6 ui-monospace,
    Consolas,
    monospace;
  min-height: 72px;
}
.run-output,
.checker-feedback {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  padding: 12px;
  background: var(--app-bg);
  font-size: 12px;
}
.submit-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px 0;
}
.example-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 12px;
  background: var(--app-bg);
  margin-top: 12px;
}
.example-row span {
  font-size: 11px;
  color: var(--app-muted);
}
.example-row pre {
  font-size: 13px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 6px 0 0;
}
.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 1050;
  padding: 12px 16px;
  height: 100dvh;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 8px;
  overflow: hidden;
  background: var(--app-bg);
}
.is-fullscreen .arena-workspace {
  height: 100%;
  min-height: 0;
}
.is-fullscreen .arena-meta, .is-fullscreen .workspace-toolbar { display:none; }
.is-fullscreen:has(.round-notice) { grid-template-rows:auto auto minmax(0, 1fr) auto; }
.is-fullscreen .round-notice { margin:0 !important; padding:8px 12px; font-size:12px; }
.is-fullscreen .arena-heading { flex-wrap:nowrap; gap:12px; margin:0; }
.is-fullscreen .arena-heading > div:first-child { min-width:0; flex:1; }
.is-fullscreen .arena-heading h1 { font-size:18px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.is-fullscreen .hero-eyebrow { display:none; }
.is-fullscreen .arena-clock span { font-size:10px; }
.is-fullscreen .arena-clock strong { font-size:20px; }
.is-fullscreen .submit-toolbar { padding:8px 0 0; }
.focus-controls { display:flex; flex:none; gap:6px; }
.focus-connection { color:var(--app-fire); font-size:11px; }
.focus-controls .btn { font-size:12px; padding:6px 8px; }
.shortcut-hint { margin-left:8px; padding:3px 5px; font-size:10px; color:inherit; background:#ffffff0a; border:1px solid currentColor; border-radius:3px; opacity:.65; box-shadow:none; }
.match-intro {
  min-height: 70dvh;
  padding: 40px 24px;
  text-align: center;
  background:
    linear-gradient(0deg, #111418f5, #11141830),
    url('../../assets/arena/temple.jpg') center 35% / cover;
  border: 1px solid var(--app-border);
}
.match-intro h1 {
  font:
    700 clamp(28px, 5vw, 44px) var(--app-font-heading);
  text-transform: uppercase;
}
.match-contenders {
  display: flex;
  justify-content: space-around;
  gap: 16px;
  flex-wrap: wrap;
  margin: 100px 0 24px;
}
.match-contenders article {
  padding: 16px 25px;
  min-width: 140px;
  background: #15191cde;
  border-bottom: 3px solid var(--app-fire);
}
.match-contenders article.fighter-ice {
  border-color: var(--app-ice);
}
.match-contenders h2 {
  font:
    700 28px var(--app-font-heading);
  margin: 7px 0;
}
.match-contenders article > span:last-child {
  font-size: 12px;
  color: var(--app-muted);
}
.fighter-monogram {
  font:
    700 28px var(--app-font-heading);
  color: var(--app-brand);
}
.match-countdown {
  font:
    700 clamp(52px, 12vw, 90px)/1.1 var(--app-font-heading);
  color: var(--app-brand);
  margin: 15px 0;
}
.match-countdown.animated {
  animation: count-pop 0.35s ease-out;
}
.match-intro > p:last-child {
  font-size: 12px;
  color: var(--app-muted);
}
:global([data-theme='light'] .match-intro) {
  background:linear-gradient(0deg,#f4f5f1f5,#f4f5f1b8),url('../../assets/arena/temple.jpg') center 35% / cover;
}
:global([data-theme='light'] .match-contenders article) { background:var(--app-card); }
@keyframes count-pop {
  from {
    transform: scale(1.35);
  }
  to {
    transform: scale(1);
  }
}
@media (max-width: 850px) {
  .split-toggle,
  .workspace-divider,
  .is-split .workspace-divider {
    display: none;
  }
  .arena-workspace.is-split {
    grid-template-columns: minmax(0, 1fr);
  }
  .is-split .arena-task {
    display: none;
  }
  .is-split.show-task .arena-task {
    display: block;
  }
  .is-split.show-task .arena-solution {
    display: none;
  }
  .arena-workspace {
    min-height: 600px;
    height: calc(100dvh - 330px);
  }
  .arena-heading h1 {
    font-size: 24px;
  }
  .editor-settings-panel {
    width: 230px;
  }
  .console-tabs {
    gap: 12px;
  }
  .match-contenders {
    margin-top: 50px;
  }
}
@media (max-width: 540px) {
  .editor-settings { position:static; }
  .editor-toolbar { position:relative; }
  .editor-settings-panel { top:100%; right:8px; }
  .workspace-actions {
    gap: 8px;
  }
  .submit-toolbar > .workspace-actions {
    width: 100%;
  }
  .submit-toolbar .btn-primary {
    flex: 1;
  }
  .round-actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: stretch;
  }
  .round-actions .btn {
    min-width: 0;
    min-height: 54px;
    white-space: normal;
  }
  .editor-toolbar {
    padding: 8px;
  }
  .editor-actions {
    gap: 2px;
  }
  .editor-settings-panel {
    right: -2px;
  }
  .is-fullscreen {
    padding: 12px;
  }
  .arena-clock strong {
    font-size: 26px;
  }
  .workspace-toolbar .btn {
    font-size: 11px;
  }
  .workspace-tabs {
    gap: 12px;
  }
  .shortcut-hint { display:none; }
  .arena-meta {
    gap: 8px;
  }
  .match-intro {
    padding: 25px 16px;
  }
  .match-contenders article {
    min-width: 100px;
    padding: 12px;
  }
  .match-intro h1 {
    font-size: 32px;
  }
}
</style>
