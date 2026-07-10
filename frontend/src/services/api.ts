import axios from 'axios'
import i18n from '@/i18n'
import { formatApiErrorDetail } from '@/utils/apiErrorDetail'
import { showApiError } from '@/services/apiNotifications'
import type {
  GenerateLessonRequest,
  OnboardRequest,
  Language,
  Lesson,
  ReviewAnswer,
  ReviewResult,
  StudyPlan,
  ProgressResponse,
  WritingAnalysis,
  WritingSubmission,
  GenerationTask,
  WrongAnswerItemResponse,
  WrongAnswerListResponse,
  WrongAnswerRetryResponse,
  WrongAnswerStatus,
  StreakResponse,
  AnalyticsResponse,
  RagMaterialsResponse,
  ImportedVocabularyListResponse,
  TtsResponse,
  TtsRequest,
  SrsDueResponse,
  SrsReviewRequest,
  StudyPlanGenerateRequest,
  ErrorType,
  DemoResetResponse,
  FeynmanFeedbackResponse,
  LearningItemDueResponse,
  LearningItemReviewResult,
  LearningItemType,
  LearningItemWeakResponse,
  LessonListItem,
  DiagnosticQuestion,
  LearningPlan,
  MicroLesson,
  MicroLessonAnswerResponse,
  MicroLessonTodayResponse,
  DailyStudyMissionResponse,
} from '@/types'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').trim()

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 120000,
})

function getFriendlyApiMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return i18n.global.t('errors.unableToLoadData')
  }

  const data = error.response?.data
  const detail =
    data !== undefined
      ? formatApiErrorDetail(data)
      : error.message || 'Network error'
  const normalized = detail.toLowerCase()

  if (
    !error.response ||
    normalized.includes('network error') ||
    normalized.includes('failed to fetch')
  ) {
    return i18n.global.t('errors.serverNotResponding')
  }

  if (
    error.response.status >= 500 ||
    normalized.includes('internal server error') ||
    normalized.includes('request failed with status code 500')
  ) {
    return i18n.global.t('errors.unableToLoadData')
  }

  return detail
}

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    showApiError(getFriendlyApiMessage(error))
    return Promise.reject(error)
  },
)

export const lessonApi = {
  async generateLesson(request: GenerateLessonRequest) {
    const response = await api.post<{ success: boolean; lesson: Lesson }>(
      '/generate/lesson',
      request,
    )
    return response.data
  },

  async getTodayLesson(language: Language) {
    const response = await api.get<{ success: boolean; lesson: Lesson | null }>(
      `/lessons/today/${language}`,
    )
    return response.data
  },

  async getLesson(lessonId: string) {
    const response = await api.get<{ success: boolean; lesson: Lesson }>(
      `/lessons/${lessonId}`,
    )
    return response.data
  },

  async submitFeynmanFeedback(
    lessonId: string,
    payload: {
      explanation: string
      language: Language
      lesson_snapshot?: Lesson
    },
  ) {
    const response = await api.post<FeynmanFeedbackResponse>(
      `/lessons/${encodeURIComponent(lessonId)}/feynman-feedback`,
      payload,
    )
    return response.data
  },

  async listLessons(params: {
    language?: Language
    start_date?: string
    end_date?: string
    level?: string
    topic?: string
    limit?: number
    offset?: number
  }) {
    const response = await api.get<{
      success: boolean
      count: number
      lessons: LessonListItem[]
    }>('/lessons', { params })
    return response.data
  },

  async getTasks(limit = 10) {
    const response = await api.get<{
      success: boolean
      tasks: GenerationTask[]
    }>('/tasks', { params: { limit } })
    return response.data
  },

  async exportPdf(lessonId: string) {
    const response = await api.get<Blob>(
      `/export/pdf/${encodeURIComponent(lessonId)}`,
      {
        responseType: 'blob',
      },
    )

    const responseContentType = response.headers['content-type']
    const contentType =
      typeof responseContentType === 'string'
        ? responseContentType
        : 'application/pdf'
    const blob = new Blob([response.data], { type: contentType })
    const url = window.URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = `lesson_${lessonId}.pdf`
    document.body.appendChild(link)
    link.click()
    link.remove()

    window.setTimeout(() => window.URL.revokeObjectURL(url), 30_000)
  },

  async getTts(text: string, language: Language) {
    const payload: TtsRequest = { text, language }
    const response = await api.post<TtsResponse>('/tts', payload)
    return response.data
  },
}

export const progressApi = {
  async getProgress() {
    const response = await api.get<ProgressResponse>('/progress')
    return response.data
  },

  async onboard(
    language: Language,
    level: OnboardRequest['level'],
    difficulty: OnboardRequest['difficulty'],
  ) {
    const payload: OnboardRequest = { language, level, difficulty }
    const response = await api.post<{ success: boolean }>('/onboard', payload)
    return response.data
  },
}

export const diagnosticApi = {
  async getQuestions() {
    const response = await api.get<{
      success: boolean
      questions: DiagnosticQuestion[]
    }>('/diagnostic/questions')
    return response.data
  },

  async submit(
    answers: Array<{
      question_id: string
      answer: string
    }>,
  ) {
    const response = await api.post<{
      success: boolean
      learning_plan: LearningPlan
    }>('/diagnostic/submit', { answers })
    return response.data
  },
}

