<template>
  <section :class="['grid', 'view-page', { 'embedded-page': embedded }]">
    <div v-if="!embedded" class="panel row between center">
      <div>
        <h2 style="margin: 0">{{ tr('chat.title', 'Chat Tutor') }}</h2>
        <p style="margin: 0.2rem 0 0; color: #475569; font-size: 0.9rem">
          {{
            tr(
              'chat.subtitle',
              'Practice with persisted conversations that restore across reloads.',
            )
          }}
        </p>
      </div>
      <select v-model="selectedLanguage" @change="handleLanguageChange">
        <option value="EN">{{ tr('common.english', 'English') }}</option>
        <option value="JP">{{ tr('common.japanese', 'Japanese') }}</option>
      </select>
    </div>

    <div class="panel chat-layout">
      <aside class="conversation-sidebar">
        <div class="sidebar-header">
          <div>
            <h3 class="sidebar-title">
              {{ tr('chat.conversations', 'Conversations') }}
            </h3>
            <p class="sidebar-subtitle">
              {{ activeLanguageLabel }}
            </p>
          </div>
          <button
            type="button"
            class="secondary"
            data-testid="chat-retry-list"
            :disabled="activeState.listLoading"
            @click="loadConversationList(selectedLanguage)"
          >
            {{ tr('common.retry', 'Retry') }}
          </button>
        </div>

        <div class="new-conversation-box">
          <label class="sidebar-label" for="chat-scenario-select">
            {{ tr('chat.scenario', 'Scenario') }}
          </label>
          <select
            id="chat-scenario-select"
            v-model="activeState.pendingScenarioId"
            data-testid="chat-scenario-select"
            :disabled="
              activeState.creatingConversation || activeState.scenarioLoading
            "
          >
            <option
              v-for="scenario in activeState.scenarios"
              :key="scenario.scenario_id"
              :value="scenario.scenario_id"
            >
              {{ scenario.label }}
            </option>
          </select>
          <button
            type="button"
            class="primary"
            data-testid="chat-new-conversation"
            :disabled="
              activeState.creatingConversation ||
              activeState.scenarioLoading ||
              activeState.scenarios.length === 0
            "
            @click="createConversation"
          >
            {{
              activeState.creatingConversation
                ? tr('chat.creatingConversation', 'Creating...')
                : tr('chat.newConversation', 'New conversation')
            }}
          </button>
        </div>

        <div v-if="activeState.scenarioError" class="sidebar-feedback error">
          {{ activeState.scenarioError }}
        </div>
        <div v-if="activeState.listError" class="sidebar-feedback error">
          {{ activeState.listError }}
        </div>
        <div
          v-if="
            activeState.listLoading && activeState.conversations.length === 0
          "
          class="sidebar-feedback"
        >
          {{ tr('chat.loadingConversations', 'Loading conversations...') }}
        </div>
        <div
          v-else-if="activeState.conversations.length === 0"
          class="sidebar-feedback"
          data-testid="chat-empty-state"
        >
          {{ tr('chat.emptyConversations', 'No conversations yet.') }}
        </div>

        <ul
          v-else
          class="conversation-list"
          data-testid="chat-conversation-list"
        >
          <li
            v-for="conversation in activeState.conversations"
            :key="conversation.conversation_id"
          >
            <button
              type="button"
              class="conversation-item"
              :class="{
                active:
                  conversation.conversation_id ===
                  activeState.selectedConversationId,
              }"
              :data-testid="`conversation-item-${conversation.conversation_id}`"
              @click="selectConversation(conversation.conversation_id)"
            >
              <span class="conversation-name">{{ conversation.title }}</span>
              <span class="conversation-meta">
                {{ scenarioLabel(conversation.scenario_id) }}
              </span>
            </button>
            <div class="conversation-actions">
              <button
                type="button"
                class="link-button"
                :data-testid="`rename-conversation-${conversation.conversation_id}`"
                @click="renameConversation(conversation)"
              >
                {{ tr('chat.renameConversation', 'Rename') }}
              </button>
              <button
                type="button"
                class="link-button danger"
                :data-testid="`delete-conversation-${conversation.conversation_id}`"
                @click="deleteConversation(conversation)"
              >
                {{ tr('common.delete', 'Delete') }}
              </button>
            </div>
          </li>
        </ul>
      </aside>

      <div class="chat-main">
        <div class="chat-toolbar">
          <div>
            <h3 class="chat-heading">
              {{
                activeConversation?.title ??
                tr('chat.selectConversation', 'Select a conversation')
              }}
            </h3>
            <p class="chat-subheading">
              {{
                activeConversation
                  ? scenarioLabel(activeConversation.scenario_id)
                  : tr(
                      'chat.selectConversationHint',
                      'Choose or create a conversation to start chatting.',
                    )
              }}
            </p>
          </div>
          <button
            v-if="activeConversation"
            type="button"
            class="secondary"
            data-testid="chat-reconnect"
            @click="manualReconnect"
          >
            {{ tr('chat.reconnect', 'Reconnect') }}
          </button>
        </div>

        <div v-if="activeState.historyError" class="inline-feedback error">
          {{ activeState.historyError }}
        </div>
        <div v-if="connectionNotice" class="inline-feedback">
          {{ connectionNotice }}
        </div>

        <div
          ref="messagesContainer"
          class="messages"
          data-testid="chat-messages"
        >
          <button
            v-if="activeState.hasOlderMessages"
            type="button"
            class="secondary older-button"
            data-testid="chat-load-older"
            :disabled="activeState.loadingOlderMessages"
            @click="loadOlderMessages"
          >
            {{
              activeState.loadingOlderMessages
                ? tr('chat.loadingOlderMessages', 'Loading older messages...')
                : tr('chat.loadOlderMessages', 'Load older messages')
            }}
          </button>

          <div
            v-if="
              activeState.historyLoading &&
              activeState.renderMessages.length === 0
            "
            class="system-message"
          >
            {{ tr('chat.loadingHistory', 'Loading conversation history...') }}
          </div>
          <div
            v-else-if="
              activeConversation &&
              !activeState.historyLoading &&
              activeState.renderMessages.length === 0
            "
            class="system-message"
            data-testid="chat-history-empty"
          >
            {{
              tr('chat.emptyHistory', 'No messages yet. Send the first one.')
            }}
          </div>
          <div
            v-else-if="!activeConversation"
            class="system-message"
            data-testid="chat-unselected-empty"
          >
            {{
              tr(
                'chat.selectConversationHint',
                'Choose or create a conversation to start chatting.',
              )
            }}
          </div>

          <div
            v-for="msg in activeState.renderMessages"
            :key="msg.renderKey"
            :class="['message', msg.role, { failed: msg.status === 'failed' }]"
            :data-testid="`chat-message-${msg.renderKey}`"
          >
            <strong>
              {{
                msg.role === 'user'
                  ? tr('chat.you', 'You')
                  : tr('chat.tutor', 'Tutor')
              }}:
            </strong>
            <span>{{ msg.content }}</span>
            <button
              v-if="
                msg.role === 'user' &&
                msg.status === 'failed' &&
                msg.clientMessageId
              "
              type="button"
              class="link-button"
              :data-testid="`retry-message-${msg.clientMessageId}`"
              @click="retryMessage(msg.clientMessageId)"
            >
              {{ tr('common.retry', 'Retry') }}
            </button>
          </div>
        </div>

        <form class="chat-input-row" @submit.prevent="sendMessage">
          <input
            v-model="inputText"
            type="text"
            data-testid="chat-input"
            :placeholder="tr('chat.messagePlaceholder', 'Type your message...')"
            :disabled="!canSend"
            style="flex: 1; padding: 0.5rem"
          />
          <button
            type="submit"
            data-testid="chat-send"
            :disabled="!inputText.trim() || !canSend"
          >
            {{ tr('chat.send', 'Send') }}
          </button>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  reactive,
  ref,
  watch,
} from 'vue'
import { useI18n } from 'vue-i18n'
import { chatApi } from '@/services/api'
import type {
  ApiErrorPayload,
  ChatConversation,
  ChatMessage,
  ChatScenario,
  ChatScenarioId,
  Language,
} from '@/types'
import { resolveWebSocketBaseUrl } from '@/utils/wsUrl'

type ConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error'

type MessageStatus = 'sent' | 'sending' | 'failed'

interface ChatRenderMessage {
  renderKey: string
  canonicalMessageId?: string
  clientMessageId?: string
  role: 'user' | 'assistant'
  content: string
  sequenceNumber?: number
  status: MessageStatus
  createdAt?: string
}

interface LanguageChatState {
  conversations: ChatConversation[]
  scenarios: ChatScenario[]
  pendingScenarioId: ChatScenarioId
  selectedConversationId: string | null
  renderMessages: ChatRenderMessage[]
  listLoading: boolean
  listError: string | null
  scenarioLoading: boolean
  scenarioError: string | null
  historyLoading: boolean
  historyError: string | null
  loadingOlderMessages: boolean
  hasOlderMessages: boolean
  nextBeforeSequence: number | null
  creatingConversation: boolean
}

interface PersistedSocketMessage {
  type: string
  conversation_id?: string
  scenario_id?: ChatScenarioId
  scenario_label?: string
  client_message_id?: string
  message?: ChatMessage | string
  code?: string
  language?: Language
  content?: string
  text?: string
}

const props = withDefaults(
  defineProps<{ embedded?: boolean; language?: Language }>(),
  {
    embedded: false,
    language: undefined,
  },
)

const { t } = useI18n()
const tr = (key: string, fallback: string) => {
  const translated = t(key)
  return translated === key ? fallback : translated
}

