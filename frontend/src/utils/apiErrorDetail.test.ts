import { describe, expect, it } from 'vitest'
import { formatApiErrorDetail } from './apiErrorDetail'

describe('formatApiErrorDetail', () => {
  it('uses structured message/code payloads when detail is absent', () => {
    expect(
      formatApiErrorDetail({
        error: true,
        message: 'Material not found',
        code: 'rag_material_not_found',
      }),
    ).toBe('Material not found')
  })

  it('prefers backend detail over structured fallback message', () => {
    expect(
      formatApiErrorDetail({
        error: true,
        message: 'Upload failed',
        code: 'rag_unavailable',
        detail: 'RAG is disabled by configuration',
      }),
    ).toBe('RAG is disabled by configuration')
  })

  it('returns string detail from FastAPI', () => {
    expect(formatApiErrorDetail({ detail: 'Not found' })).toBe('Not found')
  })

  it('joins validation error array', () => {
    expect(
      formatApiErrorDetail({
        detail: [{ msg: 'field required', type: 'missing' }],
      }),
    ).toContain('field required')
  })

  it('handles null body', () => {
    expect(formatApiErrorDetail(null)).toBe('Request failed')
  })
})
