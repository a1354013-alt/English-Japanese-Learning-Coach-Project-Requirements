<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <div>
        <h2 style="margin: 0">Chat Tutor (Preview)</h2>
        <p style="margin: 0.2rem 0 0; color: #475569; font-size: 0.9rem">
          Preview feature for the demo build. Requires a configured AI provider; chat history is not persisted.
        </p>
      </div>
      <select v-model="selectedLanguage" @change="reconnect">
        <option value="EN">English</option>
        <option value="JP">Japanese</option>
      </select>
    </div>

    <div class="panel">
      <div class="chat-container">
        <div class="messages" ref="messagesContainer">
          <div v-if="connectionStatus === 'connecting'" class="system-message">
            Connecting...
          </div>
          <div v-else-if="connectionStatus === 'reconnecting'" class="system-message">
            Reconnecting...
          </div>
          <div v-else-if="connectionStatus === 'error'" class="system-message error">
            Connection failed. This preview may be unavailable unless an AI provider is configured.
            <button @click="reconnect" class="secondary" style="margin-left: 0.5rem">Reconnect</button>
          </div>

          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            :class="['message', msg.role]"
          >
            <strong>{{ msg.role === 'user' ? 'You' : 'Tutor' }}:</strong>
            <span>{{ msg.text }}</span>
          </div>
        </div>

        <form @submit.prevent="sendMessage" class="chat-input-row">
          <input
            v-model="inputText"
            type="text"
            placeholder="Type your message..."
            :disabled="connectionStatus !== 'connected'"
            style="flex: 1; padding: 0.5rem"
          />
          <button type="submit" :disabled="!inputText.trim() || connectionStatus !== 'connected'">
            Send
          </button>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, nextTick } from 'vue'

interface Message {
  role: 'user' | 'assistant' | 'system'
  text: string
}

type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'error' | 'disconnected'

const selectedLanguage = ref('EN')
const inputText = ref('')
const messages = ref<Message[]>([])
const connectionStatus = ref<ConnectionStatus>('disconnected')
const ws = ref<WebSocket | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)
const reconnectAttempts = ref(0)
const maxReconnectAttempts = 5

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const connect = () => {
  if (ws.value) {
    ws.value.close()
  }

  connectionStatus.value = 'connecting'
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/chat/${selectedLanguage.value}`

  try {
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      connectionStatus.value = 'connected'
      reconnectAttempts.value = 0
      messages.value.push({ role: 'system', text: `Connected to ${selectedLanguage.value} tutor.` })
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.text) {
          messages.value.push({ role: data.role || 'assistant', text: data.text })
          scrollToBottom()
        }
      } catch {
        messages.value.push({ role: 'system', text: 'Received invalid message format.' })
      }
    }

    ws.value.onerror = () => {
      connectionStatus.value = 'error'
    }

    ws.value.onclose = () => {
      if (connectionStatus.value === 'connected') {
        // Unexpected close, try reconnect
        handleReconnect()
      } else {
        connectionStatus.value = 'disconnected'
      }
    }
  } catch {
    connectionStatus.value = 'error'
  }
}

const handleReconnect = () => {
  if (reconnectAttempts.value >= maxReconnectAttempts) {
    connectionStatus.value = 'error'
    messages.value.push({ role: 'system', text: 'Max reconnection attempts reached.' })
    return
  }

  connectionStatus.value = 'reconnecting'
  reconnectAttempts.value++

  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 5000)
  setTimeout(() => {
    if (connectionStatus.value === 'reconnecting') {
      connect()
    }
  }, delay)
}

const reconnect = () => {
  reconnectAttempts.value = 0
  connect()
}

const sendMessage = () => {
  const text = inputText.value.trim()
  if (!text || !ws.value || ws.value.readyState !== WebSocket.OPEN) return

  messages.value.push({ role: 'user', text })
  ws.value.send(JSON.stringify({ text }))
  inputText.value = ''
  scrollToBottom()
}

onMounted(() => {
  connect()
})

onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 60vh;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  margin-bottom: 1rem;
  background: #f8fafc;
}

.message {
  margin-bottom: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  max-width: 80%;
}

.message.user {
  background: #dbeafe;
  margin-left: auto;
  text-align: right;
}

.message.assistant {
  background: #f1f5f9;
  margin-right: auto;
}

.message.system {
  background: #fef3c7;
  color: #92400e;
  font-style: italic;
  text-align: center;
  max-width: 100%;
}

.system-message {
  text-align: center;
  color: #64748b;
  font-style: italic;
  padding: 0.5rem;
}

.system-message.error {
  color: #b91c1c;
}

.chat-input-row {
  display: flex;
  gap: 0.5rem;
}

.chat-input-row button {
  min-width: 80px;
}

.chat-input-row button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-input-row input:disabled {
  background: #f1f5f9;
  cursor: not-allowed;
}
</style>
