<template>
  <div class="app-shell">
    <AppTopbar
      :me="me"
      :is-teacher="isTeacher"
      :teacher-page="teacherPage"
      @go-battles="goToBattlesPage"
      @go-packages="goToPackagesPage"
      @go-play="goToPlayPage"
      @logout="logout"
    />

    <main class="container py-4">
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
        @dev-login="devLogin"
      />

      <template v-else>
        <template v-if="showTeacherConsole">
          <template v-if="teacherPage === 'battles'">
            <TeacherBattleRoomLogView
              v-if="isBattleRoomLogPage"
              :room-log="selectedBattleRoomLog"
              :rechecking-submission-ids="recheckingSubmissionIds"
              @back="goToBattleDetailsPage"
              @recheck-submission="recheckSubmissionFromRoomLog"
            />

            <TeacherBattleDetailsView
              v-else-if="isBattleDetailsPage"
              :selected-battle="selectedBattle"
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
            :code-extensions="codeExtensions"
            :is-checking="isSubmissionChecking"
            :opponent-activity="opponentActivity"
            :grace="roomData.grace"
            :round="roomData.round"
            :my-submission="roomData.mySubmission"
            @update:submit-language="submitForm.language = $event"
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

          <StudentBattleLobbyView
            v-else
            :battles="availableStudentBattles"
            @join-battle="joinBattle"
          />
        </template>
      </template>
    </main>

    <section
      class="toast-msg"
      :class="`toast-${toast.kind}`"
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
      <i class="bi" :class="audioEnabled ? 'bi-volume-up-fill' : 'bi-volume-mute-fill'" aria-hidden="true"></i>
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
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import api from './api'
import { io } from 'socket.io-client'
import { oneDark } from '@codemirror/theme-one-dark'
import { python } from '@codemirror/lang-python'
import { cpp } from '@codemirror/lang-cpp'
import { useRoute, useRouter } from 'vue-router'
import AppTopbar from './components/AppTopbar.vue'
import LoginCard from './components/LoginCard.vue'
import TeacherBattleListView from './components/teacher/TeacherBattleListView.vue'
import TeacherBattleDetailsView from './components/teacher/TeacherBattleDetailsView.vue'
import TeacherBattleRoomLogView from './components/teacher/TeacherBattleRoomLogView.vue'
import TeacherPackagesListView from './components/teacher/TeacherPackagesListView.vue'
import TeacherPackageDetailsView from './components/teacher/TeacherPackageDetailsView.vue'
import TeacherTaskEditorView from './components/teacher/TeacherTaskEditorView.vue'
import StudentActiveRoomView from './components/student/StudentActiveRoomView.vue'
import StudentBattleLobbyView from './components/student/StudentBattleLobbyView.vue'
import StudentJoinedBattleView from './components/student/StudentJoinedBattleView.vue'

const me = ref(null)
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
const audioEnabled = ref(true)
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
const opponentActivity = ref(null)
let socket = null
let graceRefreshTimer = null
let audioCtx = null
let unloadHandlersBound = false