export const microLessonApi = {
  async getToday() {
    const response = await api.get<MicroLessonTodayResponse>(
      '/micro-lessons/today',
    )
    return response.data
  },

  async generate() {
    const response = await api.post<{ success: boolean; lesson: MicroLesson }>(
      '/micro-lessons/generate',
    )
    return response.data
  },

  async answer(lessonId: string, answer: string) {
    const response = await api.post<MicroLessonAnswerResponse>(
      `/micro-lessons/${encodeURIComponent(lessonId)}/answer`,
      { answer },
    )
    return response.data
  },
}

export const studyApi = {
  async getTodayMission() {
    const response = await api.get<DailyStudyMissionResponse>('/study/today')
    return response.data
  },
}

export const reviewApi = {
  async submitReview(answers: ReviewAnswer[], errorType?: ErrorType) {
    const params: Record<string, string> = {}
    if (errorType) params.error_type = errorType
    const response = await api.post<ReviewResult>(
      '/review',
      answers,
      Object.keys(params).length ? { params } : undefined,
    )
    return response.data
  },

  async getDueSrs(language?: Language) {
    const response = await api.get<SrsDueResponse>('/srs/due', {
      params: { language },
    })
    return response.data
  },

  async submitSrsReview(word: string, language: Language, quality: number) {
    const payload: SrsReviewRequest = { word, language, quality }
    const response = await api.post<{ success: boolean }>(
      '/srs/review',
      payload,
    )
    return response.data
  },

  async getDueLearningItems(
    params: {
      language?: Language
      item_type?: LearningItemType
    } = {},
  ) {
    const response = await api.get<LearningItemDueResponse>('/srs/items/due', {
      params,
    })
    return response.data
  },

  async submitLearningItemReview(payload: {
    item_id: string
    rating: number
    correct: boolean
    response_time_ms?: number
    source?: 'lesson_review' | 'srs_review' | 'feynman_feedback' | 'manual'
  }) {
    const response = await api.post<LearningItemReviewResult>(
      '/srs/items/review',
      payload,
    )
    return response.data
  },

  async getWeakLearningItems(language?: Language) {
    const response = await api.get<LearningItemWeakResponse>(
      '/srs/items/weak',
      {
        params: { language },
      },
    )
    return response.data
  },
}

export const importApi = {
  async uploadRagMaterial(language: Language, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<{ success: boolean; doc_id: string }>(
      '/rag/upload',
      formData,
      {
        params: { language },
        headers: { 'Content-Type': 'multipart/form-data' },
      },
    )
    return response.data
  },

  async importExcel(language: Language, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<{ success: boolean; count: number }>(
      '/import/excel',
      formData,
      {
        params: { language },
        headers: { 'Content-Type': 'multipart/form-data' },
      },
    )
    return response.data
  },

  async listRagMaterials(language?: Language) {
    const response = await api.get<RagMaterialsResponse>('/rag/materials', {
      params: { language },
    })
    return response.data
  },

  async deleteRagMaterial(docId: string) {
    const response = await api.delete<{ success: boolean }>(
      `/rag/materials/${docId}`,
    )
    return response.data
  },

  async listImportedVocabulary(
    params: {
      language?: Language
      q?: string
      limit?: number
      offset?: number
    } = {},
  ) {
    const response = await api.get<ImportedVocabularyListResponse>(
      '/imported-vocabulary',
      { params },
    )
    return response.data
  },

  async deleteImportedVocabulary(itemId: number) {
    const response = await api.delete<{ success: boolean }>(
      `/imported-vocabulary/${itemId}`,
    )
    return response.data
  },
}

export const aiTutorApi = {
  async analyzeWriting(submission: WritingSubmission) {
    const response = await api.post<{
      success: boolean
      analysis: WritingAnalysis
    }>('/writing/analyze', submission)
    return response.data
  },

  async generateStudyPlan(targetGoal: string, language: Language) {
    const payload: StudyPlanGenerateRequest = {
      target_goal: targetGoal,
      language,
    }
    const response = await api.post<{ success: boolean; plan: StudyPlan }>(
      '/study-plan/generate',
      payload,
    )
    return response.data
  },
}

export const wrongAnswerApi = {
  async listWrongAnswers(
    params: {
      status?: WrongAnswerStatus
      limit?: number
      offset?: number
    } = {},
  ) {
    const response = await api.get<WrongAnswerListResponse>('/wrong-answers', {
      params: {
        status: params.status,
        limit: params.limit,
        offset: params.offset,
      },
    })
    return response.data
  },

  async addWrongAnswer(payload: {
    language: Language
    question_type: string
    question: string
    user_answer: string
    correct_answer: string
    source_lesson_id?: string | null
  }) {
    const response = await api.post<WrongAnswerItemResponse>(
      '/wrong-answers',
      payload,
    )
    return response.data
  },

  async updateStatus(id: number, status: WrongAnswerStatus) {
    const response = await api.patch<WrongAnswerItemResponse>(
      `/wrong-answers/${id}`,
      { status },
    )
    return response.data
  },

  async deleteWrongAnswer(id: number) {
    const response = await api.delete<{ success: boolean }>(
      `/wrong-answers/${id}`,
    )
    return response.data
  },

  async retry(id: number, userAnswer: string) {
    const response = await api.post<WrongAnswerRetryResponse>(
      `/wrong-answers/${id}/retry`,
      { user_answer: userAnswer },
    )
    return response.data
  },
}

export const streakApi = {
  async getStreak() {
    const response = await api.get<StreakResponse>('/streak')
    return response.data
  },
}

export const analyticsApi = {
  async getAnalytics() {
    const response = await api.get<AnalyticsResponse>('/analytics')
    return response.data
  },
}

export const systemApi = {
  async resetDemo() {
    const response = await api.post<DemoResetResponse>('/demo/reset')
    return response.data
  },
}

export default api