const selectedLanguage = ref<Language>(props.language ?? 'EN')
const inputText = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const ws = ref<WebSocket | null>(null)
const reconnectTimer = ref<number | null>(null)
const connectionGeneration = ref(0)
const isMounted = ref(false)
const connectionStatus = ref<ConnectionStatus>('idle')
const wsBaseUrl = resolveWebSocketBaseUrl({
  wsBaseUrl: import.meta.env.VITE_WS_BASE_URL,
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
  location: window.location,
})

const SELECTED_CONVERSATION_STORAGE_KEYS: Record<Language, string> = {
  EN: 'chat.selectedConversationId.EN',
  JP: 'chat.selectedConversationId.JP',
}

const DEFAULT_SCENARIO_ID: ChatScenarioId = 'daily_conversation'

const createLanguageState = (): LanguageChatState => ({
  conversations: [],
  scenarios: [],
  pendingScenarioId: DEFAULT_SCENARIO_ID,
  selectedConversationId: null,
  renderMessages: [],
  listLoading: false,
  listError: null,
  scenarioLoading: false,
  scenarioError: null,
  historyLoading: false,
  historyError: null,
  loadingOlderMessages: false,
  hasOlderMessages: false,
  nextBeforeSequence: null,
  creatingConversation: false,
})

const languageStates: Record<Language, LanguageChatState> = reactive({
  EN: createLanguageState(),
  JP: createLanguageState(),
})

const activeState = computed(() => languageStates[selectedLanguage.value])

const activeConversation = computed(
  () =>
    activeState.value.conversations.find(
      (item) =>
        item.conversation_id === activeState.value.selectedConversationId,
    ) ?? null,
)

const activeLanguageLabel = computed(() =>
  selectedLanguage.value === 'EN'
    ? tr('common.english', 'English')
    : tr('common.japanese', 'Japanese'),
)

const canSend = computed(
  () =>
    Boolean(activeConversation.value) &&
    connectionStatus.value === 'connected' &&
    !activeState.value.historyLoading,
)

const connectionNotice = computed(() => {
  if (!activeConversation.value) return null
  if (connectionStatus.value === 'connecting') {
    return tr('chat.connecting', 'Connecting...')
  }
  if (connectionStatus.value === 'reconnecting') {
    return tr('chat.reconnecting', 'Reconnecting...')
  }
  if (connectionStatus.value === 'error') {
    return tr('chat.connectionFailed', 'Connection failed.')
  }
  return null
})

function getState(language: Language) {
  return languageStates[language]
}

