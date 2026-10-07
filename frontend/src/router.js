import { createRouter, createWebHistory } from 'vue-router'

const EmptyView = { template: '<div />' }

const routes = [
  { path: '/', name: 'home', component: EmptyView },
  { path: '/results', name: 'my-results', component: EmptyView },
  { path: '/results/:battleId', name: 'my-result-detail', component: EmptyView },
  { path: '/battles/:battleId/students/:studentId', name: 'battle-student-results', component: EmptyView },
  { path: '/play', name: 'play', component: EmptyView },
  { path: '/battles', name: 'battles', component: EmptyView },
  { path: '/battles/:battleId', name: 'battle-details', component: EmptyView },
  { path: '/battles/:battleId/rooms/:roomId', name: 'battle-room-log', component: EmptyView },
  { path: '/packages', name: 'packages', component: EmptyView },
  { path: '/packages/:packageId', name: 'package-details', component: EmptyView },
  { path: '/packages/:packageId/tasks/:taskId', name: 'package-task-editor', component: EmptyView },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || { top: 0 }
  },
})

export default router
