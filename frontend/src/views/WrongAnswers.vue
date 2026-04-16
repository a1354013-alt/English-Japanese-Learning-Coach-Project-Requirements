<template>
  <section class="grid" style="margin-top: 1rem">
    <div class="panel row between center">
      <div>
        <h2 style="margin: 0">Wrong Answer Notebook</h2>
        <p style="margin: 0.2rem 0 0; color: #475569">Review, retry, and master your mistakes.</p>
      </div>
      <div class="row gap-sm center" style="min-width: 280px">
        <select v-model="statusFilter">
          <option value="active">Active</option>
          <option value="mastered">Mastered</option>
          <option value="all">All</option>
        </select>
        <button class="secondary" type="button" @click="loadItems" :disabled="loading">
          {{ loading ? 'Loading…' : 'Refresh' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="panel">Loading…</div>
    <div v-else-if="error" class="panel">
      <p style="color: #b91c1c; margin: 0 0 0.75rem">{{ error }}</p>
      <button type="button" @click="loadItems">Retry</button>
    </div>

    <div v-else-if="items.length === 0" class="panel">
      <p style="margin: 0">No items yet.</p>
      <p style="margin: 0.35rem 0 0; color: #475569">Answer a quiz question wrong and it will show up here automatically.</p>
    </div>

    <div v-else class="grid">
      <article v-for="item in items" :key="item.id" class="panel grid" style="gap: 0.75rem">
        <div class="row between center" style="gap: 1rem; flex-wrap: wrap">
          <div>
            <strong>{{ item.question_type.toUpperCase() }}</strong>
            <span style="color: #475569"> · {{ item.language }}</span>
            <span style="color: #475569"> · {{ formatDate(item.created_at) }}</span>
            <span v-if="item.wrong_count > 1" style="color: #475569"> · Wrong ×{{ item.wrong_count }}</span>
          </div>
          <span
            :style="{
              padding: '0.15rem 0.55rem',
              borderRadius: '999px',
              border: '1px solid #e2e8f0',
              background: item.status === 'mastered' ? '#ecfdf5' : '#eff6ff',
              color: item.status === 'mastered' ? '#065f46' : '#1d4ed8',
              fontSize: '0.85rem',
            }"
          >
            {{ item.status }}
          </span>
        </div>

        <div>
          <div style="color: #475569; font-size: 0.9rem; margin-bottom: 0.25rem">Question</div>
          <div style="white-space: pre-wrap">{{ item.question }}</div>
        </div>

        <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))">
          <div>
            <div style="color: #475569; font-size: 0.9rem; margin-bottom: 0.25rem">Your answer</div>
            <div style="white-space: pre-wrap; color: #b91c1c">{{ item.user_answer }}</div>
          </div>
          <div>
            <div style="color: #475569; font-size: 0.9rem; margin-bottom: 0.25rem">Correct answer</div>
            <div style="white-space: pre-wrap; color: #065f46">{{ item.correct_answer }}</div>
          </div>
        </div>

        <div v-if="retryingId === item.id" class="panel" style="background: #f8fafc">
          <div class="row gap-sm center" style="flex-wrap: wrap">
            <input v-model="retryAnswer" placeholder="Type your answer and retry" style="flex: 1 1 240px" />
            <button type="button" @click="submitRetry(item)" :disabled="submittingRetry">
              {{ submittingRetry ? 'Checking…' : 'Submit' }}
            </button>
            <button class="secondary" type="button" @click="cancelRetry" :disabled="submittingRetry">Cancel</button>
          </div>
          <p v-if="retryFeedback" style="margin: 0.6rem 0 0" :style="{ color: retryFeedback.ok ? '#065f46' : '#b91c1c' }">
            {{ retryFeedback.ok ? 'Correct! Marked as mastered.' : 'Not yet — keep practicing.' }}
          </p>
        </div>

        <div class="row gap-sm center" style="flex-wrap: wrap">
          <button class="secondary" type="button" @click="startRetry(item)" :disabled="retryingId !== null && retryingId !== item.id">
            Retry
          </button>
          <button
            v-if="item.status === 'active'"
            type="button"
            @click="markMastered(item)"
            :disabled="updatingId === item.id"
          >
            {{ updatingId === item.id ? 'Updating…' : 'Mark mastered' }}
          </button>
          <button class="secondary" type="button" @click="openSourceLesson(item)" :disabled="!item.source_lesson_id">
            Open source lesson
          </button>
          <button
            type="button"
            style="background: #ef4444"
            @click="removeItem(item)"
            :disabled="deletingId === item.id"
          >
            {{ deletingId === item.id ? 'Deleting…' : 'Delete' }}
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { wrongAnswerApi } from '@/services/api'
import type { WrongAnswer, WrongAnswerStatus } from '@/types'

const router = useRouter()

const items = ref<WrongAnswer[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const statusFilter = ref<'active' | 'mastered' | 'all'>('active')

const deletingId = ref<number | null>(null)
const updatingId = ref<number | null>(null)

const retryingId = ref<number | null>(null)
const retryAnswer = ref('')
const submittingRetry = ref(false)
const retryFeedback = ref<{ ok: boolean } | null>(null)

const formatDate = (iso: string) => new Date(iso).toLocaleString('zh-TW')

const loadItems = async () => {
  loading.value = true
  error.value = null
  try {
    const status: WrongAnswerStatus | undefined = statusFilter.value === 'all' ? undefined : statusFilter.value
    const res = await wrongAnswerApi.listWrongAnswers({ status })
    items.value = res.items
  } catch {
    error.value = 'Could not load your wrong answers. Check that the API is running and try again.'
  } finally {
    loading.value = false
  }
}

const removeItem = async (item: WrongAnswer) => {
  deletingId.value = item.id
  try {
    await wrongAnswerApi.deleteWrongAnswer(item.id)
    items.value = items.value.filter((x) => x.id !== item.id)
    if (retryingId.value === item.id) {
      cancelRetry()
    }
  } finally {
    deletingId.value = null
  }
}

const markMastered = async (item: WrongAnswer) => {
  updatingId.value = item.id
  try {
    const res = await wrongAnswerApi.updateStatus(item.id, 'mastered')
    if (statusFilter.value === 'active') {
      items.value = items.value.filter((x) => x.id !== item.id)
    } else {
      items.value = items.value.map((x) => (x.id === item.id ? res.item : x))
    }
  } finally {
    updatingId.value = null
  }
}

const openSourceLesson = (item: WrongAnswer) => {
  if (!item.source_lesson_id) return
  router.push(`/lesson/${item.source_lesson_id}`)
}

const startRetry = (item: WrongAnswer) => {
  retryingId.value = item.id
  retryAnswer.value = ''
  retryFeedback.value = null
}

const cancelRetry = () => {
  retryingId.value = null
  retryAnswer.value = ''
  retryFeedback.value = null
}

const submitRetry = async (item: WrongAnswer) => {
  const answer = retryAnswer.value.trim()
  if (answer.length === 0) return
  submittingRetry.value = true
  retryFeedback.value = null
  try {
    const res = await wrongAnswerApi.retry(item.id, answer)
    retryFeedback.value = { ok: res.correct }
    if (res.correct) {
      if (statusFilter.value === 'active') {
        items.value = items.value.filter((x) => x.id !== item.id)
        cancelRetry()
      } else {
        items.value = items.value.map((x) => (x.id === item.id ? res.item : x))
      }
    } else {
      items.value = items.value.map((x) => (x.id === item.id ? res.item : x))
    }
  } finally {
    submittingRetry.value = false
  }
}

watch(statusFilter, () => {
  void loadItems()
})

onMounted(loadItems)
</script>

