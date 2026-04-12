import { describe, expect, it } from 'vitest'
import { formatApiErrorDetail } from './apiErrorDetail'

describe('formatApiErrorDetail', () => {
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
