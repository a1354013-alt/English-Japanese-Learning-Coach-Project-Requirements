import { expect, test, type Page, type Route } from '@playwright/test'

type Language = 'EN' | 'JP'

interface MockConversation {
  conversation_id: string
  language: Language
  scenario_id: 'daily-conversation' | 'travel' | 'restaurant' | 'workplace'
  title: string
  lesson_id: null
  summary: null
  summary_through_sequence: number
  summary_updated_at: null
  created_at: string
  updated_at: string
  last_message_at: string | null
}

interface MockMessage {
  message_id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  sequence_number: number
  metadata: Record<string, unknown> | null
  created_at: string
}

const scenarioCatalog = {
  EN: [
    { scenario_id: 'daily-conversation', language: 'EN', label: 'Daily Conversation' },
    { scenario_id: 'travel', language: 'EN', label: 'Travel' },
    { scenario_id: 'restaurant', language: 'EN', label: 'Restaurant' },
    { scenario_id: 'workplace', language: 'EN', label: 'Workplace' },
  ],
  JP: [
    { scenario_id: 'daily-conversation', language: 'JP', label: 'Daily Conversation' },
    { scenario_id: 'travel', language: 'JP', label: 'Travel' },
    { scenario_id: 'restaurant', language: 'JP', label: 'Restaurant' },
    { scenario_id: 'workplace', language: 'JP', label: 'Workplace' },
  ],
} as const

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function installPersistedChatMocks(page: Page) {
  const conversations = new Map<string, MockConversation>()
  const messages = new Map<string, MockMessage[]>()
  let conversationCounter = 0
  let messageCounter = 0

  const nowIso = () => new Date('2026-07-21T12:00:00.000Z').toISOString()

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()

    if (!path.startsWith('/api/chat/')) {
      if (path === '/api/progress') {
        await fulfillJson(route, {
          success: true,
          progress: {
            user_id: 'default_user',
            english_progress: {
              language: 'EN',
              current_level: 'A1',
              target_level: 'A2',
              completed_lessons: 0,
              total_exercises: 0,
              correct_exercises: 0,
              accuracy_rate: 0,
              last_study_date: null,
            },
            japanese_progress: {
              language: 'JP',
              current_level: 'N5',
              target_level: 'N4',
              completed_lessons: 0,
              total_exercises: 0,
              correct_exercises: 0,
              accuracy_rate: 0,
              last_study_date: null,
            },
            rpg_stats: {
              level: 1,
              current_xp: 0,
              next_level_xp: 100,
              total_xp: 0,
              avatar_url: '',
              title: 'Mock',
              unlocked_skills: [],
              achievements: [],
              word_cards: [],
              streak_days: 0,
              difficulty_mode: 'normal',
              is_onboarded: true,
              error_distribution: {},
            },
            updated_at: nowIso(),
          },
          streak: {
            success: true,
            current_streak: 0,
            longest_streak: 0,
            last_active_date: null,
            today_completed: false,
          },
        })
        return
      }
      if (path === '/api/streak') {
        await fulfillJson(route, {
          success: true,
          current_streak: 0,
          longest_streak: 0,
          last_active_date: null,
          today_completed: false,
        })
        return
      }
      await fulfillJson(route, { success: true, lesson: null, items: [], mission: null })
      return
    }

    if (path === '/api/chat/scenarios' && method === 'GET') {
      const language = (url.searchParams.get('language') === 'JP' ? 'JP' : 'EN') as Language
      await fulfillJson(route, { success: true, scenarios: scenarioCatalog[language] })
      return
    }

    if (path === '/api/chat/conversations' && method === 'GET') {
      const language = (url.searchParams.get('language') === 'JP' ? 'JP' : 'EN') as Language
      const items = Array.from(conversations.values()).filter(
        (item) => item.language === language,
      )
      await fulfillJson(route, {
        success: true,
        count: items.length,
        conversations: items,
      })
      return
    }

    if (path === '/api/chat/conversations' && method === 'POST') {
      const body = request.postDataJSON() as {
        language: Language
        scenario_id: MockConversation['scenario_id']
        title: string
      }
      conversationCounter += 1
      const conversationId = `conv-${conversationCounter}`
      const conversation: MockConversation = {
        conversation_id: conversationId,
        language: body.language,
        scenario_id: body.scenario_id,
        title: body.title,
        lesson_id: null,
        summary: null,
        summary_through_sequence: 0,
        summary_updated_at: null,
        created_at: nowIso(),
        updated_at: nowIso(),
        last_message_at: null,
      }
      conversations.set(conversationId, conversation)
      messages.set(conversationId, [])
      await fulfillJson(route, { success: true, conversation }, 201)
      return
    }

    if (path.endsWith('/messages') && method === 'GET') {
      const conversationId = path.split('/').slice(-2)[0]
      const items = messages.get(conversationId) ?? []
      await fulfillJson(route, {
        success: true,
        messages: items,
        limit: 50,
        has_more: false,
        next_before_sequence: null,
        next_after_sequence: null,
      })
      return
    }

    if (path.startsWith('/api/chat/conversations/') && method === 'PATCH') {
      const conversationId = path.split('/').pop()!
      const body = request.postDataJSON() as { title: string }
      const conversation = conversations.get(conversationId)
      if (!conversation) {
        await fulfillJson(route, {
          error: true,
          message: 'Conversation not found',
          code: 'conversation_not_found',
        }, 404)
        return
      }
      const updated = { ...conversation, title: body.title, updated_at: nowIso() }
      conversations.set(conversationId, updated)
      await fulfillJson(route, { success: true, conversation: updated })
      return
    }

    if (path.startsWith('/api/chat/conversations/') && method === 'DELETE') {
      const conversationId = path.split('/').pop()!
      conversations.delete(conversationId)
      messages.delete(conversationId)
      await fulfillJson(route, {
        success: true,
        message: 'Conversation deleted',
        conversation_id: conversationId,
      })
      return
    }

    if (path === '/api/chat/mock-turn' && method === 'POST') {
      const body = request.postDataJSON() as {
        conversation_id: string
        client_message_id: string
        text: string
      }
      const existing = messages.get(body.conversation_id) ?? []
      const userExisting = existing.find(
        (item) =>
          item.role === 'user' &&
          item.metadata?.client_message_id === body.client_message_id,
      )
      const assistantExisting = existing.find(
        (item) =>
          item.role === 'assistant' &&
          item.metadata?.client_message_id === body.client_message_id,
      )
      const userMessage =
        userExisting ??
        {
          message_id: `msg-${++messageCounter}`,
          conversation_id: body.conversation_id,
          role: 'user' as const,
          content: body.text,
          sequence_number: existing.length + 1,
          metadata: { client_message_id: body.client_message_id },
          created_at: nowIso(),
        }
      const assistantMessage =
        assistantExisting ??
        {
          message_id: `msg-${++messageCounter}`,
          conversation_id: body.conversation_id,
          role: 'assistant' as const,
          content: `Mock reply: ${body.text}`,
          sequence_number: userExisting ? existing.length : existing.length + 2,
          metadata: { client_message_id: body.client_message_id },
          created_at: nowIso(),
        }
      if (!userExisting) {
        existing.push(userMessage)
      }
      if (!assistantExisting) {
        existing.push(assistantMessage)
      }
      messages.set(body.conversation_id, existing)
      await fulfillJson(route, {
        success: true,
        events: [
          {
            type: 'chat.user.persisted',
            client_message_id: body.client_message_id,
            message: userMessage,
          },
          {
            type: 'chat.assistant.persisted',
            client_message_id: body.client_message_id,
            message: assistantMessage,
          },
        ],
      })
      return
    }

    await route.continue()
  })

  await page.addInitScript(() => {
    class MockSocket {
      static OPEN = 1
      url: string
      readyState = MockSocket.OPEN
      onopen: (() => void) | null = null
      onmessage: ((event: MessageEvent) => void) | null = null
      onerror: (() => void) | null = null
      onclose: (() => void) | null = null

      constructor(url: string) {
        this.url = url
        queueMicrotask(() => {
          this.onopen?.()
          const parsed = new URL(url)
          const conversationId = parsed.searchParams.get('conversation_id')
          const language = parsed.pathname.endsWith('/JP') ? 'JP' : 'EN'
          this.onmessage?.(
            new MessageEvent('message', {
              data: JSON.stringify({
                type: 'conversation.ready',
                conversation_id: conversationId,
                scenario_id: 'travel',
                scenario_label: 'Travel',
                language,
              }),
            }),
          )
        })
      }

      async send(payload: string) {
        const parsed = JSON.parse(payload)
        const url = new URL(this.url)
        const conversationId = url.searchParams.get('conversation_id')
        const response = await fetch('/api/chat/mock-turn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...parsed,
            conversation_id: conversationId,
          }),
        })
        const body = await response.json()
        for (const event of body.events) {
          this.onmessage?.(
            new MessageEvent('message', {
              data: JSON.stringify(event),
            }),
          )
        }
      }

      close() {
        this.onclose?.()
      }
    }

    Object.defineProperty(window, 'WebSocket', {
      configurable: true,
      writable: true,
      value: MockSocket,
    })
  })
}

