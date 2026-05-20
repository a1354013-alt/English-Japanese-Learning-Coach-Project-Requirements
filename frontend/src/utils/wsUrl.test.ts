import { describe, expect, it } from 'vitest'
import { resolveWebSocketBaseUrl } from './wsUrl'

describe('resolveWebSocketBaseUrl', () => {
  it('uses an explicit websocket URL when provided', () => {
    expect(
      resolveWebSocketBaseUrl({
        wsBaseUrl: 'ws://api.example.com/',
        location: { protocol: 'https:', host: 'app.example.com' },
      }),
    ).toBe('ws://api.example.com')
  })

  it('derives wss from an absolute api base url', () => {
    expect(
      resolveWebSocketBaseUrl({
        apiBaseUrl: 'https://api.example.com/api',
      }),
    ).toBe('wss://api.example.com')
  })

  it('falls back to the current browser host for relative api paths', () => {
    expect(
      resolveWebSocketBaseUrl({
        apiBaseUrl: '/api',
        location: { protocol: 'https:', host: 'demo.example.com' },
      }),
    ).toBe('wss://demo.example.com')
  })

  it('uses current host when no env override is available', () => {
    expect(
      resolveWebSocketBaseUrl({
        location: { protocol: 'http:', host: '127.0.0.1:5173' },
      }),
    ).toBe('ws://127.0.0.1:5173')
  })
})
