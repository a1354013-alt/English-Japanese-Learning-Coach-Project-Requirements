import axios from 'axios'
import { formatApiErrorDetail } from '@/utils/apiErrorDetail'
import { showApiError } from '@/services/apiNotifications'
import type {
  GenerateLessonRequest,
  Language,
  Lesson,
  ReviewAnswer,
  ReviewResult,
  StudyPlan,
  UserProgress,
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
  SrsDueResponse,
  ErrorType,
  DemoResetResponse,
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const data = error.response?.data
      const msg = data !== undefined ? formatApiErrorDetail(data) : error.message || 'Network error'
      showApiError(msg)
    } else {
      showApiError('Unexpected error')
    }
    return Promise.reject(error)
  },
)

export const lessonApi = {
  async generateLesson(request: GenerateLessonRequest) {
    const response = await api.post<{ success: boolean; lesson: Lesson }>('/generate/lesson', request)
    return response.data
  },

  async getTodayLesson(language: Language) {
    const response = await api.get<{ success: boolean; lesson: Lesson | null }>(`/lessons/today/${language}`)
    return response.data
  },

  async getLesson(lessonId: string) {
    const response = await api.get<{ success: boolean; lesson: Lesson }>(`/lessons/${lessonId}`)
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
    const response = await api.get<{ success: boolean; count: number; lessons: Array<{ lesson_id: string; language: Language; level: string; topic: string; generated_at: string; key_points: string | string[] }> }>('/lessons', { params })
    return response.data
  },

  async getTasks(limit = 10) {
    const response = await api.get<{ success: boolean; tasks: GenerationTask[] }>('/tasks', { params: { limit } })
    return response.data
  },

  exportPdf(lessonId: string) {
    window.open(`/api/export/pdf/${lessonId}`, '_blank', 'noopener,noreferrer')
  },

  async getTts(text: string, language: Language) {
    const response = await api.post<TtsResponse>('/tts', null, {
      params: { text, language },
    })
    return response.data
  },
}

export const progressApi = {
  async getProgress() {
    const response = await api.get<{ success: boolean; progress: UserProgress }>('/progress')
    return response.data
  },

  async onboard(language: Language, level: string, difficulty: string) {
    const response = await api.post<{ success: boolean }>('/onboard', null, {
      params: { language, level, difficulty },
    })
    return response.data
  },
}

export const reviewApi = {
  async submitReview(answers: ReviewAnswer[], errorType?: ErrorType) {
    const params: Record<string, string> = {}
    if (errorType) params.error_type = errorType
    const response = await api.post<ReviewResult>('/review', answers, Object.keys(params).length ? { params } : undefined)
    return response.data
  },

  async getDueSrs(language?: Language) {
    const response = await api.get<SrsDueResponse>('/srs/due', { params: { language } })
    return response.data
  },

  async submitSrsReview(word: string, language: Language, quality: number) {
    const response = await api.post<{ success: boolean }>('/srs/review', null, {
      params: { word, language, quality },
    })
    return response.data
  },
}

export const importApi = {
  async uploadRagMaterial(language: Language, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<{ success: boolean }>('/rag/upload', formData, {
      params: { language },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  async importExcel(language: Language, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<{ success: boolean; count: number }>('/import/excel', formData, {
      params: { language },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  async listRagMaterials(language?: Language) {
    const response = await api.get<RagMaterialsResponse>('/rag/materials', { params: { language } })
    return response.data
  },

  async deleteRagMaterial(docId: string) {
    const response = await api.delete<{ success: boolean }>(`/rag/materials/${docId}`)
    return response.data
  },

  async listImportedVocabulary(params: { language?: Language; q?: string; limit?: number; offset?: number } = {}) {
    const response = await api.get<ImportedVocabularyListResponse>('/imported-vocabulary', { params })
    return response.data
  },

  async deleteImportedVocabulary(itemId: number) {
    const response = await api.delete<{ success: boolean }>(`/imported-vocabulary/${itemId}`)
    return response.data
  },
}

export const aiTutorApi = {
  async analyzeWriting(submission: WritingSubmission) {
    const response = await api.post<{ success: boolean; analysis: WritingAnalysis }>('/writing/analyze', submission)
    return response.data
  },

  async generateStudyPlan(targetGoal: string, language: Language) {
    const response = await api.post<{ success: boolean; plan: StudyPlan }>('/study-plan/generate', null, {
      params: { target_goal: targetGoal, language },
    })
    return response.data
  },
}

export const wrongAnswerApi = {
  async listWrongAnswers(params: { status?: WrongAnswerStatus; limit?: number; offset?: number } = {}) {
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
    const response = await api.post<WrongAnswerItemResponse>('/wrong-answers', payload)
    return response.data
  },

  async updateStatus(id: number, status: WrongAnswerStatus) {
    const response = await api.patch<WrongAnswerItemResponse>(`/wrong-answers/${id}`, { status })
    return response.data
  },

  async deleteWrongAnswer(id: number) {
    const response = await api.delete<{ success: boolean }>(`/wrong-answers/${id}`)
    return response.data
  },

  async retry(id: number, userAnswer: string) {
    const response = await api.post<WrongAnswerRetryResponse>(`/wrong-answers/${id}/retry`, { user_answer: userAnswer })
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
