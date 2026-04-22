import type { GenerationTask } from '@/types'

export const TASK_STATUS_LABELS: Record<GenerationTask['status'], string> = {
  pending: 'Queued',
  running: 'Running',
  success: 'Success',
  fallback_success: 'Success (Fallback)',
  failed: 'Failed',
  retried: 'Retried',
}

export function getTaskStatusLabel(status: GenerationTask['status']): string {
  return TASK_STATUS_LABELS[status] ?? status
}