function getStoredConversationId(language: Language): string | null {
  try {
    return window.localStorage.getItem(
      SELECTED_CONVERSATION_STORAGE_KEYS[language],
    )
  } catch {
    return null
  }
}

function setStoredConversationId(
  language: Language,
  conversationId: string | null,
) {
  try {
    const key = SELECTED_CONVERSATION_STORAGE_KEYS[language]
    if (conversationId) {
      window.localStorage.setItem(key, conversationId)
    } else {
      window.localStorage.removeItem(key)
    }
  } catch {
    // localStorage is best-effort only.
  }
}

function scenarioLabel(scenarioId: ChatScenarioId): string {
  return (
    activeState.value.scenarios.find((item) => item.scenario_id === scenarioId)
      ?.label ?? scenarioId
  )
}

function scrollToBottom() {
  nextTick(() => {
    const container = messagesContainer.value
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  })
}

function mergeCanonicalMessages(
  current: ChatRenderMessage[],
  incoming: ChatMessage[],
): ChatRenderMessage[] {
  const canonicalById = new Map<string, ChatRenderMessage>()
  const optimisticByClientId = new Map<string, ChatRenderMessage>()

  for (const item of current) {
    if (item.canonicalMessageId) {
      canonicalById.set(item.canonicalMessageId, item)
    }
    if (item.clientMessageId && !item.canonicalMessageId) {
      optimisticByClientId.set(item.clientMessageId, item)
    }
  }

  for (const message of incoming) {
    if (message.role === 'system') continue
    const clientMessageId =
      typeof message.metadata?.client_message_id === 'string'
        ? message.metadata.client_message_id
        : undefined
    const optimistic = clientMessageId
      ? optimisticByClientId.get(clientMessageId)
      : undefined
    const merged: ChatRenderMessage = {
      renderKey: message.message_id,
      canonicalMessageId: message.message_id,
      clientMessageId,
      role: message.role,
      content: message.content,
      sequenceNumber: message.sequence_number,
      status: 'sent',
      createdAt: message.created_at,
    }
    canonicalById.set(message.message_id, {
      ...(optimistic ?? canonicalById.get(message.message_id) ?? {}),
      ...merged,
    })
    if (clientMessageId) {
      optimisticByClientId.delete(clientMessageId)
    }
  }

  const combined = [
    ...canonicalById.values(),
    ...Array.from(optimisticByClientId.values()),
  ]

  return combined.sort((left, right) => {
    const leftSequence = left.sequenceNumber ?? Number.MAX_SAFE_INTEGER
    const rightSequence = right.sequenceNumber ?? Number.MAX_SAFE_INTEGER
    if (leftSequence !== rightSequence) {
      return leftSequence - rightSequence
    }
    return (left.createdAt ?? '').localeCompare(right.createdAt ?? '')
  })
}

function reconcilePersistedMessage(message: ChatMessage) {
  const state = activeState.value
  if (
    message.conversation_id !== state.selectedConversationId ||
    message.role === 'system'
  ) {
    return
  }
  state.renderMessages = mergeCanonicalMessages(state.renderMessages, [message])
  scrollToBottom()
}

function markMessageFailed(clientMessageId: string) {
  const state = activeState.value
  state.renderMessages = state.renderMessages.map((item) =>
    item.clientMessageId === clientMessageId
      ? { ...item, status: 'failed' }
      : item,
  )
}

function upsertOptimisticMessage(clientMessageId: string, content: string) {
  const state = activeState.value
  const existingIndex = state.renderMessages.findIndex(
    (item) => item.clientMessageId === clientMessageId,
  )
  const optimistic: ChatRenderMessage = {
    renderKey: `optimistic:${clientMessageId}`,
    clientMessageId,
    role: 'user',
    content,
    status: 'sending',
  }
  if (existingIndex >= 0) {
    state.renderMessages.splice(existingIndex, 1, {
      ...state.renderMessages[existingIndex],
      ...optimistic,
    })
  } else {
    state.renderMessages = [...state.renderMessages, optimistic]
  }
  scrollToBottom()
}

