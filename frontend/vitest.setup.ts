import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, vi } from 'vitest'
import { resetFeedbackState } from '@/services/appFeedback'

enableAutoUnmount(afterEach)

afterEach(() => {
  resetFeedbackState()
  vi.clearAllMocks()
  vi.restoreAllMocks()
  vi.useRealTimers()
  document.body.innerHTML = ''
})
