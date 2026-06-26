import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ChatTutor from '@/views/ChatTutor.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, params?: Record<string, string | number>) => {
      if (!params) return key
      return `${key} ${Object.values(params).join(' ')}`
    },
  }),
}))

vi.mock('@/utils/wsUrl', () => ({
  resolveWebSocketBaseUrl: () => 'ws://localhost:8000',
}))

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1

  onopen: (() => void) | null = null
  onmessage: WebSocket['onmessage'] = null
  onerror: (() => void) | null = null
  onclose: WebSocket['onclose'] = null
  readyState = MockWebSocket.OPEN
  url: string

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send = vi.fn()
  close = vi.fn()
}

describe('ChatTutor.vue', () => {
  const originalWebSocket = globalThis.WebSocket

  beforeEach(() => {
    vi.clearAllMocks()
    MockWebSocket.instances = []
    globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket
  })

  afterEach(() => {
    globalThis.WebSocket = originalWebSocket
  })

  it('keeps error status when websocket close follows an error', async () => {
    const wrapper = mount(ChatTutor)
    const socket = MockWebSocket.instances[0]

    socket.onerror?.()
    await wrapper.vm.$nextTick()
    socket.onclose?.call(
      socket as unknown as WebSocket,
      {
        code: 1006,
      } as CloseEvent,
    )
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('chat.connectionFailed')
    expect(wrapper.find('input').attributes('disabled')).toBe('')
  })

  it('shows disconnected input state after a normal close', async () => {
    const wrapper = mount(ChatTutor)
    const socket = MockWebSocket.instances[0]

    socket.onopen?.()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('input').attributes('disabled')).toBeUndefined()

    socket.onclose?.call(
      socket as unknown as WebSocket,
      {
        code: 1000,
      } as CloseEvent,
    )
    await wrapper.vm.$nextTick()

    expect(wrapper.find('input').attributes('disabled')).toBe('')
  })

  it('reconnects with the updated language prop', async () => {
    const wrapper = mount(ChatTutor, {
      props: { embedded: true, language: 'EN' },
    })

    expect(MockWebSocket.instances[0]?.url).toContain('/ws/chat/EN')
    await wrapper.setProps({ language: 'JP' })
    await wrapper.vm.$nextTick()

    expect(
      MockWebSocket.instances[MockWebSocket.instances.length - 1]?.url,
    ).toContain('/ws/chat/JP')
  })
})