function parseApiMessage(error: unknown, fallback: string): string {
  const payload = (error as { response?: { data?: ApiErrorPayload } })?.response
    ?.data
  if (payload?.code === 'conversation_not_found') {
    return tr('chat.errorConversationNotFound', 'Conversation not found.')
  }
  if (payload?.code === 'invalid_chat_scenario') {
    return tr('chat.errorScenarioMismatch', 'Scenario is not supported.')
  }
  if (payload?.code === 'invalid_chat_language') {
    return tr(
      'chat.errorLanguageMismatch',
      'Language does not match this conversation.',
    )
  }
  if (payload?.code === 'invalid_chat_pagination') {
    return tr(
      'chat.errorInvalidPagination',
      'Unable to load this page of messages.',
    )
  }
  if (payload?.code === 'idempotency_conflict') {
    return tr(
      'chat.errorIdempotencyConflict',
      'This message conflicts with a previous retry.',
    )
  }
  if (payload?.code === 'provider_failure') {
    return tr(
      'chat.errorProviderFailure',
      'The chat provider is temporarily unavailable.',
    )
  }
  return payload?.message || fallback
}

async function loadScenarioList(language: Language) {
  const state = getState(language)
  state.scenarioLoading = true
  state.scenarioError = null
  try {
    const response = await chatApi.listScenarios(language)
    state.scenarios = response.scenarios
    if (
      !state.scenarios.some(
        (item) => item.scenario_id === state.pendingScenarioId,
      )
    ) {
      state.pendingScenarioId =
        state.scenarios[0]?.scenario_id ?? DEFAULT_SCENARIO_ID
    }
  } catch (error) {
    state.scenarioError = parseApiMessage(
      error,
      tr('chat.loadingScenariosFailed', 'Unable to load scenarios.'),
    )
  } finally {
    state.scenarioLoading = false
  }
}

async function loadConversationList(language: Language) {
  const state = getState(language)
  state.listLoading = true
  state.listError = null
  try {
    const response = await chatApi.listConversations(language)
    state.conversations = response.conversations
    const stored = getStoredConversationId(language)
    if (
      stored &&
      state.conversations.some((item) => item.conversation_id === stored)
    ) {
      state.selectedConversationId = stored
    } else if (
      state.selectedConversationId &&
      state.conversations.some(
        (item) => item.conversation_id === state.selectedConversationId,
      )
    ) {
      // keep current
    } else {
      state.selectedConversationId =
        state.conversations[0]?.conversation_id ?? null
    }
    setStoredConversationId(language, state.selectedConversationId)
  } catch (error) {
    state.listError = parseApiMessage(
      error,
      tr('chat.loadingConversationsFailed', 'Unable to load conversations.'),
    )
  } finally {
    state.listLoading = false
  }
}

async function loadMessages(language: Language, conversationId: string) {
  const state = getState(language)
  state.historyLoading = true
  state.historyError = null
  try {
    const response = await chatApi.readMessagesPage(conversationId, {
      limit: 50,
    })
    state.renderMessages = mergeCanonicalMessages([], response.messages)
    state.hasOlderMessages = response.has_more
    state.nextBeforeSequence = response.next_before_sequence ?? null
  } catch (error) {
    state.historyError = parseApiMessage(
      error,
      tr('chat.loadingHistoryFailed', 'Unable to load conversation history.'),
    )
    state.renderMessages = []
    state.hasOlderMessages = false
    state.nextBeforeSequence = null
  } finally {
    state.historyLoading = false
    scrollToBottom()
  }
}

async function selectConversation(conversationId: string) {
  const state = activeState.value
  if (
    state.selectedConversationId === conversationId &&
    state.renderMessages.length > 0
  ) {
    return
  }
  disposeActiveSocket()
  state.selectedConversationId = conversationId
  setStoredConversationId(selectedLanguage.value, conversationId)
  await loadMessages(selectedLanguage.value, conversationId)
  connectForSelectedConversation()
}

