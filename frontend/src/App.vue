<template>
  <div class="app-shell">
    <AppTopbar
      :me="me"
      :is-teacher="isTeacher"
      :teacher-page="teacherPage"
      :results-active="isPersonalResults"
      @go-results="router.push('/results')"
      @go-battles="goToBattlesPage"
      @go-packages="goToPackagesPage"
      @go-play="goToPlayPage"
      @logout="logout"
    />

    <main class="container py-4" :class="{ 'arena-container': myRoom.room_id && showPlayerUi && !isPersonalResults }">
      <div v-if="me && (connectionState !== 'online' || dataError)" class="notice notice-warning mb-3" role="status">
        <span>{{ dataError || (connectionState === 'connecting' ? 'Подключаемся к игре…' : 'Соединение потеряно. Черновик остаётся на этом устройстве.') }}</span>
        <button class="btn btn-sm btn-outline-secondary" @click="retryConnection">Повторить</button>
      </div>
      <div v-if="!me && dataError" class="notice notice-warning mb-3" role="alert">{{ dataError }} <button class="btn btn-sm btn-outline-secondary" @click="reloadPage">Обновить страницу</button></div>
      <section v-if="me && showPlayerUi && !isPersonalResults && studentJoinedBattleId && !myRoom.room_id && lastResult?.battle_id === studentJoinedBattleId" class="round-summary mb-4" aria-live="polite">
        <div><p class="eyebrow mb-1">Последний раунд · {{ lastResult.task_title }}</p><h2 class="h5 mb-1">{{ resultLabel(lastResult.result_type) }}</h2><p class="text-muted small mb-0">{{ lastResult.is_final ? 'Результат сохранён' : 'Остальные участники ещё дорешивают. Итоговые очки появятся после завершения.' }}</p></div>
        <div class="text-end"><strong class="result-points">+{{ lastResult.points }}</strong><span class="text-muted small d-block">очков за раунд</span></div>
      </section>
      <section class="card shadow-sm border-0" v-if="isBootstrapping">
        <div class="card-body d-flex align-items-center gap-3 py-4">
          <div class="spinner-border spinner-border-sm text-primary" role="status" aria-hidden="true"></div>
          <span>Загружаем данные...</span>
        </div>
      </section>

      <LoginCard
        v-else-if="!me"
        :login-form="loginForm"
        :dev-login-enabled="authOptions.devLoginEnabled"
        :geekclass-enabled="authOptions.geekclassEnabled"
        @dev-login="devLogin"
        @login="geekclassLogin"
      />

      <template v-else>
        <StudentResultsView v-if="route.name === 'my-results'" :refresh-key="reportVersion" :play-path="isTeacher ? '/play' : '/'" @resume="resumeBattle" />
        <BattleResultDetail v-else-if="route.name === 'my-result-detail'" :path="`/me/results/${route.params.battleId}`" :refresh-key="reportVersion" @resume="resumeBattle" />
        <template v-else-if="showTeacherConsole">
          <template v-if="teacherPage === 'battles'">
            <BattleResultDetail v-if="isStudentReportPage" :path="`/battles/${route.params.battleId}/students/${route.params.studentId}/results`" :back-path="`/battles/${route.params.battleId}`" :task-id="route.query.task ? String(route.query.task) : undefined" :refresh-key="reportVersion" teacher />
            <TeacherBattleRoomLogView
              v-else-if="isBattleRoomLogPage"
              :room-log="selectedBattleRoomLog"
              :rechecking-submission-ids="recheckingSubmissionIds"
              @back="goToBattleDetailsPage"
              @recheck-submission="recheckSubmissionFromRoomLog"
              @rejudged="syncData"
            />

            <TeacherBattleDetailsView
              v-else-if="isBattleDetailsPage"
              :selected-battle="selectedBattle"
              :refresh-key="reportVersion"
              @invite-saved="onInviteSaved"
              @open-student="openStudentReport"
              :battle-tasks="battleTasks"
              :task-packages="taskPackages"
              :battle-package-ids="battlePackageIds"
              :queue-entries="queue.entries"
              :leaderboard-participants="leaderboard.participants"
              :battle-logs="battleLogs"
              :can-delete="selectedBattle?.status === 'finished'"
              @back="goToBattlesPage"
              @open-lobby="openLobby"
              @start="startBattle"
              @stop="stopBattle"
              @finish="finishBattle"
              @delete-battle="deleteBattle"
              @add-package="addPackageToBattle"
              @remove-package="removePackageFromBattle"
              @open-room-log="openBattleRoomLog"
            />

            <TeacherBattleListView
              v-else
              :show-create-battle-form="showCreateBattleForm"
              :new-battle-title="newBattleTitle"
              :new-battle-package-ids="newBattlePackageIds"
              :task-packages="taskPackages"
              :battles="battles"
              @toggle-create="showCreateBattleForm = !showCreateBattleForm"
              @update:new-battle-title="newBattleTitle = $event"
              @toggle-new-battle-package="toggleNewBattlePackage"
              @create-battle="createBattle"
              @open-battle="openBattleDashboard"
            />
          </template>

          <template v-else>
            <TeacherTaskEditorView
              v-if="isTaskEditorPage"
              :has-task="Boolean(selectedPackageTask)"
              :package-name="selectedTaskPackage?.package?.name || 'Пакет'"
              :package-task-form="packageTaskForm"
              @back="closeTaskEditor"
              @save="saveSelectedPackageTask"
              @remove="removeSelectedPackageTask"
            />

            <TeacherPackageDetailsView
              v-else-if="isPackageDetailsPage"
              :selected-task-package="selectedTaskPackage"
              :task-action-panel="taskActionPanel"
              :package-task-form="packageTaskForm"
              @back="goToPackagesPage"
              @open-panel="openTaskActionPanel"
              @close-panel="taskActionPanel = null"
              @export="exportSelectedPackageToJson"
              @delete-package="deleteSelectedTaskPackage"
              @create-task="createTaskInSelectedPackage"
              @open-task="openTaskEditor"
            />

            <TeacherPackagesListView
              v-else
              :task-packages="taskPackages"
              :task-action-panel="taskActionPanel"
              :package-form="packageForm"
              :import-summary="importSummary"
              @open-panel="openTaskActionPanel"
              @close-panel="taskActionPanel = null"
              @file-selected="onTaskJsonSelected"
              @create-package="createTaskPackage"
              @open-package="openTaskPackagePage"
            />
          </template>
        </template>

        <template v-else>
          <StudentActiveRoomView
            v-if="myRoom.room_id"
            :room-status="roomData.status"
            :active-battle-title="activeBattleTitle"
            :room-id="myRoom.room_id"
            :task="roomData.task"
            :participants="roomData.participants"
            :me-id="me.id"
            :submit-language="submitForm.language"
            :submit-code="submitForm.source_code"
            :can-submit="connectionState === 'online' && !dataError"
            :draft-status="draftStatus"
            :is-checking="isSubmissionChecking || isSubmitting"
            :opponent-activity="opponentActivity"
            :grace="roomData.grace"
            :round="roomData.round"
            :my-submission="roomData.mySubmission"
            @update:submit-language="updateSubmitLanguage"
            @update:submit-code="updateSubmitCode"
            @submit="submitCode"
            @surrender="surrenderRound"
          />

          <StudentJoinedBattleView
            v-else-if="studentJoinedBattleId && selectedBattle"
            :battle="selectedBattle"
            :queue-entries="queue.entries"
            :queue-meta="queue.meta"
            :me-id="me.id"
            :my-score="myLeaderboardEntry"
            :leaderboard-participants="leaderboard.participants"
            @ready="readyQueue"
            @leave="leaveQueue"
          />

          <StudentBattleLobbyView v-else @joined="onInviteJoined" />
        </template>
      </template>
    </main>

    <section
      class="toast-msg"
      :class="`toast-${toast.kind}`"
      role="status" aria-live="polite"
      v-if="toast.text"
    >
      <span class="toast-icon" aria-hidden="true">{{ toastIcon }}</span>
      <span>{{ toast.text }}</span>
    </section>

    <section class="bonus-banner" v-if="bonusBanner.text" :key="bonusBanner.id" aria-live="polite">
      {{ bonusBanner.text }}
    </section>

    <section class="burst-layer" aria-hidden="true">
      <span
        v-for="particle in burstParticles"
        :key="particle.id"
        class="burst-dot"
        :style="burstParticleStyle(particle)"
      ></span>
    </section>

    <button
      class="sound-toggle btn btn-sm"
      :class="audioEnabled ? 'btn-primary' : 'btn-outline-secondary'"
      type="button"
      :title="audioEnabled ? 'Выключить звуки' : 'Включить звуки'"
      @click="toggleAudio"
    >
      <AppIcon :name="audioEnabled ? 'volume-on' : 'volume-off'" />
    </button>

    <section class="streak-chip" v-if="showPlayerUi && streak > 1" aria-live="polite">
      🔥 Серия x{{ streak }}
    </section>

    <section class="round-overlay" v-if="roundOverlay.visible" aria-live="polite">
      <div class="round-overlay-card">
        <h3 class="mb-1">{{ roundOverlay.title }}</h3>
        <p class="text-muted mb-2">{{ roundOverlay.subtitle }}</p>
        <p class="mb-2" v-if="roundOverlay.positionText">{{ roundOverlay.positionText }}</p>
        <p class="bonus-score" v-if="roundOverlay.deltaText">{{ roundOverlay.deltaText }}</p>
        <p class="small mb-0" v-if="roundOverlay.streakText">{{ roundOverlay.streakText }}</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import AppIcon from './components/AppIcon.vue'
