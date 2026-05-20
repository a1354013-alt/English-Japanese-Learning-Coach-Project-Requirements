import { describe, expect, it } from 'vitest'
import {
  clearNotices,
  confirmState,
  notices,
  requestConfirmation,
  resetFeedbackState,
  resolveConfirmation,
  showNotice,
} from './appFeedback'

describe('appFeedback service', () => {
  it('stores dismissible notices', () => {
    resetFeedbackState()
    showNotice('Saved', 'success', 0)

    expect(notices.value).toHaveLength(1)
    expect(notices.value[0]).toMatchObject({
      message: 'Saved',
      tone: 'success',
    })

    clearNotices()
    expect(notices.value).toHaveLength(0)
  })

  it('resolves confirmation promises through shared state', async () => {
    resetFeedbackState()
    const promise = requestConfirmation({
      title: 'Delete item',
      message: 'This cannot be undone.',
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    })

    expect(confirmState.value.open).toBe(true)
    expect(confirmState.value.title).toBe('Delete item')

    resolveConfirmation(true)

    await expect(promise).resolves.toBe(true)
    expect(confirmState.value.open).toBe(false)
  })
})
