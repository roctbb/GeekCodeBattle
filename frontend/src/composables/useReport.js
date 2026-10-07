import { ref, watch, onUnmounted } from 'vue'
import api from '../api'

export function useReport(path, refreshKey) {
  const data = ref(null),
    loading = ref(true),
    error = ref('')
  let generation = 0
  async function reload() {
    const current = ++generation
    error.value = ''
    loading.value = !data.value
    try {
      const response = await api.get(path())
      if (current === generation) data.value = response.data
    } catch (e) {
      if (current === generation)
        error.value =
          e.response?.data?.error?.message ||
          'Не удалось загрузить данные. Попробуйте ещё раз.'
    } finally {
      if (current === generation) loading.value = false
    }
  }
  watch(
    path,
    () => {
      data.value = null
      reload()
    },
    { immediate: true },
  )
  if (refreshKey) watch(refreshKey, reload)
  onUnmounted(() => {
    generation++
  })
  return { data, loading, error, reload }
}
