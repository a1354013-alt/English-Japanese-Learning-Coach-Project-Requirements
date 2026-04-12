/** Normalize FastAPI / Axios error payloads for user-visible messages. */
export function formatApiErrorDetail(data: unknown): string {
  if (data == null || typeof data !== 'object') {
    return 'Request failed'
  }
  const d = data as Record<string, unknown>
  const det = d.detail
  if (typeof det === 'string') {
    return det
  }
  if (Array.isArray(det)) {
    return det
      .map((item) => {
        if (item != null && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg: unknown }).msg)
        }
        return JSON.stringify(item)
      })
      .join('; ')
  }
  if (d.message != null) {
    return String(d.message)
  }
  return 'Request failed'
}
