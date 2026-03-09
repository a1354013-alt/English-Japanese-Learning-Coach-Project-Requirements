import { createRouter, createWebHistory } from 'vue-router'
import TodayLesson from './views/TodayLesson.vue'
import Progress from './views/Progress.vue'
import Archive from './views/Archive.vue'
import WritingCenter from './views/WritingCenter.vue'

const routes = [
  {
    path: '/',
    name: 'TodayLesson',
    component: TodayLesson
  },
  {
    path: '/progress',
    name: 'Progress',
    component: Progress
  },
  {
    path: '/archive',
    name: 'Archive',
    component: Archive
  },
  {
    path: '/writing',
    name: 'WritingCenter',
    component: WritingCenter
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