import { computed, defineAsyncComponent, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { resultLabel, verdictLabel } from './labels'
import api from './api'
import { io } from 'socket.io-client'
import { useRoute, useRouter } from 'vue-router'
import AppTopbar from './components/AppTopbar.vue'
import LoginCard from './components/LoginCard.vue'
import TeacherBattleListView from './components/teacher/TeacherBattleListView.vue'
import TeacherBattleDetailsView from './components/teacher/TeacherBattleDetailsView.vue'
import TeacherBattleRoomLogView from './components/teacher/TeacherBattleRoomLogView.vue'
import TeacherPackagesListView from './components/teacher/TeacherPackagesListView.vue'
import TeacherPackageDetailsView from './components/teacher/TeacherPackageDetailsView.vue'
import TeacherTaskEditorView from './components/teacher/TeacherTaskEditorView.vue'
const StudentActiveRoomView = defineAsyncComponent(() => import('./components/student/StudentActiveRoomView.vue'))
import StudentBattleLobbyView from './components/student/StudentBattleLobbyView.vue'
import StudentJoinedBattleView from './components/student/StudentJoinedBattleView.vue'
import StudentResultsView from './components/results/StudentResultsView.vue'
import BattleResultDetail from './components/results/BattleResultDetail.vue'

const me = ref(null)
const reportVersion = ref(0)
const isPersonalResults = computed(() => route.path.startsWith('/results'))
const isStudentReportPage = computed(() => route.name === 'battle-student-results')
const battles = ref([])
const selectedBattleId = ref(null)
const studentJoinedBattleId = ref(null)
const selectedBattle = computed(() => battles.value.find((b) => b.id === selectedBattleId.value) || null)
const queue = reactive({ entries: [], meta: null })
const leaderboard = reactive({ participants: [] })
const battleLogs = ref([])
const selectedBattleRoomLog = ref(null)
const recheckingSubmissionIds = ref([])
const taskPackages = ref([])
const battleTasks = ref([])
const battlePackages = ref([])
const myRoom = reactive({ room_id: null, match_id: null, battle_id: null })
const roomData = reactive({ status: null, participants: [], task: null, grace: null, round: null, mySubmission: null })

const route = useRoute()
const router = useRouter()
const authResolved = ref(false)
const initialSyncDone = ref(false)
const showCreateBattleForm = ref(false)

const packageImportFile = ref(null)
const importSummary = ref(null)
const taskActionPanel = ref(null)
const selectedTaskPackageId = ref(null)
const selectedTaskPackage = ref(null)
const selectedPackageTaskId = ref(null)
const authOptions = reactive({ devLoginEnabled: false, geekclassEnabled: true })
const isAuthRedirecting = ref(false)

const loginForm = reactive({ name: 'Teacher', external_id: 'teacher-1', role: 'teacher' })
const newBattleTitle = ref('Весенний батл')
const newBattlePackageIds = ref([])
const submitForm = reactive({ language: 'python', source_code: 'print("hello")' })
const SUBMIT_DRAFT_STORAGE_PREFIX = 'gcb:submit-draft:v1'
const DEFAULT_ROOM_SOURCE_CODE = ''
const draftRoomId = ref(null)
const packageForm = reactive({ name: '', description: '' })
const packageTaskForm = reactive({
  title: '',
  statement_md: '',
  difficulty: 'easy',
  check_type: 'tests',
  tests_json: '[]'
})

const toast = reactive({ text: '', kind: 'info', stamp: 0 })
const bonusBanner = reactive({ text: '', id: 0 })
const burstParticles = ref([])
let particleSeq = 0
const leaderboardPointsMemo = reactive({})
const audioEnabled = ref(false)
const streak = ref(0)
const bestStreak = ref(0)
const roundOverlay = reactive({
  visible: false,
  title: '',
  subtitle: '',
  positionText: '',
  deltaText: '',
  streakText: '',
  stamp: 0
})
const isSubmissionChecking = ref(false)
const isSubmitting = ref(false)
let sessionEpoch = 0
const opponentActivity = ref(null)
const connectionState = ref('connecting')
const dataError = ref('')
const draftStatus = ref('')
const lastResult = ref(null)
let socket = null
let refreshTimer = null
let eventSyncTimer = null
let syncPromise = null
let syncAgain = false
let graceRefreshTimer = null
let audioCtx = null
let unloadHandlersBound = false

const isTeacher = computed(() => me.value && (me.value.role === 'teacher' || me.value.role === 'admin'))
const teacherPage = computed(() => {
  if (route.path.startsWith('/packages')) return 'tasks'
  if (route.path.startsWith('/play') || isPersonalResults.value) return 'play'
  return 'battles'
})
const teacherPlayMode = computed(() => isTeacher.value && teacherPage.value === 'play')
const showTeacherConsole = computed(() => isTeacher.value && !teacherPlayMode.value)
const showPlayerUi = computed(() => !isTeacher.value || teacherPlayMode.value)
const isBattleDetailsPage = computed(() => route.name === 'battle-details')
const isBattleRoomLogPage = computed(() => route.name === 'battle-room-log')
const isPackageDetailsPage = computed(() => route.name === 'package-details')
const isTaskEditorPage = computed(() => route.name === 'package-task-editor')
const isBootstrapping = computed(() => !authResolved.value || isAuthRedirecting.value || (Boolean(me.value) && !initialSyncDone.value))
const battlePackageIds = computed(() => (battlePackages.value || []).map((p) => p.id))
const activeBattleTitle = computed(() => battles.value.find((i) => i.id === myRoom.battle_id)?.title || null)
const selectedPackageTask = computed(() => selectedTaskPackage.value?.tasks?.find((t) => t.id === selectedPackageTaskId.value) || null)
const myLeaderboardEntry = computed(() => {
  if (!me.value) return null
  return leaderboard.participants.find((p) => p.user_id === me.value.id) || null
})
const toastIcon = computed(() => {
  if (toast.kind === 'success') return '✓'
  if (toast.kind === 'warning') return '!'
  if (toast.kind === 'error') return '✕'
  if (toast.kind === 'bonus') return '★'
  return '•'
})

function toggleAudio() {
  audioEnabled.value = !audioEnabled.value
  if (audioEnabled.value) playSound('toggle_on')
}

function ensureAudioContext() {
  if (typeof window === 'undefined') return null
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) return null
  if (!audioCtx) audioCtx = new Ctx()
  if (audioCtx.state === 'suspended') audioCtx.resume().catch(() => {})
  return audioCtx
}

