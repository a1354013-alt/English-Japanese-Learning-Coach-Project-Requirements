import { ref } from 'vue'

export const apiErrorMessage = ref<string | null>(null)

export function showApiError(message: string): void {
  apiErrorMessage.value = message
}

export function clearApiError(): void {
  apiErrorMessage.value = null
}
