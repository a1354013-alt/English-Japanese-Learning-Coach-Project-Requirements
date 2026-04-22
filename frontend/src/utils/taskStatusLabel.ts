import type { GenerationTask } from '@/types'

export const TASK_STATUS_LABELS: Record<GenerationTask['status'], string> = {
  pending: 'Queued',
  running: 'In progress',
  success: 'Completed',
  fallback_success: 'Completed (basic lesson)',
  failed: 'Failed',
  retried: 'Retried',
}

export function getTaskStatusLabel(status: GenerationTask['status']): string {
  return TASK_STATUS_LABELS[status] ?? status
}