function playTone({ freq = 440, duration = 0.1, type = 'sine', gain = 0.08, when = 0 }) {
  const ctx = ensureAudioContext()
  if (!ctx || !audioEnabled.value) return
  const osc = ctx.createOscillator()
  const amp = ctx.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, ctx.currentTime + when)
  amp.gain.setValueAtTime(0.0001, ctx.currentTime + when)
  amp.gain.exponentialRampToValueAtTime(gain, ctx.currentTime + when + 0.01)
  amp.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + when + duration)
  osc.connect(amp).connect(ctx.destination)
  osc.start(ctx.currentTime + when)
  osc.stop(ctx.currentTime + when + duration + 0.02)
}

function playSound(kind) {
  if (!audioEnabled.value || prefersReducedMotion()) return
  if (kind === 'bonus') {
    playTone({ freq: 620, duration: 0.09, type: 'triangle', gain: 0.09, when: 0 })
    playTone({ freq: 880, duration: 0.11, type: 'triangle', gain: 0.085, when: 0.08 })
    playTone({ freq: 1170, duration: 0.13, type: 'triangle', gain: 0.08, when: 0.17 })
    return
  }
  if (kind === 'success') {
    playTone({ freq: 520, duration: 0.08, type: 'sine', gain: 0.08, when: 0 })
    playTone({ freq: 740, duration: 0.1, type: 'sine', gain: 0.075, when: 0.08 })
    return
  }
  if (kind === 'warning') {
    playTone({ freq: 290, duration: 0.12, type: 'square', gain: 0.06, when: 0 })
    return
  }
  if (kind === 'error') {
    playTone({ freq: 240, duration: 0.12, type: 'sawtooth', gain: 0.06, when: 0 })
    playTone({ freq: 190, duration: 0.12, type: 'sawtooth', gain: 0.05, when: 0.11 })
    return
  }
  if (kind === 'round_end') {
    playTone({ freq: 660, duration: 0.08, type: 'triangle', gain: 0.08, when: 0 })
    playTone({ freq: 540, duration: 0.08, type: 'triangle', gain: 0.08, when: 0.09 })
    playTone({ freq: 860, duration: 0.15, type: 'triangle', gain: 0.09, when: 0.19 })
    return
  }
  if (kind === 'toggle_on') {
    playTone({ freq: 480, duration: 0.06, type: 'sine', gain: 0.06, when: 0 })
    playTone({ freq: 700, duration: 0.08, type: 'sine', gain: 0.06, when: 0.06 })
  }
}

function showRoundOverlay({ title, subtitle, positionText = '', deltaText = '', streakText = '' }) {
  const stamp = Date.now()
  roundOverlay.visible = true
  roundOverlay.title = title
  roundOverlay.subtitle = subtitle
  roundOverlay.positionText = positionText
  roundOverlay.deltaText = deltaText
  roundOverlay.streakText = streakText
  roundOverlay.stamp = stamp
  setTimeout(() => {
    if (roundOverlay.stamp === stamp) {
      roundOverlay.visible = false
    }
  }, 2600)
}

function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function burstParticleStyle(particle) {
  return {
    left: `${particle.originX}%`,
    top: `${particle.originY}%`,
    '--dx': `${particle.dx}px`,
    '--dy': `${particle.dy}px`,
    '--dr': `${particle.dr}deg`,
    '--sz': `${particle.size}px`,
    '--h': `${particle.hue}`
  }
}

function triggerBurst({ intensity = 'normal', originX = 50, originY = 58 } = {}) {
  if (prefersReducedMotion()) return
  const count = intensity === 'high' ? 34 : 22
  const next = Array.from({ length: count }, (_, idx) => ({
    id: `${Date.now()}-${particleSeq++}-${idx}`,
    originX,
    originY,
    dx: Math.round((Math.random() * 2 - 1) * (intensity === 'high' ? 320 : 210)),
    dy: Math.round(-(120 + Math.random() * (intensity === 'high' ? 260 : 180))),
    dr: Math.round((Math.random() * 2 - 1) * 340),
    size: Math.round(6 + Math.random() * 9),
    hue: Math.round(20 + Math.random() * 300)
  }))
  burstParticles.value = [...burstParticles.value, ...next]
  setTimeout(() => {
    const ids = new Set(next.map((p) => p.id))
    burstParticles.value = burstParticles.value.filter((p) => !ids.has(p.id))
  }, 980)
}

