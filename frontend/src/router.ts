import { createRouter, createWebHistory } from 'vue-router'
import Archive from '@/views/Archive.vue'
import LessonDetail from '@/views/LessonDetail.vue'
import Progress from '@/views/Progress.vue'
import TodayLesson from '@/views/TodayLesson.vue'
import WritingCenter from '@/views/WritingCenter.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'TodayLesson', component: TodayLesson },
    { path: '/progress', name: 'Progress', component: Progress },
    { path: '/archive', name: 'Archive', component: Archive },
    { path: '/lesson/:id', name: 'LessonDetail', component: LessonDetail, props: true },
    { path: '/writing', name: 'WritingCenter', component: WritingCenter },
  ],
})

export default router
