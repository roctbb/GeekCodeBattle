// Load vendor styles before component styles and the product theme.
import 'bootstrap/dist/css/bootstrap.min.css'
import '@fortawesome/fontawesome-svg-core/styles.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/theme.css'
const app = createApp(App)
app.config.errorHandler = (error) => {
  console.error(error)
  const messages = {
    'Scored battles must be retained for rating history': 'Сражение с начисленными очками нельзя удалить: оно нужно для истории рейтинга.',
    'Finish the round before rejudging': 'Сначала завершите раунд.',
  }
  const serverMessage = error?.response?.data?.error?.message
  window.dispatchEvent(new CustomEvent('gcb-ui-error', { detail: messages[serverMessage] || 'Не удалось выполнить действие. Проверьте данные и попробуйте ещё раз.' }))
}
app.use(createPinia()).use(router).mount('#app')
