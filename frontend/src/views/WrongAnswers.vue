<template>
  <section :class="['grid', 'view-page', { 'embedded-page': embedded }]">
    <div v-if="!embedded" class="panel row between center">
      <div>
        <h2 style="margin: 0">{{ t('mistakes.title') }}</h2>
        <p style="margin: 0.2rem 0 0; color: #475569">{{ t('mistakes.subtitle') }}</p>
      </div>
      <div class="row gap-sm center" style="min-width: 280px">
        <select v-model="statusFilter" :disabled="loading">
          <option value="active">{{ t('mistakes.active') }}</option>
          <option value="mastered">{{ t('mistakes.mastered') }}</option>
          <option value="all">{{ t('mistakes.all') }}</option>
        </select>
        <button class="secondary" type="button" @click="loadItems" :disabled="loading">
          {{ loading ? t('mistakes.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="panel">{{ t('mistakes.loading') }}</div>

    <div v-else-if="error" class="panel">
      <p style="color: #b91c1c; margin: 0 0 0.75rem">{{ error }}</p>
      <button type="button" @click="loadItems">{{ t('common.retry') }}</button>
    </div>

    <div v-else-if="items.length === 0" class="panel">
      <p style="margin: 0">{{ t('mistakes.empty') }}</p>
      <p style="margin: 0.35rem 0 0; color: #475569">
        {{ t('mistakes.emptyHint') }}
      </p>
    </div>

    <div v-else class="grid">
      <article v-for="item in items" :key="item.id" class="panel grid" style="gap: 0.75rem">
        <div class="row between center" style="gap: 1rem; flex-wrap: wrap">
          <div>
            <strong>{{ item.question_type.toUpperCase() }}</strong>
            <span style="color: #475569"> · {{ item.language }}</span>
            <span style="color: #475569"> · {{ formatDate(item.created_at) }}</span>
            <span v-if="item.wrong_count > 1" style="color: #475569"> · {{ t('mistakes.wrongCount', { count: item.wrong_count }) }}</span>
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
            {{ item.status === 'mastered' ? t('mistakes.mastered') : t('mistakes.active') }}
          </span>
        </div>

        <div>
          <div style="color: #475569; font-size: 0.9rem; margin-bottom: 0.25rem">{{ t('mistakes.question') }}</div>
          <div style="white-space: pre-wrap">{{ item.question }}</div>
        </div>

        <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))">
          <div>
            <div style="color: #475569; font-size: 0.9rem; margin-bottom: 0.25rem">{{ t('mistakes.yourAnswer') }}</div>
            <div style="white-space: pre-wrap; color: #b91c1c">{{ item.user_answer }}</div>
          </div>
          <div>
            <div style="color: #475569; font-size: 0.9rem; margin-bottom: 0.25rem">{{ t('mistakes.correctAnswer') }}</div>
            <div style="white-space: pre-wrap; color: #065f46">{{ item.correct_answer }}</div>
          </div>
        </div>

        <div v-if="retryingId === item.id" class="panel" style="background: #f8fafc">
          <div class="row gap-sm center" style="flex-wrap: wrap">
            <input v-model="retryAnswer" :placeholder="t('mistakes.retryPlaceholder')" style="flex: 1 1 240px" />
            <button type="button" @click="submitRetry(item)" :disabled="submittingRetry">
              {{ submittingRetry ? t('mistakes.checking') : t('mistakes.retrySubmit') }}
            </button>
            <button class="secondary" type="button" @click="cancelRetry" :disabled="submittingRetry">{{ t('mistakes.retryCancel') }}</button>
          </div>
          <p
            v-if="retryFeedback"
            style="margin: 0.6rem 0 0"
            :style="{ color: retryFeedback.ok ? '#065f46' : '#b91c1c' }"
          >
            {{ retryFeedback.ok ? t('mistakes.retryCorrect') : t('mistakes.retryIncorrect') }}
          </p>
        </div>

        <div class="row gap-sm center" style="flex-wrap: wrap">
          <button
            class="secondary"
            type="button"
            @click="startRetry(item)"
            :disabled="retryingId !== null && retryingId !== item.id"
          >
            {{ t('mistakes.retry') }}
          </button>
          <button v-if="item.status === 'active'" type="button" @click="markMastered(item)" :disabled="updatingId === item.id">
            {{ updatingId === item.id ? t('mistakes.updating') : t('mistakes.markMastered') }}
          </button>
          <button class="secondary" type="button" @click="openSourceLesson(item)" :disabled="!item.source_lesson_id">
            {{ t('mistakes.openSourceLesson') }}
          </button>
          <button type="button" style="background: #ef4444" @click="removeItem(item)" :disabled="deletingId === item.id">
            {{ deletingId === item.id ? t('mistakes.deleting') : t('mistakes.delete') }}
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { wrongAnswerApi } from '@/services/api'
import type { WrongAnswer, WrongAnswerStatus } from '@/types'

withDefaults(defineProps<{ embedded?: boolean }>(), {
  embedded: false,
})

const router = useRouter()
const { t } = useI18n()

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

const formatDate = (iso: string) => new Date(iso).toLocaleString()

const loadItems = async () => {
  loading.value = true
  error.value = null
  try {
    const status: WrongAnswerStatus | undefined = statusFilter.value === 'all' ? undefined : statusFilter.value
    const res = await wrongAnswerApi.listWrongAnswers({ status })
    items.value = res.items
  } catch (err) {
    console.error(err)
    error.value = t('mistakes.loadError')
  } finally {
    loading.value = false
  }
}

const removeItem = async (item: WrongAnswer) => {
  deletingId.value = item.id
  try {
    await wrongAnswerApi.deleteWrongAnswer(item.id)
    items.value = items.value.filter((x) => x.id !== item.id)
    if (retryingId.value === item.id) cancelRetry()
  } catch (err) {
    console.error(err)
    error.value = t('mistakes.deleteError')
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
  } catch (err) {
    console.error(err)
    error.value = t('mistakes.updateError')
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
  } catch (err) {
    console.error(err)
    error.value = t('mistakes.retryError')
  } finally {
    submittingRetry.value = false
  }
}

watch(statusFilter, () => {
  void loadItems()
})

onMounted(loadItems)
</script>