function showBonusBanner(text) {
  bonusBanner.text = text
  bonusBanner.id = Date.now()
  const stamp = bonusBanner.id
  setTimeout(() => {
    if (bonusBanner.id === stamp) {
      bonusBanner.text = ''
    }
  }, 1450)
}

function notify(msg, kind = 'info', options = {}) {
  const stamp = Date.now()
  toast.text = msg
  toast.kind = kind
  toast.stamp = stamp
  if (!options.silent) {
    if (kind === 'bonus') playSound('bonus')
    else if (kind === 'success') playSound('success')
    else if (kind === 'warning') playSound('warning')
    else if (kind === 'error') playSound('error')
  }
  if (options.burst) {
    triggerBurst({ intensity: options.intensity || 'normal', originX: options.originX ?? 50, originY: options.originY ?? 58 })
  }
  if (options.banner) {
    showBonusBanner(options.banner)
  }
  setTimeout(() => {
    if (toast.stamp === stamp) {
      toast.text = ''
    }
  }, 2600)
}

function findParticipantName(studentId) {
  const p = roomData.participants.find((item) => item.student_id === studentId)
  return p?.name || String(studentId || '').slice(0, 8)
}

function showOpponentActivity(payload) {
  const stamp = Date.now()
  opponentActivity.value = { ...payload, active: true, stamp }
  setTimeout(() => {
    if (opponentActivity.value?.stamp === stamp) {
      opponentActivity.value = null
    }
  }, 2200)
}

function clearGraceRefreshTimer() {
  if (graceRefreshTimer) {
    clearTimeout(graceRefreshTimer)
    graceRefreshTimer = null
  }
}

function scheduleGraceRefresh() {
  clearGraceRefreshTimer()
  const deadlineAt = roomData.grace?.deadline_at
  if (!deadlineAt || !myRoom.room_id) return
  const delayMs = Math.max(800, new Date(deadlineAt).getTime() - Date.now() + 1000)
  graceRefreshTimer = setTimeout(() => {
    loadCurrentRoom().catch(() => {})
  }, delayMs)
}

function goToBattlesPage() {
  router.push(isTeacher.value ? '/battles' : '/')
}

function goToPackagesPage() {
  if (route.path !== '/packages') router.push('/packages')
}

function goToPlayPage() {
  if (route.path !== '/play') router.push('/play')
}

function toggleNewBattlePackage(packageId) {
  if (newBattlePackageIds.value.includes(packageId)) {
    newBattlePackageIds.value = newBattlePackageIds.value.filter((id) => id !== packageId)
    return
  }
  newBattlePackageIds.value = [...newBattlePackageIds.value, packageId]
}

async function openBattleDashboard(battleId) {
  selectedBattleRoomLog.value = null
  recheckingSubmissionIds.value = []
  selectedBattleId.value = battleId
  await router.push(`/battles/${battleId}`)
}

async function openTaskPackagePage(packageId) {
  await router.push(`/packages/${packageId}`)
}

function closeTaskEditor() {
  selectedPackageTaskId.value = null
  taskActionPanel.value = null
  if (selectedTaskPackageId.value) {
    router.push(`/packages/${selectedTaskPackageId.value}`)
    return
  }
  router.push('/packages')
}

function scheduleSync() {
  clearTimeout(eventSyncTimer)
  eventSyncTimer = setTimeout(() => { if (me.value) syncData().catch(() => {}) }, 120)
}

function setupSocket() {
  if (socket) return
  socket = io('/', { withCredentials: true, closeOnBeforeunload: true })
  socket.on('connect', () => {
    connectionState.value = 'online'
    subscribeSocket()
    syncData().catch(() => {})
  })
  socket.on('disconnect', () => { connectionState.value = 'offline' })
  socket.on('connect_error', () => { connectionState.value = 'offline' })
  for (const event of ['queue_updated', 'battle_status_changed', 'match_found', 'round_finished', 'leaderboard_updated', 'presence_updated']) {
    socket.on(event, scheduleSync)
  }
  socket.on('submission_queued', (payload) => {
    if (isEventForCurrentMatch(payload) && payload.student_id !== me.value?.id) {
      showOpponentActivity({ kind: 'pending', message: `${findParticipantName(payload.student_id)} отправил решение` })
    }
    scheduleSync()
  })
  socket.on('submission_verdict', (payload) => {
    if (isEventForCurrentMatch(payload)) {
      if (payload.student_id === me.value?.id) {
        isSubmissionChecking.value = false
        notify(verdictLabel(payload.verdict), payload.verdict === 'accepted' ? 'success' : 'info')
      } else {
        showOpponentActivity({ kind: payload.verdict === 'accepted' ? 'success' : 'fail', message: `${findParticipantName(payload.student_id)}: ${verdictLabel(payload.verdict)}` })
      }
    }
    scheduleSync()
  })
}

function retryConnection() {
  socket?.connect()
  syncData().catch(() => {})
}
function reloadPage() { window.location.reload() }
function refreshOnFocus() {
  if (me.value && document.visibilityState === 'visible') retryConnection()
}
function reportUiError(event) { notify(event.detail || 'Не удалось выполнить действие. Попробуйте ещё раз.', 'error') }

function closeSocketForUnload() {
  if (!socket) return
  try {
    if (socket.connected) {
      socket.disconnect()
    }
  } catch {}
}

function bindUnloadHandlers() {
  if (typeof window === 'undefined' || unloadHandlersBound) return
  window.addEventListener('beforeunload', closeSocketForUnload)
  window.addEventListener('pagehide', closeSocketForUnload)
  unloadHandlersBound = true
}

function unbindUnloadHandlers() {
  if (typeof window === 'undefined' || !unloadHandlersBound) return
  window.removeEventListener('beforeunload', closeSocketForUnload)
  window.removeEventListener('pagehide', closeSocketForUnload)
  unloadHandlersBound = false
}

function subscribeSocket() {
  if (!socket || !me.value) return
  socket.emit('subscribe', {
    battle_id: selectedBattleId.value || myRoom.battle_id || undefined,
    room_id: myRoom.room_id || undefined,
    match_id: myRoom.match_id || undefined
  })
}

function isEventForCurrentMatch(payload) {
  if (!showPlayerUi.value) return true
  const currentMatchId = myRoom.match_id ? String(myRoom.match_id) : null
  const payloadMatchId = payload?.match_id ? String(payload.match_id) : null
  if (!currentMatchId || !payloadMatchId) return false
  return currentMatchId === payloadMatchId
}

function draftStorageKey(roomId) {
  if (!roomId) return null
  const userId = me.value?.id ? String(me.value.id) : 'anonymous'
  return `${SUBMIT_DRAFT_STORAGE_PREFIX}:${userId}:${String(roomId)}`
}

