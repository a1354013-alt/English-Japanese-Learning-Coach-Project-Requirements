interface LocationLike {
  protocol: string
  host: string
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

function toWsOrigin(value: string): string {
  return value.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:')
}

function isAbsoluteUrl(value: string): boolean {
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(value)
}

export function resolveWebSocketBaseUrl(options: {
  wsBaseUrl?: string | null
  apiBaseUrl?: string | null
  location?: LocationLike
}): string {
  const explicitWsBaseUrl = options.wsBaseUrl?.trim()
  if (explicitWsBaseUrl) {
    if (isAbsoluteUrl(explicitWsBaseUrl)) {
      return trimTrailingSlash(toWsOrigin(explicitWsBaseUrl))
    }
    if (options.location) {
      const protocol = options.location.protocol === 'https:' ? 'wss:' : 'ws:'
      return trimTrailingSlash(
        `${protocol}//${options.location.host}${explicitWsBaseUrl}`,
      )
    }
    return trimTrailingSlash(explicitWsBaseUrl)
  }

  const apiBaseUrl = options.apiBaseUrl?.trim()
  if (apiBaseUrl && isAbsoluteUrl(apiBaseUrl)) {
    const normalizedApiUrl = new URL(apiBaseUrl)
    return trimTrailingSlash(
      `${normalizedApiUrl.protocol === 'https:' ? 'wss:' : 'ws:'}//${normalizedApiUrl.host}`,
    )
  }

  if (options.location) {
    return trimTrailingSlash(
      `${options.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${options.location.host}`,
    )
  }

  return ''
}