async function createConversation() {
  const state = activeState.value
  state.creatingConversation = true
  state.listError = null
  state.historyError = null
  try {
    const scenario = state.scenarios.find(
      (item) => item.scenario_id === state.pendingScenarioId,
    )
    const response = await chatApi.createConversation({
      language: selectedLanguage.value,
      scenario_id: state.pendingScenarioId,
      title: scenario?.label ?? 'New conversation',
    })
    state.conversations = [response.conversation, ...state.conversations]
    await selectConversation(response.conversation.conversation_id)
  } catch (error) {
    state.listError = parseApiMessage(
      error,
      tr('chat.createConversationFailed', 'Unable to create a conversation.'),
    )
  } finally {
    state.creatingConversation = false
  }
}

async function renameConversation(conversation: ChatConversation) {
  const nextTitle = window.prompt(
    tr('chat.renamePrompt', 'Rename conversation'),
    conversation.title,
  )
  if (nextTitle === null) return
  const trimmed = nextTitle.trim()
  if (!trimmed) return
  try {
    const response = await chatApi.renameConversation(
      conversation.conversation_id,
      trimmed,
    )
    const state = activeState.value
    state.conversations = state.conversations.map((item) =>
      item.conversation_id === conversation.conversation_id
        ? response.conversation
        : item,
    )
  } catch (error) {
    activeState.value.listError = parseApiMessage(
      error,
      tr('chat.renameConversationFailed', 'Unable to rename the conversation.'),
    )
  }
}

async function deleteConversation(conversation: ChatConversation) {
  const confirmed = window.confirm(
    tr('chat.deleteConversationConfirm', 'Delete this conversation?'),
  )
  if (!confirmed) return

  try {
    await chatApi.deleteConversation(conversation.conversation_id)
    const state = activeState.value
    const deletedSelected =
      state.selectedConversationId === conversation.conversation_id
    state.conversations = state.conversations.filter(
      (item) => item.conversation_id !== conversation.conversation_id,
    )
    if (deletedSelected) {
      disposeActiveSocket()
      state.renderMessages = []
      state.selectedConversationId =
        state.conversations[0]?.conversation_id ?? null
      setStoredConversationId(
        selectedLanguage.value,
        state.selectedConversationId,
      )
      if (state.selectedConversationId) {
        await loadMessages(selectedLanguage.value, state.selectedConversationId)
        connectForSelectedConversation()
      }
    }
  } catch (error) {
    activeState.value.listError = parseApiMessage(
      error,
      tr('chat.deleteConversationFailed', 'Unable to delete the conversation.'),
    )
  }
}

async function loadOlderMessages() {
  const conversationId = activeState.value.selectedConversationId
  const beforeSequence = activeState.value.nextBeforeSequence
  if (!conversationId || !beforeSequence) return
  const container = messagesContainer.value
  const previousScrollHeight = container?.scrollHeight ?? 0
  activeState.value.loadingOlderMessages = true
  try {
    const response = await chatApi.readMessagesPage(conversationId, {
      limit: 50,
      before_sequence: beforeSequence,
    })
    activeState.value.renderMessages = mergeCanonicalMessages(
      activeState.value.renderMessages,
      response.messages,
    )
    activeState.value.hasOlderMessages = response.has_more
    activeState.value.nextBeforeSequence = response.next_before_sequence ?? null
    await nextTick()
    if (container) {
      const delta = container.scrollHeight - previousScrollHeight
      container.scrollTop += delta
    }
  } catch (error) {
    activeState.value.historyError = parseApiMessage(
      error,
      tr('chat.loadingOlderMessagesFailed', 'Unable to load older messages.'),
    )
  } finally {
    activeState.value.loadingOlderMessages = false
  }
}

function cleanupReconnectTimer() {
  if (reconnectTimer.value !== null) {
    window.clearTimeout(reconnectTimer.value)
    reconnectTimer.value = null
  }
}

function closeSocket() {
  const socket = ws.value
  ws.value = null
  if (socket) {
    socket.close()
  }
}

function disposeActiveSocket() {
  cleanupReconnectTimer()
  connectionGeneration.value += 1
  closeSocket()
}