const isTeacher = computed(() => me.value && (me.value.role === 'teacher' || me.value.role === 'admin'))
const teacherPage = computed(() => {
  if (route.path.startsWith('/packages')) return 'tasks'
  if (route.path.startsWith('/play')) return 'play'
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
const codeExtensions = computed(() => [oneDark, submitForm.language === 'cpp' ? cpp() : python()])
const activeBattleTitle = computed(() => battles.value.find((i) => i.id === myRoom.battle_id)?.title || null)
const selectedPackageTask = computed(() => selectedTaskPackage.value?.tasks?.find((t) => t.id === selectedPackageTaskId.value) || null)
const availableStudentBattles = computed(() => battles.value.filter((b) => b.status !== 'finished'))
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
  if (route.path !== '/battles') router.push('/battles')
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

function setupSocket() {
  if (socket) return
  socket = io('/', { withCredentials: true, closeOnBeforeunload: true })
  socket.on('connect', () => subscribeSocket())
  socket.on('queue_updated', () => loadQueue().catch(() => {}))
  socket.on('battle_status_changed', async () => { await syncData() })
  socket.on('match_found', async () => {
    notify('Найден новый раунд!', 'bonus', { burst: true, intensity: 'high', banner: 'НОВЫЙ РАУНД' })
    await syncData()
  })
  socket.on('submission_queued', async (payload) => {
    if (!payload?.student_id || !me.value) return
    if (!isEventForCurrentMatch(payload)) return
    if (payload.student_id !== me.value.id) {
      showOpponentActivity({
        kind: 'pending',
        message: `${findParticipantName(payload.student_id)} отправил посылку на проверку`
      })
    }
    if (showTeacherConsole.value && (isBattleDetailsPage.value || isBattleRoomLogPage.value)) {
      await loadBattleLogs().catch(() => {})
      if (isBattleRoomLogPage.value) await loadSelectedBattleRoomLog().catch(() => {})
    }
  })
  socket.on('submission_verdict', async (payload) => {
    if (!payload?.student_id || !me.value) return
    if (!isEventForCurrentMatch(payload)) return
    if (payload.student_id === me.value.id) {
      isSubmissionChecking.value = false
      const winnerStudentId = roomData.grace?.winner_student_id ? String(roomData.grace.winner_student_id) : null
      const currentStudentId = me.value?.id ? String(me.value.id) : null
      const acceptedAfterKnownWinner = Boolean(winnerStudentId && currentStudentId && winnerStudentId !== currentStudentId)
      if (payload.verdict === 'accepted') {
        streak.value += 1
        bestStreak.value = Math.max(bestStreak.value, streak.value)
        if (acceptedAfterKnownWinner) {
          notify('Решение принято, но соперник решил раньше', 'info')
        } else {
          notify('Правильно! Отличная отправка', 'bonus', { burst: true, intensity: 'high', banner: 'ПРАВИЛЬНЫЙ ОТВЕТ' })
        }
        if (!acceptedAfterKnownWinner && streak.value >= 2) {
          showBonusBanner(`COMBO x${streak.value}`)
        }
        if (showPlayerUi.value) {
          showRoundOverlay({
            title: acceptedAfterKnownWinner ? 'Задача решена, но победа у соперника' : 'Победа в раунде!',
            subtitle: acceptedAfterKnownWinner ? 'Раунд уже был выигран ранее. Переходим в лобби.' : 'Переходим в лобби и ждём следующий матч',
            deltaText: 'Нажмите «Готов», когда будете готовы'
          })
          myRoom.room_id = null
          myRoom.match_id = null
          roomData.status = null
          roomData.participants = []
          roomData.task = null
          roomData.grace = null
          roomData.round = null
          roomData.mySubmission = null
          opponentActivity.value = null
          subscribeSocket()
          await syncData()
          return
        }
      } else if (payload.verdict === 'wrong_answer') {
        streak.value = 0
        notify('Почти! Проверка не пройдена', 'warning')
      } else {
        streak.value = 0
        notify(`Результат: ${payload.verdict || 'получен'}`, 'info')
      }
    } else {
      const passed = payload.visible_tests_passed
      const total = payload.visible_tests_total
      const hasTests = Number.isInteger(passed) && Number.isInteger(total)
      const resultText = hasTests ? ` (${passed}/${total} тестов)` : ''
      const kind = payload.verdict === 'accepted' ? 'success' : (payload.verdict === 'wrong_answer' ? 'fail' : 'error')
      showOpponentActivity({
        kind,
        message: `${findParticipantName(payload.student_id)} получил результат: ${payload.verdict}${resultText}`
      })
    }
    await loadCurrentRoom()
    if (showTeacherConsole.value && (isBattleDetailsPage.value || isBattleRoomLogPage.value)) {
      await loadBattleLogs().catch(() => {})
      if (isBattleRoomLogPage.value) await loadSelectedBattleRoomLog().catch(() => {})
    }
  })
  socket.on('round_finished', async (payload) => {
    if (showPlayerUi.value && !isEventForCurrentMatch(payload)) return
    isSubmissionChecking.value = false
    const meId = me.value?.id
    const beforePoints = meId ? Number((leaderboard.participants.find((p) => p.user_id === meId)?.season_points ?? 0)) : null
    const beforeRank = meId ? leaderboard.participants.findIndex((p) => p.user_id === meId) + 1 : null

    notify('Раунд завершен', 'bonus', { burst: true, intensity: 'high', banner: 'ФИНИШ РАУНДА' })
    playSound('round_end')
    await syncData()

    if (showPlayerUi.value && meId) {
      const afterRank = leaderboard.participants.findIndex((p) => p.user_id === meId) + 1
      const afterPoints = Number((leaderboard.participants.find((p) => p.user_id === meId)?.season_points ?? 0))
      const delta = Number.isFinite(beforePoints) ? afterPoints - beforePoints : 0
      const rankShift = Number.isFinite(beforeRank) && beforeRank > 0 && afterRank > 0 ? (beforeRank - afterRank) : 0
      const rankText = afterRank > 0 ? `Позиция в таблице: #${afterRank}` : ''
      const deltaText = delta > 0 ? `+${delta} очков` : (delta < 0 ? `${delta} очков` : 'Очки без изменений')
      const streakText = streak.value > 1 ? `Текущая серия: x${streak.value}` : (bestStreak.value > 1 ? `Лучшая серия: x${bestStreak.value}` : '')
      showRoundOverlay({
        title: rankShift > 0 ? `Подъем на ${rankShift} поз.` : 'Раунд завершен',
        subtitle: rankShift > 0 ? 'Отличный рывок!' : 'Смотрим итог и готовимся к следующему',
        positionText: rankText,
        deltaText,
        streakText
      })
      if (delta > 0) {
        triggerBurst({ intensity: delta >= 3 ? 'high' : 'normal', originX: 52, originY: 44 })
      }
    }
  })
  socket.on('leaderboard_updated', () => loadLeaderboard().catch(() => {}))
  socket.on('presence_updated', async () => {
    if (myRoom.room_id) {
      await loadCurrentRoom().catch(() => {})
    }
    if (showTeacherConsole.value && isBattleRoomLogPage.value) {
      await loadSelectedBattleRoomLog().catch(() => {})
    }
  })
}

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
    return value === null ? null : String(value)
  } catch {
    return null
  }
}

