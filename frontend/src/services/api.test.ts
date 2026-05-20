import { describe, expect, it, vi } from 'vitest'

// Mock axios before importing the module under test (handle hoisting).
const mocks = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  deleteMock: vi.fn(),
  patchMock: vi.fn(),
  createMock: vi.fn(),
}))

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  mocks.createMock.mockImplementation(() => ({
    get: mocks.getMock,
    post: mocks.postMock,
    delete: mocks.deleteMock,
    patch: mocks.patchMock,
    interceptors: { response: { use: vi.fn() } },
  }))
  return {
    ...actual,
    default: {
      ...actual.default,
      isAxiosError: () => true,
      create: mocks.createMock,
    },
  }
})

import { aiTutorApi, importApi, lessonApi, progressApi, reviewApi } from './api'
import type { ReviewAnswer } from '@/types'

describe('api client', () => {
  it('defaults the API base URL to the Vite proxy path', () => {
    expect(mocks.createMock).toHaveBeenCalledWith(
      expect.objectContaining({
        baseURL: '/api',
      }),
    )
  })

  it('calls SRS endpoints with typed body payloads', async () => {
    mocks.getMock.mockResolvedValueOnce({ data: { success: true, items: [] } })
    await reviewApi.getDueSrs('EN')
    expect(mocks.getMock).toHaveBeenCalledWith('/srs/due', {
      params: { language: 'EN' },
    })

    mocks.postMock.mockResolvedValueOnce({ data: { success: true } })
    await reviewApi.submitSrsReview('hello', 'EN', 5)
    expect(mocks.postMock).toHaveBeenCalledWith('/srs/review', {
      word: 'hello',
      language: 'EN',
      quality: 5,
    })
  })

  it('posts onboarding, study plan, and tts requests as JSON bodies', async () => {
    mocks.postMock.mockResolvedValueOnce({ data: { success: true } })
    await progressApi.onboard('EN', 'A1', 'normal')
    expect(mocks.postMock).toHaveBeenCalledWith('/onboard', {
      language: 'EN',
      level: 'A1',
      difficulty: 'normal',
    })

    mocks.postMock.mockResolvedValueOnce({ data: { success: true, plan: {} } })
    await aiTutorApi.generateStudyPlan('TOEIC 800', 'EN')
    expect(mocks.postMock).toHaveBeenCalledWith('/study-plan/generate', {
      target_goal: 'TOEIC 800',
      language: 'EN',
    })

    mocks.postMock.mockResolvedValueOnce({ data: { success: true } })
    await lessonApi.getTts('Hello world', 'EN')
    expect(mocks.postMock).toHaveBeenCalledWith('/tts', {
      text: 'Hello world',
      language: 'EN',
    })
  })

  it('calls RAG list/delete endpoints', async () => {
    mocks.getMock.mockResolvedValueOnce({ data: { success: true, items: [] } })
    await importApi.listRagMaterials('JP')
    expect(mocks.getMock).toHaveBeenCalledWith('/rag/materials', {
      params: { language: 'JP' },
    })

    mocks.deleteMock.mockResolvedValueOnce({ data: { success: true } })
    await importApi.deleteRagMaterial('doc1')
    expect(mocks.deleteMock).toHaveBeenCalledWith('/rag/materials/doc1')
  })

  it('does not send demo user_id query params from the frontend client', async () => {
    const answers: ReviewAnswer[] = [
      {
        lesson_id: 'l1',
        exercise_type: 'grammar',
        question_index: 0,
        user_answer: 'A',
        correct_answer: 'A',
      },
    ]

    mocks.postMock.mockResolvedValueOnce({ data: { success: true } })
    await reviewApi.submitReview(answers)
    expect(mocks.postMock).toHaveBeenCalledWith('/review', answers, undefined)
  })
})