function readRoomDraft(roomId) {
  if (typeof window === 'undefined') return null
  const key = draftStorageKey(roomId)
  if (!key) return null
  try {
    const value = window.localStorage.getItem(key)
    if (value === null) return null
    try { const draft = JSON.parse(value); if (draft?.version === 2) return draft } catch {}
    return { source_code: value, language: 'python' }
  } catch {
    return null
  }
}

function writeRoomDraft(roomId, sourceCode) {
  if (typeof window === 'undefined') return
  const key = draftStorageKey(roomId)
  if (!key) return
  try {
    window.localStorage.setItem(key, JSON.stringify({ version: 2, source_code: String(sourceCode ?? ''), language: submitForm.language }))
    draftStatus.value = 'Черновик сохранён на устройстве'
  } catch { draftStatus.value = 'Не удалось сохранить черновик' }
}

function applyDraftForRoom(roomId) {
  if (!roomId) {
    draftRoomId.value = null
    return
  }
  const stored = readRoomDraft(roomId)
  submitForm.source_code = stored?.source_code ?? DEFAULT_ROOM_SOURCE_CODE
  submitForm.language = stored?.language || 'python'
  draftStatus.value = stored ? 'Черновик восстановлен' : 'Автосохранение на устройстве'
  draftRoomId.value = String(roomId)
}

function updateSubmitCode(nextCode) {
  submitForm.source_code = nextCode
  if (myRoom.room_id) {
    writeRoomDraft(myRoom.room_id, submitForm.source_code)
  }
}

function updateSubmitLanguage(language) {
  submitForm.language = language
  if (myRoom.room_id) writeRoomDraft(myRoom.room_id, submitForm.source_code)
}

async function devLogin() {
  if (!authOptions.devLoginEnabled) {
    notify('Тестовый вход отключен', 'warning')
    return
  }
  initialSyncDone.value = false
  try {
  const { data } = await api.post('/auth/dev-login', loginForm)
  me.value = data
  authResolved.value = true
  setupSocket()
  await syncData()
  subscribeSocket()
  } finally { initialSyncDone.value = true }
}

async function loadAuthOptions() {
  try {
    const { data } = await api.get('/auth/options')
    authOptions.devLoginEnabled = Boolean(data?.dev_login_enabled)
    authOptions.geekclassEnabled = Boolean(data?.geekclass_enabled ?? true)
  } catch {
    authOptions.devLoginEnabled = false
    authOptions.geekclassEnabled = false
    throw new Error('Auth options unavailable')
  }
}

function geekclassLogin() {
  if (!authOptions.geekclassEnabled) {
    notify('Вход через GeekClass временно недоступен', 'warning')
    return
  }
  isAuthRedirecting.value = true
  const next = typeof window !== 'undefined'
    ? `${window.location.pathname}${window.location.search}${window.location.hash}`
    : '/'
  window.location.href = `/api/v1/auth/login?next=${encodeURIComponent(next)}`
}

async function logout() {
  await api.post('/auth/logout')
  sessionEpoch += 1
  lastResult.value = null
  dataError.value = ''
  me.value = null
  selectedBattleId.value = null
  studentJoinedBattleId.value = null
  queue.entries = []
  queue.meta = null
  leaderboard.participants = []
  battleLogs.value = []
  taskPackages.value = []
  battleTasks.value = []
  battlePackages.value = []
  selectedTaskPackage.value = null
  selectedTaskPackageId.value = null
  selectedPackageTaskId.value = null
  showCreateBattleForm.value = false
  myRoom.room_id = null
  myRoom.match_id = null
  myRoom.battle_id = null
  roomData.status = null
  roomData.participants = []
  roomData.task = null
  roomData.grace = null
  roomData.round = null
  roomData.mySubmission = null
  submitForm.source_code = DEFAULT_ROOM_SOURCE_CODE
  draftRoomId.value = null
  isSubmissionChecking.value = false
  opponentActivity.value = null
  streak.value = 0
  bestStreak.value = 0
  roundOverlay.visible = false
  clearGraceRefreshTimer()
  selectedBattleRoomLog.value = null
  recheckingSubmissionIds.value = []
  initialSyncDone.value = true
  if (socket) {
    socket.disconnect()
    socket = null
  }
}

async function loadMe() {
  try {
    const { data } = await api.get('/me')
    me.value = data
  } catch (error) {
    me.value = null
    if (error?.response?.status !== 401) throw error
  }
}

async function loadBattles() {
  const { data } = await api.get('/battles')
  battles.value = data
  if (showTeacherConsole.value) {
    const routeId = route.params.battleId ? String(route.params.battleId) : null
    if (routeId) selectedBattleId.value = routeId
    else if (!selectedBattleId.value && battles.value.length) selectedBattleId.value = battles.value[0].id
  }
}

async function createBattle() {
  const { data } = await api.post('/battles', {
    title: newBattleTitle.value,
    package_ids: newBattlePackageIds.value
  })
  notify(`Битва создана: ${data.title}`, 'success')
  await loadBattles()
  newBattlePackageIds.value = []
  showCreateBattleForm.value = false
  await openBattleDashboard(data.id)
}

async function selectBattle(id) {
  selectedBattleId.value = id
  if (!myRoom.room_id || showTeacherConsole.value) await loadBattleContext()
  subscribeSocket()
}

async function openLobby() {
  if (!selectedBattleId.value) return
  await api.post(`/battles/${selectedBattleId.value}/open-lobby`)
  notify('Лобби открыто', 'success')
  await syncData()
}

async function startBattle() {
  if (!selectedBattleId.value) return
  const { data } = await api.post(`/battles/${selectedBattleId.value}/start`)
  notify(`Битва запущена, создано комнат: ${data.created_rooms?.length || 0}`, 'bonus', {
    burst: true,
    banner: 'БАТЛ СТАРТОВАЛ'
  })
  await syncData()
}

async function stopBattle() {
  if (!selectedBattleId.value) return
  await api.post(`/battles/${selectedBattleId.value}/stop`)
  notify('Битва остановлена', 'warning')
  await syncData()
}

async function finishBattle() {
  if (!selectedBattleId.value) return
  const confirmed = window.confirm('Завершить батл? После завершения его можно будет удалить.')
  if (!confirmed) return
  await api.post(`/battles/${selectedBattleId.value}/finish`)
  notify('Битва завершена', 'bonus', { burst: true, banner: 'БАТЛ ЗАВЕРШЕН' })
  await syncData()
}

async function deleteBattle() {
  if (!selectedBattleId.value || selectedBattle.value?.status !== 'finished') return
  const confirmed = window.confirm('Удалить завершенный батл? Это действие нельзя отменить.')
  if (!confirmed) return

  await api.delete(`/battles/${selectedBattleId.value}`)
  notify('Битва удалена', 'warning')
  selectedBattleId.value = null
  selectedBattleRoomLog.value = null
  battleTasks.value = []
  battlePackages.value = []
  battleLogs.value = []
  queue.entries = []
  queue.meta = null
  leaderboard.participants = []
  await syncData()
  await goToBattlesPage()
}

