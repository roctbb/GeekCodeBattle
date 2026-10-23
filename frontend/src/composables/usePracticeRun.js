import { onUnmounted, ref, watch } from 'vue'
import api from '../api'

export function usePracticeRun(roomId) {
  const result = ref(null),
    running = ref(false),
    error = ref('')
  let timer,
    controller,
    epoch = 0
  function reset() {
    epoch++
    clearTimeout(timer)
    controller?.abort()
    running.value = false
    result.value = null
    error.value = ''
  }
  watch(roomId, reset)
  onUnmounted(reset)
  async function run(payload) {
    if (running.value || !roomId()) return
    const room = roomId(),
      version = ++epoch
    controller = new AbortController()
    running.value = true
    error.value = ''
    result.value = null
    const started = Date.now(),
      options = { signal: controller.signal }
    const accept = (data) => {
      if (epoch !== version) return
      result.value = data
      if (data.verdict !== 'queued') running.value = false
    }
    async function poll(id) {
      try {
        const { data } = await api.get(`/rooms/${room}/runs/${id}`, options)
        if (epoch !== version) return
        accept(data)
        if (data.verdict === 'queued') {
          if (Date.now() - started > ((Number(data.timeout_seconds) || 600) + 10) * 1000) {
            error.value = 'Проверка задерживается. Повторите запуск.'
            running.value = false
            return
          }
          timer = setTimeout(() => poll(id), 1200)
        }
      } catch (e) {
        if (epoch === version) {
          running.value = false
          error.value =
            'Не удалось получить результат запуска. Повторите попытку.'
        }
      }
    }
    try {
      const { data } = await api.post(`/rooms/${room}/runs`, payload, options)
      if (epoch !== version) return
      accept(data)
      if (data.verdict === 'queued')
        timer = setTimeout(() => poll(data.id), 800)
    } catch (e) {
      if (epoch === version) {
        const previousRunId = e.response?.data?.error?.details?.run_id
        if (e.response?.status === 409 && previousRunId &&
            e.response?.data?.error?.message === 'Previous run is still being checked') {
          // Recover a pending run after visiting solution history or reconnecting.
          await poll(previousRunId)
          return
        }
        running.value = false
        error.value =
          {
            'Previous run is still being checked':
              'Предыдущий запуск ещё проверяется.',
            'Round has not started yet': 'Дождитесь начала раунда.',
            'Round is already finished': 'Раунд завершён.',
            'Practice limit reached: 100 runs per round':
              'Достигнут лимит 100 пробных запусков за раунд.',
          }[e.response?.data?.error?.message] ||
          'Не удалось запустить код. Проверьте соединение и повторите.'
      }
    }
  }
  return { result, running, error, run }
}
