import { describe, expect, it } from 'vitest'
import { getTaskStatusLabel } from '@/utils/taskStatusLabel'

describe('task status labels', () => {
  it('maps internal task statuses to user-friendly labels', () => {
    expect(getTaskStatusLabel('success')).toBe('Ready')
    expect(getTaskStatusLabel('fallback_success')).toBe('Ready (Simplified)')
    expect(getTaskStatusLabel('failed')).toBe('Generation failed')
    expect(getTaskStatusLabel('pending')).toBe('Queued')
    expect(getTaskStatusLabel('running')).toBe('Generating')
    expect(getTaskStatusLabel('retried')).toBe('Retry scheduled')
  })
})
