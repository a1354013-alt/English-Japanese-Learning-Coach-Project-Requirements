import { describe, expect, it } from 'vitest'
import { getTaskStatusLabel } from '@/utils/taskStatusLabel'

describe('task status labels', () => {
  it('maps internal task statuses to user-friendly labels', () => {
    expect(getTaskStatusLabel('success')).toBe('Success')
    expect(getTaskStatusLabel('fallback_success')).toBe('Success (Fallback)')
    expect(getTaskStatusLabel('failed')).toBe('Failed')
    expect(getTaskStatusLabel('pending')).toBe('Queued')
    expect(getTaskStatusLabel('running')).toBe('Running')
    expect(getTaskStatusLabel('retried')).toBe('Retried')
  })
})

