import { createRouter, createWebHistory } from 'vue-router'
import LessonDetail from '@/views/LessonDetail.vue'
import Progress from '@/views/Progress.vue'
import TodayLesson from '@/views/TodayLesson.vue'
import Analytics from '@/views/Analytics.vue'
import Vocabulary from '@/views/Vocabulary.vue'
import LearningWorkspace from '@/views/LearningWorkspace.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'TodayLesson', component: TodayLesson },
    { path: '/today', redirect: '/' },
    { path: '/workspace', name: 'LearningWorkspace', component: LearningWorkspace },
    { path: '/progress', name: 'Progress', component: Progress },
    { path: '/archive', name: 'Archive', redirect: { path: '/progress', query: { tab: 'history' } } },
    { path: '/mistakes', name: 'WrongAnswers', redirect: { path: '/progress', query: { tab: 'mistakes' } } },
    { path: '/lesson/:id', name: 'LessonDetail', component: LessonDetail, props: true },
    { path: '/writing', name: 'WritingCenter', redirect: { path: '/workspace', query: { tab: 'writing' } } },
    { path: '/chat', name: 'ChatTutor', redirect: { path: '/workspace', query: { tab: 'chat' } } },
    { path: '/analytics', name: 'Analytics', component: Analytics },
    { path: '/review', name: 'SrsReview', redirect: { path: '/progress', query: { tab: 'review' } } },
    { path: '/materials', name: 'Materials', redirect: { path: '/workspace', query: { tab: 'materials' } } },
    { path: '/vocabulary', name: 'Vocabulary', component: Vocabulary },
  ],
})

export default router