function writeRoomDraft(roomId, sourceCode) {
  if (typeof window === 'undefined') return
  const key = draftStorageKey(roomId)
  if (!key) return
  try {
    window.localStorage.setItem(key, String(sourceCode ?? ''))
  } catch {}
}

function applyDraftForRoom(roomId) {
  if (!roomId) {
    draftRoomId.value = null
    return
  }
  const stored = readRoomDraft(roomId)
  submitForm.source_code = stored !== null ? stored : DEFAULT_ROOM_SOURCE_CODE
  draftRoomId.value = String(roomId)
}

function updateSubmitCode(nextCode) {
  submitForm.source_code = nextCode
  if (myRoom.room_id) {
    writeRoomDraft(myRoom.room_id, submitForm.source_code)
  }
}

async function devLogin() {
  if (!authOptions.devLoginEnabled) {
    notify('Тестовый вход отключен', 'warning')
    return
  }
  initialSyncDone.value = false
  const { data } = await api.post('/auth/dev-login', loginForm)
  me.value = data
  authResolved.value = true
  setupSocket()
  await syncData()
  initialSyncDone.value = true
  subscribeSocket()
}

async function loadAuthOptions() {
  try {
    const { data } = await api.get('/auth/options')
    authOptions.devLoginEnabled = Boolean(data?.dev_login_enabled)
    authOptions.geekclassEnabled = Boolean(data?.geekclass_enabled ?? true)
  } catch {
    authOptions.devLoginEnabled = false
    authOptions.geekclassEnabled = true
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
  } catch {
    me.value = null
  }
}

