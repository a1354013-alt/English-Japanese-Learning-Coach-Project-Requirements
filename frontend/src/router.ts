import { createRouter, createWebHistory } from 'vue-router'
import Archive from '@/views/Archive.vue'
import LessonDetail from '@/views/LessonDetail.vue'
import Progress from '@/views/Progress.vue'
import TodayLesson from '@/views/TodayLesson.vue'
import WritingCenter from '@/views/WritingCenter.vue'
import WrongAnswers from '@/views/WrongAnswers.vue'
import ChatTutor from '@/views/ChatTutor.vue'
import Analytics from '@/views/Analytics.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'TodayLesson', component: TodayLesson },
    { path: '/progress', name: 'Progress', component: Progress },
    { path: '/archive', name: 'Archive', component: Archive },
    { path: '/mistakes', name: 'WrongAnswers', component: WrongAnswers },
    { path: '/lesson/:id', name: 'LessonDetail', component: LessonDetail, props: true },
    { path: '/writing', name: 'WritingCenter', component: WritingCenter },
    { path: '/chat', name: 'ChatTutor', component: ChatTutor },
    { path: '/analytics', name: 'Analytics', component: Analytics },
  ],
})

export default router