async function addPackageToBattle(packageId) {
  if (!selectedBattleId.value) return
  await api.post(`/battles/${selectedBattleId.value}/task-packages/${packageId}`)
  await loadBattleContext()
}

async function removePackageFromBattle(packageId) {
  if (!selectedBattleId.value) return
  await api.delete(`/battles/${selectedBattleId.value}/task-packages/${packageId}`)
  await loadBattleContext()
}

async function onInviteJoined() {
  await router.push(isTeacher.value ? '/play' : '/')
  await syncData()
}

async function resumeBattle(battleId) {
  try {
    if (myRoom.battle_id !== battleId || !myRoom.room_id) {
      await api.post(`/battles/${battleId}/queue/join`)
    }
    await router.push(isTeacher.value ? '/play' : '/')
    await syncData()
  } catch (error) {
    notify(error?.response?.data?.error?.message || 'Не удалось вернуться в батл', 'warning')
  }
}

function onInviteSaved(code) {
  if (selectedBattle.value) selectedBattle.value.invite_code = code
}

function openStudentReport({ studentId, taskId }) {
  router.push({ path: `/battles/${selectedBattleId.value}/students/${studentId}`, query: taskId ? { task: taskId } : {} })
}

async function readyQueue() {
  if (!selectedBattleId.value) return
  const { data } = await api.post(`/battles/${selectedBattleId.value}/queue/ready`)
  if (data.created_rooms?.length) {
    notify(`Стартовал раунд: ${data.created_rooms.length} комнат`, 'bonus', {
      burst: true,
      banner: 'ПОЕХАЛИ!'
    })
  }
  await syncData()
  await loadLeaderboard().catch(() => {})
}

async function leaveQueue() {
  if (!selectedBattleId.value) return
  await api.post(`/battles/${selectedBattleId.value}/queue/leave`)
  studentJoinedBattleId.value = null
  await syncData()
  await loadLeaderboard().catch(() => {})
}

async function loadQueue(battleId = selectedBattleId.value) {
  if (!battleId) return null
  const { data } = await api.get(`/battles/${battleId}/queue`)
  queue.entries = data.entries || []
  queue.meta = data.matchmaking || null
  return data
}

async function loadLeaderboard(battleId = selectedBattleId.value) {
  if (!battleId) return
  const meId = me.value?.id
  const previousPoints = meId ? leaderboardPointsMemo[`${battleId}:${meId}`] : null
  const { data } = await api.get(`/battles/${battleId}/leaderboard`)
  leaderboard.participants = data.participants || []
  if (meId) {
    const current = leaderboard.participants.find((p) => p.user_id === meId)
    const currentPoints = Number(current?.season_points ?? 0)
    leaderboardPointsMemo[`${battleId}:${meId}`] = currentPoints
    if (showPlayerUi.value && Number.isFinite(previousPoints) && currentPoints > previousPoints) {
      const delta = currentPoints - previousPoints
      notify(`Бонус: +${delta} очк.`, 'bonus', {
        burst: true,
        intensity: delta >= 3 ? 'high' : 'normal',
        banner: `+${delta} ОЧКОВ`
      })
    }
  }
}

async function loadBattleLogs() {
  if (!selectedBattleId.value || !showTeacherConsole.value) return
  const { data } = await api.get(`/battles/${selectedBattleId.value}/logs`)
  battleLogs.value = Array.isArray(data) ? data : []
}

async function openBattleRoomLog(roomId) {
  if (!selectedBattleId.value || !roomId) return
  await router.push(`/battles/${selectedBattleId.value}/rooms/${roomId}`)
}

async function goToBattleDetailsPage() {
  if (!selectedBattleId.value) {
    await router.push('/battles')
    return
  }
  await router.push(`/battles/${selectedBattleId.value}`)
}

async function loadSelectedBattleRoomLog(roomId = route.params.roomId ? String(route.params.roomId) : null) {
  if (!selectedBattleId.value || !roomId || !showTeacherConsole.value) {
    selectedBattleRoomLog.value = null
    return
  }
  const { data } = await api.get(`/battles/${selectedBattleId.value}/rooms/${roomId}/logs`)
  selectedBattleRoomLog.value = data || null
}

async function recheckSubmissionFromRoomLog(payload) {
  const submissionId = payload?.submissionId
  if (!selectedBattleId.value || !submissionId) return
  if (recheckingSubmissionIds.value.includes(submissionId)) return

  recheckingSubmissionIds.value = [...recheckingSubmissionIds.value, submissionId]
  try {
    await api.post(`/battles/${selectedBattleId.value}/submissions/${submissionId}/recheck`)
    notify('Посылка отправлена на перепроверку', 'success')
    await loadSelectedBattleRoomLog().catch(() => {})
    await loadBattleLogs().catch(() => {})
  } catch {
    notify('Не удалось отправить посылку на перепроверку', 'error')
  } finally {
    recheckingSubmissionIds.value = recheckingSubmissionIds.value.filter((id) => id !== submissionId)
  }
}

async function loadTaskPackages() {
  const { data } = await api.get('/task-packages')
  taskPackages.value = data || []
  if (selectedTaskPackageId.value && !taskPackages.value.find((p) => p.id === selectedTaskPackageId.value)) {
    selectedTaskPackageId.value = null
    selectedTaskPackage.value = null
    selectedPackageTaskId.value = null
  }
}

async function loadBattlePackages() {
  if (!selectedBattleId.value) return
  const { data } = await api.get(`/battles/${selectedBattleId.value}/task-packages`)
  battlePackages.value = data || []
}

async function loadBattleTasks() {
  if (!selectedBattleId.value) return
  const { data } = await api.get(`/battles/${selectedBattleId.value}/tasks`)
  battleTasks.value = data
}

async function loadCurrentRoom() {
  if (!myRoom.room_id) return
  const roomId = myRoom.room_id
  const epoch = sessionEpoch
  const roomRes = await api.get(`/rooms/${roomId}`)
  if (epoch !== sessionEpoch || myRoom.room_id !== roomId) return
  roomData.status = roomRes.data.status
  roomData.participants = roomRes.data.participants || []
  roomData.task = roomRes.data.task || null
  roomData.grace = roomRes.data.grace || null
  roomData.round = roomRes.data.round || null
  roomData.mySubmission = roomRes.data.my_submission || null
  isSubmissionChecking.value = roomData.mySubmission?.verdict === 'queued'
  scheduleGraceRefresh()
  subscribeSocket()
}