async function loadBattles() {
  const { data } = await api.get('/battles')
  battles.value = data
  if (showTeacherConsole.value && !selectedBattleId.value && battles.value.length) {
    selectedBattleId.value = battles.value[0].id
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

async function joinQueue() {
  if (!selectedBattleId.value) return
  const { data } = await api.post(`/battles/${selectedBattleId.value}/queue/join`)
  if (data.created_rooms?.length) notify(`Найдено комнат: ${data.created_rooms.length}`, 'success')
  await syncData()
}

async function joinBattle(battleId) {
  selectedBattleId.value = battleId
  await joinQueue()
  studentJoinedBattleId.value = battleId
  await Promise.all([loadQueue(), loadLeaderboard(battleId)])
  subscribeSocket()
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
  const roomRes = await api.get(`/rooms/${myRoom.room_id}`)
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

async function detectStudentActiveRoom() {
  if (!me.value || !showPlayerUi.value) return false
  for (const battle of battles.value) {
    const { data } = await api.get(`/battles/${battle.id}/my-room`)
    if (data.room_id) {
      myRoom.room_id = data.room_id
      myRoom.match_id = data.match_id
      myRoom.battle_id = battle.id
      selectedBattleId.value = battle.id
      studentJoinedBattleId.value = battle.id
      await loadCurrentRoom()
      return true
    }
  }
  myRoom.room_id = null
  myRoom.match_id = null
  myRoom.battle_id = null
  roomData.status = null
  roomData.participants = []
  roomData.task = null
  roomData.grace = null
  roomData.round = null
  roomData.mySubmission = null
  opponentActivity.value = null
  clearGraceRefreshTimer()
  return false
}

async function detectStudentJoinedBattle() {
  if (!me.value || !showPlayerUi.value) return false

  const candidateBattleIds = []
  if (studentJoinedBattleId.value) {
    candidateBattleIds.push(studentJoinedBattleId.value)
  }
  candidateBattleIds.push(...battles.value.map((b) => b.id).filter((id) => id !== studentJoinedBattleId.value))

  for (const battleId of candidateBattleIds) {
    const data = await loadQueue(battleId)
    const joined = (data?.entries || []).some((e) => e.user_id === me.value.id)
    if (joined) {
      selectedBattleId.value = battleId
      studentJoinedBattleId.value = battleId
      await loadLeaderboard(battleId).catch(() => {})
      return true
    }
  }

  studentJoinedBattleId.value = null
  selectedBattleId.value = null
  queue.entries = []
  queue.meta = null
  return false
}

async function submitCode() {
  if (!myRoom.room_id) return
  if (isSubmissionChecking.value) return
  try {
    await api.post(`/rooms/${myRoom.room_id}/submit`, submitForm)
    isSubmissionChecking.value = true
    notify('Решение отправлено на проверку', 'success')
  } catch (error) {
    const isPendingConflict = error?.response?.status === 409
      && error?.response?.data?.error?.message === 'Previous submission is still being checked'
    isSubmissionChecking.value = isPendingConflict ? true : false
    notify(isPendingConflict ? 'Предыдущее решение ещё проверяется' : 'Не удалось отправить решение', isPendingConflict ? 'warning' : 'error')
  }
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
  const jobs = [loadQueue(), loadLeaderboard(), loadBattleTasks(), loadBattlePackages()]
  if (showTeacherConsole.value) jobs.push(loadBattleLogs())
  if (showTeacherConsole.value && isBattleRoomLogPage.value) jobs.push(loadSelectedBattleRoomLog())
  await Promise.all(jobs)
}

async function syncData() {
  await loadBattles()

  if (showTeacherConsole.value) {
    await loadTaskPackages()
    if ((isBattleDetailsPage.value || isBattleRoomLogPage.value) && selectedBattleId.value) await loadBattleContext()
    return
  }

  const hasActiveRoom = await detectStudentActiveRoom()
  if (!hasActiveRoom) {
    await detectStudentJoinedBattle()
  }
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
  } catch {
    notify('Некорректный JSON тестов', 'error')
    return
  }
  await api.patch(`/task-packages/${selectedTaskPackageId.value}/tasks/${selectedPackageTaskId.value}`, {
    title: packageTaskForm.title,
    statement_md: packageTaskForm.statement_md,
    difficulty: packageTaskForm.difficulty,
    check_type: packageTaskForm.check_type,
    config: { tests }
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

    if (authOptions.geekclassEnabled) {
      geekclassLogin()
      return
    }

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

    if (route.name === 'battle-details') {
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
  clearGraceRefreshTimer()
  unbindUnloadHandlers()
  if (socket) socket.disconnect()
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
  --app-bg: #f4f7ff;
  --app-bg-soft: #eaf0ff;
  --app-ink: #15213b;
  --app-muted: #5f6d89;
  --app-border: #d8deee;
  --app-card: #ffffff;
  --app-brand: #2b5fff;
  --app-brand-strong: #1f4ae0;
  --app-accent: #0ea5a4;
}

body {
  font-family: 'Manrope', 'Segoe UI', sans-serif;
  color: var(--app-ink);
  background: var(--app-bg);
}

a {
  color: inherit;
}

.app-shell {
  position: relative;
  min-height: 100vh;
  background:
    radial-gradient(circle at 12% -5%, #dbe6ff 0%, rgba(219, 230, 255, 0) 45%),
    radial-gradient(circle at 88% 0%, #d8f4f4 0%, rgba(216, 244, 244, 0) 34%),
    linear-gradient(160deg, var(--app-bg) 0%, var(--app-bg-soft) 100%);
}

.app-topbar {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(216, 222, 238, 0.8);
  box-shadow: 0 10px 30px rgba(32, 51, 92, 0.08);
}

.app-brand {
  letter-spacing: 0.02em;
  color: #13264f;
}

.brand-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(135deg, #2b5fff 0%, #0ea5a4 100%);
  box-shadow: 0 0 0 4px rgba(43, 95, 255, 0.12);
}

.container.py-4 {
  position: relative;
  z-index: 1;
  max-width: 1120px;
}

.card {
  border: 1px solid var(--app-border) !important;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fdfefe 100%);
  box-shadow: 0 12px 30px rgba(31, 58, 120, 0.08) !important;
  animation: card-enter 220ms ease-out;
}

.card .card-body {
  padding: 1.2rem;
}

.form-control,
.form-select {
  border: 1px solid var(--app-border);
  background: #fdfefe;
}

.form-control:focus,
.form-select:focus {
  border-color: #93b1ff;
  box-shadow: 0 0 0 0.2rem rgba(43, 95, 255, 0.14);
}

.btn {
  border-radius: 10px;
  font-weight: 600;
  min-height: 40px;
  transition: transform 140ms ease, box-shadow 140ms ease, background-color 140ms ease, color 140ms ease;
}

.btn:hover {
  transform: translateY(-1px);
}

.btn-primary {
  background: linear-gradient(135deg, var(--app-brand) 0%, var(--app-brand-strong) 100%);
  border-color: transparent;
  box-shadow: 0 8px 18px rgba(43, 95, 255, 0.2);
}

.btn-primary:hover,
.btn-primary:focus {
  background: linear-gradient(135deg, var(--app-brand-strong) 0%, #173dbd 100%);
}

.btn-outline-primary {
  color: var(--app-brand);
  border-color: rgba(43, 95, 255, 0.45);
}

.btn-outline-primary:hover {
  background: rgba(43, 95, 255, 0.08);
  color: var(--app-brand-strong);
}

.btn-outline-secondary {
  color: #3f4d69;
  border-color: rgba(95, 109, 137, 0.4);
}

.btn-outline-warning {
  color: #9a6200;
  border-color: rgba(229, 160, 0, 0.45);
}

.btn-outline-warning:hover {
  background: rgba(229, 160, 0, 0.12);
  color: #7a4d00;
}

.text-muted {
  color: var(--app-muted) !important;
}

.form-control,
.form-select {
  min-height: 42px;
}

button:focus-visible,
.btn:focus-visible,
.form-control:focus-visible,
.form-select:focus-visible,
a:focus-visible {
  outline: 2px solid rgba(14, 165, 164, 0.9);
  outline-offset: 2px;
}

.elevated-panel {
  background: linear-gradient(180deg, #f9fbff 0%, #f4f8ff 100%);
  border: 1px solid #d7e2f6;
  border-radius: 12px;
  padding: 1rem;
}

.list-group-item {
  border-color: #e2e8f5;
  transition: background-color 140ms ease, border-color 140ms ease;
}

.list-group-item:hover {
  background: #f4f8ff;
  border-color: #cfd9ef;
}

.list-group-item.active {
  background: rgba(43, 95, 255, 0.9);
  border-color: rgba(43, 95, 255, 0.9);
}

.app-list-item {
  border-radius: 10px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  border: 1px solid transparent;
}

.presence-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 10px;
}

.presence-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.85), 0 0 0 1px rgba(117, 132, 163, 0.32);
}

.presence-dot.online {
  background: #16a34a;
}

.presence-dot.offline {
  background: #dc2626;
}

.status-draft {
  background: #edf1f8;
  color: #5b6780;
  border-color: #d6dfef;
}

.status-lobby_open {
  background: #e7f6ff;
  color: #1562a2;
  border-color: #cde9fa;
}

.status-running {
  background: #e8f9ef;
  color: #1d7d3f;
  border-color: #caeed7;
}

.status-stopped {
  background: #fff6e9;
  color: #9c6206;
  border-color: #f8e2bd;
}

.status-finished {
  background: #f1ecff;
  color: #5f45ad;
  border-color: #dfd5f8;
}

.difficulty-easy {
  background: #e7f8ee;
  color: #1f7a40;
  border-color: #c7e9d4;
}

.difficulty-medium {
  background: #fff8e8;
  color: #8c6100;
  border-color: #f1dfb6;
}

.difficulty-hard {
  background: #ffeef0;
  color: #a12938;
  border-color: #f8d0d5;
}

.action-ribbon {
  padding: 0.6rem;
  border-radius: 12px;
  background: #f7faff;
  border: 1px solid #dbe4f8;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 38px;
}

.action-btn-sm {
  min-height: 32px;
  font-size: 0.84rem;
}

.soft-panel {
  border: 1px solid #dbe4f8;
  border-radius: 12px;
  background: linear-gradient(180deg, #fbfdff 0%, #f7faff 100%);
  padding: 0.9rem;
}

.participant-tile {
  border: 1px solid #d8e1f2;
  border-radius: 10px;
  padding: 0.55rem 0.65rem;
  background: #fbfdff;
}

.empty-state {
  padding: 1rem;
  border-radius: 12px;
  border: 1px dashed #cbd7ef;
  background: #f8fbff;
  color: var(--app-muted);
  font-size: 0.92rem;
}

.editor-textarea {
  min-height: 120px;
}

.code-like {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.88rem;
}

.table {
  --bs-table-bg: #fbfdff;
}

.table th {
  color: #1b325d;
  font-weight: 700;
}

.table td,
.table th {
  vertical-align: middle;
}

.table pre {
  white-space: pre-wrap;
  word-break: break-word;
}

.table-light {
  --bs-table-bg: #edf4ff;
}

.badge.text-bg-primary {
  background-color: var(--app-accent) !important;
}

.battle-list {
  max-height: 60vh;
  overflow: auto;
  scrollbar-width: thin;
  scrollbar-color: #b8c7e8 transparent;
}

.task-pre {
  background: #0f172a;
  color: #e6eef9;
  font-family: 'JetBrains Mono', monospace;
  border-radius: 12px;
  padding: 12px;
  white-space: pre-wrap;
  margin: 0;
  box-shadow: inset 0 0 0 1px rgba(203, 213, 225, 0.15);
}

.code-editor {
  border: 1px solid #cfd8eb;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 18px rgba(27, 39, 72, 0.1);
}

.icon-btn {
  min-width: 38px;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.toast-msg {
  position: fixed;
  right: 16px;
  bottom: 16px;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  color: #fff;
  padding: 11px 15px;
  border-radius: 12px;
  border: 1px solid transparent;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.24);
  z-index: 1000;
  animation: toast-in 230ms ease-out;
}

.toast-icon {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.24);
  font-weight: 800;
}

.toast-info {
  background: linear-gradient(135deg, #1f2a44 0%, #111827 100%);
}

.toast-success {
  background: linear-gradient(135deg, #0e9f6e 0%, #047857 100%);
}

.toast-warning {
  background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
}

.toast-error {
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
}

.toast-bonus {
  background: linear-gradient(135deg, #ff6a00 0%, #ff2d95 48%, #6f45ff 100%);
  border-color: rgba(255, 255, 255, 0.35);
  animation: toast-in 230ms ease-out, bonus-pulse 560ms ease-out 1;
}

.bonus-banner {
  position: fixed;
  left: 50%;
  top: 78px;
  transform: translateX(-50%);
  z-index: 1150;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  color: #fff;
  font-weight: 800;
  font-size: 0.9rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: linear-gradient(135deg, #ff7a18 0%, #ff2d95 55%, #6f45ff 100%);
  box-shadow: 0 14px 30px rgba(111, 69, 255, 0.3);
  animation: banner-pop 360ms cubic-bezier(0.22, 1, 0.36, 1);
}

.burst-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1100;
  overflow: hidden;
}

.burst-dot {
  position: absolute;
  width: var(--sz);
  height: var(--sz);
  border-radius: 2px;
  background: hsl(var(--h), 94%, 58%);
  transform: translate(0, 0) rotate(0deg);
  opacity: 0.96;
  box-shadow: 0 0 10px hsla(var(--h), 96%, 56%, 0.55);
  animation: burst-flight 940ms cubic-bezier(0.16, 0.84, 0.28, 1) forwards;
}

.sound-toggle {
  position: fixed;
  left: 16px;
  bottom: 16px;
  z-index: 1060;
  width: 42px;
  height: 42px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(20, 37, 74, 0.22);
}

.streak-chip {
  position: fixed;
  right: 16px;
  top: 78px;
  z-index: 1080;
  padding: 0.42rem 0.72rem;
  border-radius: 999px;
  color: #fff;
  font-weight: 800;
  background: linear-gradient(135deg, #ff7a18 0%, #ff2d95 60%, #6f45ff 100%);
  box-shadow: 0 12px 24px rgba(255, 45, 149, 0.25);
  animation: banner-pop 320ms ease-out;
}

.round-overlay {
  position: fixed;
  inset: 0;
  z-index: 1120;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  padding: 1rem;
  background: rgba(14, 21, 38, 0.38);
  backdrop-filter: blur(2px);
}

.round-overlay-card {
  width: min(460px, 100%);
  border-radius: 18px;
  padding: 1.2rem 1.3rem;
  color: #fff;
  background: linear-gradient(135deg, #ff7a18 0%, #ff2d95 52%, #6f45ff 100%);
  border: 1px solid rgba(255, 255, 255, 0.36);
  box-shadow: 0 22px 42px rgba(18, 18, 36, 0.35);
  animation: overlay-pop 280ms cubic-bezier(0.22, 1, 0.36, 1);
}

.round-overlay-card .text-muted {
  color: rgba(255, 255, 255, 0.82) !important;
}

.bonus-score {
  font-size: 1.28rem;
  font-weight: 900;
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes bonus-pulse {
  0% {
    filter: saturate(1.1);
  }
  65% {
    filter: saturate(1.55);
  }
  100% {
    filter: saturate(1);
  }
}

@keyframes banner-pop {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px) scale(0.92);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0) scale(1);
  }
}

@keyframes burst-flight {
  0% {
    opacity: 0.96;
    transform: translate(0, 0) rotate(0deg) scale(1);
  }
  100% {
    opacity: 0;
    transform: translate(var(--dx), var(--dy)) rotate(var(--dr)) scale(0.35);
  }
}

@keyframes overlay-pop {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 768px) {
  .container.py-4 {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }

  .card .card-body {
    padding: 1rem;
  }

  .action-btn {
    width: 100%;
    justify-content: center;
  }

  .btn-group > .btn {
    padding-left: 0.6rem;
    padding-right: 0.6rem;
  }

  .app-brand {
    font-size: 1rem;
  }

  .task-pre {
    font-size: 0.86rem;
  }

  .table {
    font-size: 0.88rem;
  }

  .bonus-banner {
    top: 70px;
    font-size: 0.8rem;
  }

  .streak-chip {
    top: 64px;
    font-size: 0.8rem;
  }

  .sound-toggle {
    width: 40px;
    height: 40px;
    left: 12px;
    bottom: 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation: none !important;
    transition: none !important;
  }
}
</style>