function connectForSelectedConversation() {
  const conversationId = activeState.value.selectedConversationId
  if (!conversationId || !isMounted.value) {
    connectionStatus.value = 'idle'
    return
  }

  disposeActiveSocket()
  const generation = connectionGeneration.value
  connectionStatus.value = 'connecting'

  const params = new URLSearchParams({ conversation_id: conversationId })
  const url = `${wsBaseUrl.replace(/\/$/, '')}/ws/chat/${selectedLanguage.value}?${params.toString()}`
  const socket = new WebSocket(url)
  ws.value = socket

  socket.onopen = () => {
    if (!isMounted.value || generation !== connectionGeneration.value) return
    connectionStatus.value = 'connected'
  }

  socket.onmessage = (event) => {
    if (!isMounted.value || generation !== connectionGeneration.value) return
    const data = JSON.parse(String(event.data)) as PersistedSocketMessage
    if (data.type === 'conversation.ready') {
      if (data.conversation_id) {
        activeState.value.selectedConversationId = data.conversation_id
        setStoredConversationId(selectedLanguage.value, data.conversation_id)
      }
      if (data.scenario_id && activeConversation.value) {
        activeState.value.conversations = activeState.value.conversations.map(
          (item) =>
            item.conversation_id === data.conversation_id
              ? { ...item, scenario_id: data.scenario_id ?? item.scenario_id }
              : item,
        )
      }
      return
    }
    if (
      data.type === 'chat.user.persisted' &&
      data.message &&
      typeof data.message !== 'string'
    ) {
      reconcilePersistedMessage(data.message)
      return
    }
    if (
      data.type === 'chat.assistant.persisted' &&
      data.message &&
      typeof data.message !== 'string'
    ) {
      reconcilePersistedMessage(data.message)
      return
    }
    if (data.type === 'chat.error') {
      if (data.client_message_id) {
        markMessageFailed(data.client_message_id)
      }
      activeState.value.historyError =
        data.content ||
        data.text ||
        (typeof data.message === 'string' ? data.message : undefined) ||
        tr('chat.providerFailed', 'Unable to complete this turn right now.')
      return
    }
    if (data.type === 'chat.validation_error') {
      if (data.client_message_id) {
        markMessageFailed(data.client_message_id)
      }
      activeState.value.historyError =
        data.content ||
        data.text ||
        (typeof data.message === 'string' ? data.message : undefined) ||
        tr('chat.providerFailed', 'Unable to complete this turn right now.')
    }
  }

  socket.onerror = () => {
    if (!isMounted.value || generation !== connectionGeneration.value) return
    connectionStatus.value = 'error'
  }

  socket.onclose = () => {
    if (!isMounted.value || generation !== connectionGeneration.value) return
    if (!activeState.value.selectedConversationId) {
      connectionStatus.value = 'idle'
      return
    }
    if (
      connectionStatus.value === 'connected' ||
      connectionStatus.value === 'connecting'
    ) {
      connectionStatus.value = 'reconnecting'
      cleanupReconnectTimer()
      reconnectTimer.value = window.setTimeout(() => {
        if (!isMounted.value || generation !== connectionGeneration.value)
          return
        connectForSelectedConversation()
      }, 1000)
      return
    }
    if (connectionStatus.value === 'error') {
      cleanupReconnectTimer()
    }
  }
}

function manualReconnect() {
  connectForSelectedConversation()
}

function clientMessageId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
}

function sendRawMessage(clientMessageIdValue: string, text: string) {
  const socket = ws.value
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    markMessageFailed(clientMessageIdValue)
    connectionStatus.value = 'error'
    return
  }
  socket.send(
    JSON.stringify({
      text,
      client_message_id: clientMessageIdValue,
    }),
  )
}

function sendMessage() {
  const text = inputText.value.trim()
  if (!text || !activeState.value.selectedConversationId) return
  const id = clientMessageId()
  upsertOptimisticMessage(id, text)
  sendRawMessage(id, text)
  inputText.value = ''
}

function retryMessage(clientMessageIdValue: string) {
  const message = activeState.value.renderMessages.find(
    (item) => item.clientMessageId === clientMessageIdValue,
  )
  if (!message) return
  upsertOptimisticMessage(clientMessageIdValue, message.content)
  sendRawMessage(clientMessageIdValue, message.content)
}