test('mocked persisted chat flow restores and isolates conversation state', async ({
  page,
}) => {
  await installPersistedChatMocks(page)
  page.on('dialog', async (dialog) => {
    if (dialog.type() === 'prompt') {
      await dialog.accept('Travel Renamed')
      return
    }
    await dialog.accept()
  })

  await page.goto('/workspace?tab=chat')
  await page.getByTestId('chat-scenario-select').selectOption('travel')
  await page.getByTestId('chat-new-conversation').click()

  await expect(page.locator('[data-testid^="conversation-item-"]').first()).toContainText('Travel')
  await page.getByTestId('chat-input').fill('Hello there')
  await page.getByTestId('chat-send').click()
  await expect(page.getByText('Mock reply: Hello there')).toBeVisible()

  await page.reload()
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText('Hello there')
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText('Mock reply: Hello there')

  await page.getByTestId('rename-conversation-conv-1').click()
  await expect(page.locator('[data-testid^="conversation-item-"]').first()).toContainText('Travel Renamed')

  await page.locator('select.workspace-language').selectOption('JP')
  await expect(page.getByTestId('chat-empty-state')).toBeVisible()
  await page.getByTestId('chat-new-conversation').click()
  await expect(page.locator('[data-testid^="conversation-item-"]').first()).toContainText(
    'Daily Conversation',
  )

  await page.locator('select.workspace-language').selectOption('EN')
  await expect(page.locator('[data-testid^="conversation-item-"]').first()).toContainText('Travel Renamed')
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText('Hello there')

  await page.getByTestId('delete-conversation-conv-1').click()
  await expect(page.getByTestId('chat-empty-state')).toBeVisible()
})
