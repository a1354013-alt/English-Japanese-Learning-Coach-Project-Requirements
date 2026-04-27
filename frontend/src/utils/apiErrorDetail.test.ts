import { describe, expect, it } from 'vitest'
import { formatApiErrorDetail } from './apiErrorDetail'

describe('formatApiErrorDetail', () => {
  it('prefers structured message/code payloads', () => {
    expect(formatApiErrorDetail({ error: true, message: 'Material not found', code: 'rag_material_not_found' })).toBe(
      'Material not found',
    )
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
