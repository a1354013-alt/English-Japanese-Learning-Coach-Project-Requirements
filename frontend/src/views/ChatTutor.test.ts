import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ChatTutor from '@/views/ChatTutor.vue'

const chatApiMocks = vi.hoisted(() => ({
  listScenarios: vi.fn(),
  listConversations: vi.fn(),
  createConversation: vi.fn(),
  readMessagesPage: vi.fn(),
  renameConversation: vi.fn(),
  deleteConversation: vi.fn(),
}))

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('@/utils/wsUrl', () => ({
  resolveWebSocketBaseUrl: () => 'ws://localhost:8000',
}))

vi.mock('@/services/api', () => ({
  chatApi: chatApiMocks,
}))

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1

  onopen: (() => void) | null = null
  // eslint-disable-next-line no-unused-vars
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  readyState = MockWebSocket.OPEN
  url: string
  send = vi.fn()
  close = vi.fn(() => {
    this.onclose?.()
  })

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent)
  }
}

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

const scenarios = [
  {
    scenario_id: 'daily_conversation',
    language: 'EN',
    label: 'Daily Conversation',
  },
  { scenario_id: 'travel', language: 'EN', label: 'Travel' },
]

const jpScenarios = [
  {
    scenario_id: 'daily_conversation',
    language: 'JP',
    label: 'Daily Conversation',
  },
  { scenario_id: 'travel', language: 'JP', label: 'Travel' },
]