async function handleLanguageChange() {
  inputText.value = ''
  disposeActiveSocket()
  connectionStatus.value = 'idle'
  const state = activeState.value
  if (state.conversations.length === 0) {
    await Promise.all([
      loadScenarioList(selectedLanguage.value),
      loadConversationList(selectedLanguage.value),
    ])
  }
  if (state.selectedConversationId) {
    await loadMessages(selectedLanguage.value, state.selectedConversationId)
    connectForSelectedConversation()
  }
}

watch(
  () => props.language,
  async (language) => {
    if (language && language !== selectedLanguage.value) {
      selectedLanguage.value = language
      await handleLanguageChange()
    }
  },
)

onMounted(async () => {
  isMounted.value = true
  for (const language of ['EN', 'JP'] as const) {
    getState(language).selectedConversationId =
      getStoredConversationId(language)
  }
  await Promise.all([
    loadScenarioList('EN'),
    loadScenarioList('JP'),
    loadConversationList('EN'),
    loadConversationList('JP'),
  ])
  if (activeState.value.selectedConversationId) {
    await loadMessages(
      selectedLanguage.value,
      activeState.value.selectedConversationId,
    )
    connectForSelectedConversation()
  }
})

onUnmounted(() => {
  isMounted.value = false
  disposeActiveSocket()
})
</script>

<style scoped>
.chat-layout {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 1rem;
}

.conversation-sidebar,
.chat-main {
  min-height: 62vh;
}

.conversation-sidebar {
  border-right: 1px solid #e2e8f0;
  padding-right: 1rem;
}

.sidebar-header,
.chat-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
}

.sidebar-title,
.chat-heading {
  margin: 0;
}

.sidebar-subtitle,
.chat-subheading {
  margin: 0.25rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.sidebar-label {
  font-size: 0.85rem;
  color: #475569;
}

.new-conversation-box {
  display: grid;
  gap: 0.5rem;
  margin: 1rem 0;
}

.sidebar-feedback,
.inline-feedback {
  margin: 0.75rem 0;
  padding: 0.65rem 0.8rem;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 0.9rem;
}

.sidebar-feedback.error,
.inline-feedback.error {
  background: #fef2f2;
  color: #b91c1c;
}

.conversation-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}

.conversation-item {
  width: 100%;
  text-align: left;
  padding: 0.65rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
}

.conversation-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.conversation-name,
.conversation-meta {
  display: block;
}

.conversation-name {
  font-weight: 600;
}

.conversation-meta {
  margin-top: 0.2rem;
  color: #64748b;
  font-size: 0.85rem;
}

.conversation-actions {
  display: flex;
  gap: 0.75rem;
  padding: 0.2rem 0.1rem 0.45rem;
}

.chat-main {
  display: flex;
  flex-direction: column;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin: 1rem 0;
  background: #f8fafc;
}

.older-button {
  display: block;
  margin: 0 auto 1rem;
}

.message {
  margin-bottom: 0.75rem;
  padding: 0.65rem 0.8rem;
  border-radius: 8px;
  max-width: 84%;
}

.message.user {
  background: #dbeafe;
  margin-left: auto;
  text-align: right;
}

.message.assistant {
  background: #fff;
  margin-right: auto;
}

.message.failed {
  border: 1px solid #fca5a5;
}

.system-message {
  text-align: center;
  color: #64748b;
  font-style: italic;
  padding: 0.5rem;
}

.chat-input-row {
  display: flex;
  gap: 0.5rem;
}

.chat-input-row button {
  min-width: 88px;
}

.chat-input-row button:disabled,
.chat-input-row input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.link-button {
  padding: 0;
  border: 0;
  background: none;
  color: #2563eb;
  font-size: 0.85rem;
}

.link-button.danger {
  color: #b91c1c;
}

@media (max-width: 900px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }

  .conversation-sidebar {
    border-right: 0;
    border-bottom: 1px solid #e2e8f0;
    padding-right: 0;
    padding-bottom: 1rem;
  }
}
</style>
