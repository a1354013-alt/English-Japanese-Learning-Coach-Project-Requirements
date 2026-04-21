import { describe, expect, it, vi } from 'vitest'

// Mock axios before importing the module under test (handle hoisting).
const mocks = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  deleteMock: vi.fn(),
  patchMock: vi.fn(),
}))

vi.mock('axios', async () => {
  const actual = await vi.importActual<any>('axios')
  return {
    ...actual,
    default: {
      ...actual.default,
      isAxiosError: () => true,
      create: () => ({
        get: mocks.getMock,
        post: mocks.postMock,
        delete: mocks.deleteMock,
        patch: mocks.patchMock,
        interceptors: { response: { use: vi.fn() } },
      }),
    },
  }
})

import { importApi, reviewApi } from './api'

describe('api client', () => {
  it('calls SRS endpoints with query params', async () => {
    mocks.getMock.mockResolvedValueOnce({ data: { success: true, items: [] } })
    await reviewApi.getDueSrs('EN')
    expect(mocks.getMock).toHaveBeenCalledWith('/srs/due', { params: { language: 'EN' } })

    mocks.postMock.mockResolvedValueOnce({ data: { success: true } })
    await reviewApi.submitSrsReview('hello', 'EN', 5)
    expect(mocks.postMock).toHaveBeenCalledWith('/srs/review', null, { params: { word: 'hello', language: 'EN', quality: 5 } })
  })

  it('calls RAG list/delete endpoints', async () => {
    mocks.getMock.mockResolvedValueOnce({ data: { success: true, items: [] } })
    await importApi.listRagMaterials('JP')
    expect(mocks.getMock).toHaveBeenCalledWith('/rag/materials', { params: { language: 'JP' } })

    mocks.deleteMock.mockResolvedValueOnce({ data: { success: true } })
    await importApi.deleteRagMaterial('doc1')
    expect(mocks.deleteMock).toHaveBeenCalledWith('/rag/materials/doc1')
  })
})
