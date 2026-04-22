import type { GenerationTask } from '@/types'

export const TASK_STATUS_LABELS: Record<GenerationTask['status'], string> = {
  pending: 'Queued',
  running: 'Generating',
  success: 'Ready',
  fallback_success: 'Ready (Simplified)',
  failed: 'Generation failed',
  retried: 'Retry scheduled',
}

export function getTaskStatusLabel(status: GenerationTask['status']): string {
  return TASK_STATUS_LABELS[status] ?? status
}