async function submitCode() {
  if (!myRoom.room_id) return
  if (isSubmissionChecking.value || isSubmitting.value) return
  isSubmitting.value = true
  isSubmissionChecking.value = true
  try {
    await api.post(`/rooms/${myRoom.room_id}/submit`, submitForm)
    await syncData()
    notify('Решение отправлено на проверку', 'success')
  } catch (error) {
    const isPendingConflict = error?.response?.status === 409
      && error?.response?.data?.error?.message === 'Previous submission is still being checked'
    isSubmissionChecking.value = isPendingConflict ? true : false
    notify(isPendingConflict ? 'Предыдущее решение ещё проверяется' : 'Не удалось отправить решение', isPendingConflict ? 'warning' : 'error')
  } finally { isSubmitting.value = false }
}

async function surrenderRound() {
  if (!myRoom.room_id) return
  const confirmed = window.confirm('Сдаться в этом раунде и перейти к следующему?')
  if (!confirmed) return
  try {
    await api.post(`/rooms/${myRoom.room_id}/surrender`)
    notify('Вы сдались. Ожидаем следующий раунд.', 'warning')
    await loadCurrentRoom()
  } catch {
    notify('Сдаться сейчас нельзя', 'warning')
  }
}

async function loadBattleContext() {
  if (!selectedBattleId.value) return
  const jobs = [loadQueue(), loadLeaderboard()]
  if (isTeacher.value) jobs.push(loadBattleTasks(), loadBattlePackages())
  if (showTeacherConsole.value) jobs.push(loadBattleLogs())
  if (showTeacherConsole.value && isBattleRoomLogPage.value) jobs.push(loadSelectedBattleRoomLog())
  await Promise.all(jobs)
}

async function syncSnapshot() {
  const previousBattleId = studentJoinedBattleId.value
  const epoch = sessionEpoch
  await loadBattles()
  if (epoch !== sessionEpoch || !me.value) return
  if (showTeacherConsole.value) {
    await loadTaskPackages()
    if (route.params.packageId && selectedTaskPackageId.value !== String(route.params.packageId)) {
      await selectTaskPackage(String(route.params.packageId))
    }
    if (route.params.taskId && selectedPackageTaskId.value !== String(route.params.taskId)) {
      const task = selectedTaskPackage.value?.tasks?.find(t => t.id === String(route.params.taskId))
      if (task) selectPackageTask(task)
    }
    if ((isBattleDetailsPage.value || isBattleRoomLogPage.value) && selectedBattleId.value) await loadBattleContext()
    return
  }
  const { data } = await api.get('/me/state')
  if (epoch !== sessionEpoch || !me.value) return
  me.value = data.me
  streak.value = Number(data.me.win_streak || 0)
  lastResult.value = data.last_result
  selectedBattleId.value = data.battle_id
  studentJoinedBattleId.value = data.battle_id
  myRoom.room_id = data.room_id
  myRoom.match_id = data.match_id
  myRoom.battle_id = data.battle_id
  if (data.room_id) await loadCurrentRoom()
  else {
    roomData.task = null
    roomData.mySubmission = null
    isSubmissionChecking.value = false
    clearGraceRefreshTimer()
    if (data.battle_id) await Promise.all([loadQueue(), loadLeaderboard()])
    else { queue.entries = []; queue.meta = null; leaderboard.participants = [] }
  }
  subscribeSocket()
  if (previousBattleId && !data.battle_id && data.result_battle_id === previousBattleId && !isPersonalResults.value) {
    await router.push(`/results/${previousBattleId}`)
  }
}

function syncData() {
  const epoch = sessionEpoch
  if (syncPromise) { syncAgain = true; return syncPromise }
  syncPromise = (async () => {
    do {
      syncAgain = false
      await syncSnapshot()
      reportVersion.value += 1
      dataError.value = ''
    } while (syncAgain && me.value)
  })().catch((error) => {
    if (epoch !== sessionEpoch) return
    dataError.value = error?.response?.status === 401 ? 'Сессия завершена. Войдите снова.' : 'Не удалось обновить данные. Повторяем подключение…'
    if (error?.response?.status === 401) { me.value = null; socket?.disconnect() }
    throw error
  }).finally(() => { syncPromise = null })
  return syncPromise
}

function openTaskActionPanel(panel) {
  if (panel === 'create_task_in_package' && !selectedTaskPackageId.value) {
    notify('Сначала выберите пакет задач', 'warning')
    return
  }
  taskActionPanel.value = panel
}

function onTaskJsonSelected(event) {
  packageImportFile.value = event.target.files?.[0] || null
}

async function createTaskPackage() {
  const name = packageForm.name.trim()
  if (!name) {
    notify('Введите название пакета', 'warning')
    return
  }
  let importedTasks = []
  if (packageImportFile.value) {
    const text = await packageImportFile.value.text()
    let payload
    try {
      payload = JSON.parse(text)
    } catch {
      notify('Некорректный JSON файл', 'error')
      return
    }

    if (Array.isArray(payload)) {
      importedTasks = payload
    } else if (payload && Array.isArray(payload.tasks)) {
      importedTasks = payload.tasks
    } else {
      notify('В файле не найден массив задач', 'error')
      return
    }
  }

  const { data } = await api.post('/task-packages', {
    name,
    description: packageForm.description || null,
    tasks: importedTasks
  })
  importSummary.value = data
  notify(`Пакет создан: ${data.package.name}`, 'success')
  packageForm.name = ''
  packageForm.description = ''
  packageImportFile.value = null
  taskActionPanel.value = null
  await loadTaskPackages()
  if (data.package?.id) await router.push(`/packages/${data.package.id}`)
}

