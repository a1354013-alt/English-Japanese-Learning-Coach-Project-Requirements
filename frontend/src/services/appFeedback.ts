import { ref } from 'vue'

export type NoticeTone = 'info' | 'success' | 'warning' | 'error'

export interface AppNotice {
  id: number
  message: string
  tone: NoticeTone
}

interface ConfirmState {
  open: boolean
  title: string
  message: string
  confirmLabel: string
  cancelLabel: string
}

const AUTO_DISMISS_MS = 4000

export const notices = ref<AppNotice[]>([])
export const confirmState = ref<ConfirmState>({
  open: false,
  title: '',
  message: '',
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
})

let nextNoticeId = 1
// eslint-disable-next-line no-unused-vars
let pendingResolver: ((confirmed: boolean) => void) | null = null

export function showNotice(
  message: string,
  tone: NoticeTone = 'info',
  durationMs = AUTO_DISMISS_MS,
): number {
  const id = nextNoticeId++
  notices.value = [...notices.value, { id, message, tone }]
  if (durationMs > 0) {
    window.setTimeout(() => dismissNotice(id), durationMs)
  }
  return id
}

export function dismissNotice(id: number): void {
  notices.value = notices.value.filter((notice) => notice.id !== id)
}

export function clearNotices(): void {
  notices.value = []
}

export function resetFeedbackState(): void {
  clearNotices()
  if (pendingResolver) {
    pendingResolver(false)
    pendingResolver = null
  }
  confirmState.value = {
    open: false,
    title: '',
    message: '',
    confirmLabel: 'Confirm',
    cancelLabel: 'Cancel',
  }
}

export function requestConfirmation(options: {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
}): Promise<boolean> {
  if (pendingResolver) {
    pendingResolver(false)
    pendingResolver = null
  }

  confirmState.value = {
    open: true,
    title: options.title,
    message: options.message,
    confirmLabel: options.confirmLabel || 'Confirm',
    cancelLabel: options.cancelLabel || 'Cancel',
  }

  return new Promise<boolean>((resolve) => {
    pendingResolver = resolve
  })
}

export function resolveConfirmation(confirmed: boolean): void {
  if (pendingResolver) {
    pendingResolver(confirmed)
    pendingResolver = null
  }
  confirmState.value = {
    open: false,
    title: '',
    message: '',
    confirmLabel: 'Confirm',
    cancelLabel: 'Cancel',
  }
}
