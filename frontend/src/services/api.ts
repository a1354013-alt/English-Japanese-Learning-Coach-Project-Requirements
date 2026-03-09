import axios from 'axios'
import type { Lesson, UserProgress, ReviewAnswer, ReviewResult, GenerateLessonRequest } from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000
})

export const lessonApi = {
  // Generate new lesson
  async generateLesson(request: GenerateLessonRequest) {
    const response = await api.post<{ success: boolean; lesson: Lesson; message: string }>('/generate/lesson', request)
    return response.data
  },

  // Trigger daily generation
  async triggerDailyGeneration() {
    const response = await api.post<{ success: boolean; message: string }>('/generate/trigger')
    return response.data
  },

  // Get today's lesson
  async getTodayLesson(language: 'EN' | 'JP') {
    const response = await api.get<{ success: boolean; lesson: Lesson | null; message?: string }>(`/lessons/today/${language}`)
    return response.data
  },

  // Get lesson by ID
  async getLesson(lessonId: string) {
    const response = await api.get<{ success: boolean; lesson: Lesson }>(`/lessons/${lessonId}`)
    return response.data
  },

  // List lessons with filters
  async listLessons(params: {
    language?: 'EN' | 'JP'
    start_date?: string
    end_date?: string
    level?: string
    topic?: string
    limit?: number
    offset?: number
  }) {
    const response = await api.get<{ success: boolean; count: number; lessons: any[] }>('/lessons', { params })
    return response.data
  }
}

export const progressApi = {
  // Get progress
  async getProgress(userId: string = 'default_user') {
    const response = await api.get<{ success: boolean; progress: UserProgress }>('/progress', {
      params: { user_id: userId }
    })
    return response.data
  },

  // Update progress
  async updateProgress(progress: UserProgress) {
    const response = await api.post<{ success: boolean; message: string }>('/progress', progress)
    return response.data
  }
}

export const reviewApi = {
  // Submit review answers
  async submitReview(answers: ReviewAnswer[], userId: string = 'default_user') {
    const response = await api.post<ReviewResult>('/review', answers, {
      params: { user_id: userId }
    })
    return response.data
  }
}

export const statsApi = {
  // Get statistics
  async getStatistics(userId: string = 'default_user') {
    const response = await api.get<{ success: boolean; stats: any }>('/stats', {
      params: { user_id: userId }
    })
    return response.data
  }
}

export const importApi = {
  // Upload RAG material
  async uploadRagMaterial(language: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<{ success: boolean; message: string }>(`/rag/upload?language=${language}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  // Import Excel vocabulary
  async importExcel(language: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<{ success: boolean; message: string; count: number }>(`/import/excel?language=${language}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }
}

export default api