describe('ChatTutor.vue', () => {
  const originalWebSocket = globalThis.WebSocket
  const originalPrompt = window.prompt
  const originalConfirm = window.confirm

  beforeEach(() => {
    vi.clearAllMocks()
    MockWebSocket.instances = []
    globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket
    window.localStorage.clear()
    window.prompt = vi.fn(() => 'Renamed chat')
    window.confirm = vi.fn(() => true)

    chatApiMocks.listScenarios.mockImplementation(
      async (language: 'EN' | 'JP') => ({
        success: true,
        scenarios: language === 'EN' ? scenarios : jpScenarios,
      }),
    )
    chatApiMocks.listConversations.mockImplementation(
      async (language: 'EN' | 'JP') => ({
        success: true,
        count: language === 'EN' ? 1 : 1,
        conversations:
          language === 'EN'
            ? [
                {
                  conversation_id: 'conv-en',
                  language: 'EN',
                  scenario_id: 'travel',
                  title: 'English Travel',
                  lesson_id: null,
                  summary: null,
                  summary_through_sequence: 0,
                  summary_updated_at: null,
                  created_at: '2026-07-21T10:00:00Z',
                  updated_at: '2026-07-21T10:00:00Z',
                  last_message_at: '2026-07-21T10:00:00Z',
                },
              ]
            : [
                {
                  conversation_id: 'conv-jp',
                  language: 'JP',
                  scenario_id: 'daily_conversation',
                  title: 'Japanese Daily',
                  lesson_id: null,
                  summary: null,
                  summary_through_sequence: 0,
                  summary_updated_at: null,
                  created_at: '2026-07-21T11:00:00Z',
                  updated_at: '2026-07-21T11:00:00Z',
                  last_message_at: '2026-07-21T11:00:00Z',
                },
              ],
      }),
    )
    chatApiMocks.readMessagesPage.mockImplementation(
      async (conversationId: string) => ({
        success: true,
        messages:
          conversationId === 'conv-en'
            ? [
                {
                  message_id: 'm1',
                  conversation_id: 'conv-en',
                  role: 'user',
                  content: 'Hello',
                  sequence_number: 1,
                  metadata: { client_message_id: 'seed-1' },
                  created_at: '2026-07-21T10:01:00Z',
                },
              ]
            : [],
        limit: 50,
        has_more: false,
        next_before_sequence: null,
        next_after_sequence: null,
      }),
    )
    chatApiMocks.createConversation.mockResolvedValue({
      success: true,
      conversation: {
        conversation_id: 'conv-new',
        language: 'EN',
        scenario_id: 'travel',
        title: 'Travel',
        lesson_id: null,
        summary: null,
        summary_through_sequence: 0,
        summary_updated_at: null,
        created_at: '2026-07-21T12:00:00Z',
        updated_at: '2026-07-21T12:00:00Z',
        last_message_at: null,
      },
    })
    chatApiMocks.renameConversation.mockResolvedValue({
      success: true,
      conversation: {
        conversation_id: 'conv-en',
        language: 'EN',
        scenario_id: 'travel',
        title: 'Renamed chat',
        lesson_id: null,
        summary: null,
        summary_through_sequence: 0,
        summary_updated_at: null,
        created_at: '2026-07-21T10:00:00Z',
        updated_at: '2026-07-21T10:05:00Z',
        last_message_at: '2026-07-21T10:00:00Z',
      },
    })
    chatApiMocks.deleteConversation.mockResolvedValue({
      success: true,
      message: 'Conversation deleted',
      conversation_id: 'conv-en',
    })
  })

  afterEach(() => {
    globalThis.WebSocket = originalWebSocket
    window.prompt = originalPrompt
    window.confirm = originalConfirm
  })

  it('loads conversations and restores the selected conversation history', async () => {
    window.localStorage.setItem('chat.selectedConversationId.EN', 'conv-en')

    const wrapper = mount(ChatTutor)
    await flushPromises()
    await flushPromises()

    expect(chatApiMocks.listConversations).toHaveBeenCalledWith('EN')
    expect(chatApiMocks.readMessagesPage).toHaveBeenCalledWith('conv-en', {
      limit: 50,
    })
    expect(wrapper.text()).toContain('English Travel')
    expect(wrapper.text()).toContain('Hello')
    expect(MockWebSocket.instances[0]?.url).toContain('conversation_id=conv-en')
  })

  it('creates a conversation and selects it', async () => {
    const wrapper = mount(ChatTutor)
    await flushPromises()
    await flushPromises()

    await wrapper.get('[data-testid="chat-scenario-select"]').setValue('travel')
    await wrapper.get('[data-testid="chat-new-conversation"]').trigger('click')
    await flushPromises()

    expect(chatApiMocks.createConversation).toHaveBeenCalledWith({
      language: 'EN',
      scenario_id: 'travel',
      title: 'Travel',
    })
    expect(wrapper.text()).toContain('Travel')
  })

  it('isolates EN and JP conversation state', async () => {
    const wrapper = mount(ChatTutor, {
      props: { embedded: true, language: 'EN' },
    })
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('English Travel')
    await wrapper.setProps({ language: 'JP' })
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Japanese Daily')
    expect(wrapper.text()).not.toContain('English Travel')
  })

  it('reconciles optimistic messages with canonical persisted messages', async () => {
    const wrapper = mount(ChatTutor)
    await flushPromises()
    await flushPromises()

    const socket = MockWebSocket.instances[0]
    socket.onopen?.()
    await wrapper.vm.$nextTick()
    await wrapper.get('[data-testid="chat-input"]').setValue('How are you?')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('How are you?')

    const rawSend = socket.send.mock.calls[0][0] as string
    const parsedSend = JSON.parse(rawSend)

    socket.emit({
      type: 'chat.user.persisted',
      client_message_id: parsedSend.client_message_id,
      message: {
        message_id: 'm-user',
        conversation_id: 'conv-en',
        role: 'user',
        content: 'How are you?',
        sequence_number: 2,
        metadata: { client_message_id: parsedSend.client_message_id },
        created_at: '2026-07-21T10:02:00Z',
      },
    })
    socket.emit({
      type: 'chat.assistant.persisted',
      client_message_id: parsedSend.client_message_id,
      message: {
        message_id: 'm-assistant',
        conversation_id: 'conv-en',
        role: 'assistant',
        content: 'I am doing well. How about you?',
        sequence_number: 3,
        metadata: { client_message_id: parsedSend.client_message_id },
        created_at: '2026-07-21T10:02:10Z',
      },
    })
    await flushPromises()

    expect(wrapper.findAll('[data-testid^="chat-message-"]').length).toBe(3)
    expect(wrapper.text()).toContain('I am doing well. How about you?')
  })

  it('marks failed messages and retries using the same client message id', async () => {
    const wrapper = mount(ChatTutor)
    await flushPromises()
    await flushPromises()

    const socket = MockWebSocket.instances[0]
    socket.onopen?.()
    await wrapper.vm.$nextTick()
    await wrapper.get('[data-testid="chat-input"]').setValue('Retry me')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const firstPayload = JSON.parse(socket.send.mock.calls[0][0] as string)
    socket.emit({
      type: 'chat.error',
      client_message_id: firstPayload.client_message_id,
      message: 'Provider failed',
    })
    await flushPromises()

    await wrapper
      .get(`[data-testid="retry-message-${firstPayload.client_message_id}"]`)
      .trigger('click')
    const secondPayload = JSON.parse(socket.send.mock.calls[1][0] as string)

    expect(secondPayload.client_message_id).toBe(firstPayload.client_message_id)
  })

  it('renames and deletes conversations', async () => {
    const wrapper = mount(ChatTutor)
    await flushPromises()
    await flushPromises()

    await wrapper
      .get('[data-testid="rename-conversation-conv-en"]')
      .trigger('click')
    await flushPromises()
    expect(chatApiMocks.renameConversation).toHaveBeenCalledWith(
      'conv-en',
      'Renamed chat',
    )

    await wrapper
      .get('[data-testid="delete-conversation-conv-en"]')
      .trigger('click')
    await flushPromises()
    expect(chatApiMocks.deleteConversation).toHaveBeenCalledWith('conv-en')
  })
})