async function exportSelectedPackageToJson() {
  if (!selectedTaskPackageId.value) return
  const { data } = await api.get(`/task-packages/${selectedTaskPackageId.value}/export`)
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${selectedTaskPackage.value?.package?.name || 'task-package'}.json`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

async function selectTaskPackage(packageId, { resetTaskSelection = true } = {}) {
  selectedTaskPackageId.value = packageId
  if (resetTaskSelection) {
    selectedPackageTaskId.value = null
  }
  const { data } = await api.get(`/task-packages/${packageId}`)
  selectedTaskPackage.value = data
}

async function deleteSelectedTaskPackage() {
  if (!selectedTaskPackageId.value) return
  await api.delete(`/task-packages/${selectedTaskPackageId.value}`)
  notify('Пакет удален', 'warning')
  selectedTaskPackage.value = null
  selectedTaskPackageId.value = null
  selectedPackageTaskId.value = null
  await loadTaskPackages()
  await router.push('/packages')
}

function resetPackageTaskForm() {
  packageTaskForm.title = ''
  packageTaskForm.statement_md = ''
  packageTaskForm.difficulty = 'easy'
  packageTaskForm.check_type = 'tests'
  packageTaskForm.tests_json = '[]'
}

async function createTaskInSelectedPackage() {
  if (!selectedTaskPackageId.value) return
  const title = packageTaskForm.title.trim()
  const statement = packageTaskForm.statement_md.trim()
  if (!title || !statement) {
    notify('Заполните название и условие', 'warning')
    return
  }
  let tests
  try {
    tests = JSON.parse(packageTaskForm.tests_json || '[]')
    if (!Array.isArray(tests) || tests.some(t => !t || typeof t !== 'object' || !('input' in t) || !('expected' in t))) throw new Error('Invalid tests')
  } catch {
    notify('Некорректный JSON тестов', 'error')
    return
  }
  await api.post(`/task-packages/${selectedTaskPackageId.value}/tasks`, {
    title,
    statement_md: statement,
    difficulty: packageTaskForm.difficulty,
    check_type: packageTaskForm.check_type,
    config: { tests }
  })
  notify('Задача добавлена в пакет', 'success')
  taskActionPanel.value = null
  resetPackageTaskForm()
  await selectTaskPackage(selectedTaskPackageId.value)
}

function selectPackageTask(task) {
  selectedPackageTaskId.value = task.id
  packageTaskForm.title = task.title
  packageTaskForm.statement_md = task.statement_md
  packageTaskForm.difficulty = task.difficulty
  packageTaskForm.check_type = task.check_type
  packageTaskForm.tests_json = JSON.stringify(task.config?.tests || [], null, 2)
}

async function openTaskEditor(task) {
  selectPackageTask(task)
  if (selectedTaskPackageId.value) await router.push(`/packages/${selectedTaskPackageId.value}/tasks/${task.id}`)
}

async function saveSelectedPackageTask() {
  if (!selectedTaskPackageId.value || !selectedPackageTaskId.value) return
  let tests
  try {
    tests = JSON.parse(packageTaskForm.tests_json || '[]')
    if (!Array.isArray(tests) || tests.some(t => !t || typeof t !== 'object' || !('input' in t) || !('expected' in t))) throw new Error('Invalid tests')
  } catch {
    notify('Некорректный JSON тестов', 'error')
    return
  }
  await api.patch(`/task-packages/${selectedTaskPackageId.value}/tasks/${selectedPackageTaskId.value}`, {
    title: packageTaskForm.title,
    statement_md: packageTaskForm.statement_md,
    difficulty: packageTaskForm.difficulty,
    check_type: packageTaskForm.check_type,
    config: { ...selectedPackageTask.value?.config, tests }
  })
  notify('Задача обновлена', 'success')
  await selectTaskPackage(selectedTaskPackageId.value, { resetTaskSelection: false })
}

async function removeSelectedPackageTask() {
  if (!selectedTaskPackageId.value || !selectedPackageTaskId.value) return
  await api.delete(`/task-packages/${selectedTaskPackageId.value}/tasks/${selectedPackageTaskId.value}`)
  notify('Задача удалена из пакета', 'warning')
  selectedPackageTaskId.value = null
  resetPackageTaskForm()
  await selectTaskPackage(selectedTaskPackageId.value)
  closeTaskEditor()
}

onMounted(async () => {
  bindUnloadHandlers()
  document.addEventListener('visibilitychange', refreshOnFocus)
  window.addEventListener('online', refreshOnFocus)
  window.addEventListener('gcb-ui-error', reportUiError)
  refreshTimer = setInterval(() => { if (me.value && document.visibilityState === 'visible') syncData().catch(() => {}) }, 10000)
  try {
    await loadAuthOptions()
    await loadMe()
    authResolved.value = true

    if (me.value) {
      setupSocket()
      if (isTeacher.value && route.path === '/') await router.push('/battles')
      await syncData()
      subscribeSocket()
      return
    }

    if (route.query.auth_error) {
      dataError.value = 'Не удалось войти через GeekClass. Повторите вход.'
      return
    }
    if (authOptions.geekclassEnabled) {
      geekclassLogin()
      return
    }

  } catch {
    authResolved.value = true
    dataError.value = 'Не удалось загрузить приложение. Проверьте соединение и повторите.'
  } finally {
    initialSyncDone.value = true
  }
})

watch(
  () => route.fullPath,
  async () => {
    if (!authResolved.value) return

    if (me.value && !isTeacher.value && (route.path.startsWith('/packages') || route.path.startsWith('/battles') || route.path.startsWith('/play'))) {
      router.push('/')
      return
    }

    if (!isTeacher.value) return

    if (teacherPlayMode.value) {
      await syncData().catch(() => {})
      subscribeSocket()
      return
    }

    if (route.name === 'battle-details' || isStudentReportPage.value) {
      const routeBattleId = route.params.battleId ? String(route.params.battleId) : null
      if (!routeBattleId) {
        router.push('/battles')
        return
      }
      if (selectedBattleId.value !== routeBattleId) selectedBattleId.value = routeBattleId
      await loadBattleContext().catch(() => {})
      subscribeSocket()
      return
    }

    if (route.name === 'battle-room-log') {
      const routeBattleId = route.params.battleId ? String(route.params.battleId) : null
      const routeRoomId = route.params.roomId ? String(route.params.roomId) : null
      if (!routeBattleId || !routeRoomId) {
        router.push('/battles')
        return
      }
      if (selectedBattleId.value !== routeBattleId) selectedBattleId.value = routeBattleId
      const ok = await loadBattleContext().then(() => true).catch(() => false)
      if (!ok) {
        router.push('/battles')
        return
      }
      subscribeSocket()
      return
    }

    if (route.path.startsWith('/packages')) {
      await loadTaskPackages().catch(() => {})
      const routePackageId = route.params.packageId ? String(route.params.packageId) : null
      const routeTaskId = route.params.taskId ? String(route.params.taskId) : null

      if (routePackageId) {
        if (selectedTaskPackageId.value !== routePackageId) {
          const ok = await selectTaskPackage(routePackageId).then(() => true).catch(() => false)
          if (!ok) {
            router.push('/packages')
            return
          }
        }
      } else {
        selectedTaskPackageId.value = null
        selectedTaskPackage.value = null
      }

      if (routeTaskId && selectedTaskPackage.value) {
        const task = selectedTaskPackage.value.tasks?.find((t) => t.id === routeTaskId)
        if (task) selectPackageTask(task)
        else closeTaskEditor()
      }
    }
  }
)

watch(
  () => myRoom.room_id,
  (nextRoomId, prevRoomId) => {
    const nextId = nextRoomId ? String(nextRoomId) : null
    const prevId = prevRoomId ? String(prevRoomId) : null
    if (!nextId) {
      draftRoomId.value = null
      return
    }
    if (nextId === prevId && draftRoomId.value === nextId) {
      return
    }
    applyDraftForRoom(nextId)
  }
)

onUnmounted(() => {
  clearInterval(refreshTimer)
  clearTimeout(eventSyncTimer)
  document.removeEventListener('visibilitychange', refreshOnFocus)
  window.removeEventListener('online', refreshOnFocus)
  window.removeEventListener('gcb-ui-error', reportUiError)
  clearGraceRefreshTimer()
  unbindUnloadHandlers()
  if (socket) socket.disconnect()
})
</script>
