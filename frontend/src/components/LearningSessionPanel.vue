<template>
  <div class="section-card session-panel" data-testid="learning-session-panel">
    <div class="section-header">
      <div>
        <h2>Learning Session</h2>
      </div>
      <select v-model="language" @change="reload">
        <option value="EN">English</option>
        <option value="JP">Japanese</option>
      </select>
    </div>

    <div class="session-controls">
      <button
        v-for="minutes in [10, 20, 30]"
        :key="minutes"
        type="button"
        :class="{ active: plannedMinutes === minutes }"
        @click="plannedMinutes = minutes"
      >
        {{ minutes }} min
      </button>
      <input v-model.number="plannedMinutes" type="number" min="1" max="480" />
      <button type="button" :disabled="loading" @click="startOrResume">
        {{ activeSession ? 'Resume' : 'Start' }}
      </button>
    </div>

    <div v-if="error" class="error-text">{{ error }}</div>

    <div v-if="activeSession" class="session-grid">
      <article class="stat-card">
        <p class="stat-label">Language</p>
        <p class="stat-value">{{ activeSession.language }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">Elapsed</p>
        <p class="stat-value">{{ formatDuration(elapsedSeconds) }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">Events</p>
        <p class="stat-value">{{ events.length }}</p>
      </article>
    </div>

    <div v-if="activeSession" class="note-row">
      <input v-model="noteText" maxlength="500" placeholder="Session note" />
      <button type="button" :disabled="!canAddNote" @click="addNote">
        {{ actionLoading.note ? 'Adding...' : 'Add note' }}
      </button>
    </div>

    <div v-if="activeSession" class="session-actions">
      <button
        type="button"
        :disabled="actionLoading.complete || activeSession.status !== 'active'"
        @click="completeSession"
      >
        Complete
      </button>
      <button
        type="button"
        class="secondary"
        :disabled="actionLoading.abandon || activeSession.status !== 'active'"
        @click="abandonSession"
      >
        Abandon
      </button>
    </div>

    <div v-if="summary" class="surface-muted summary-box">
      <strong>Summary</strong>
      <p>
        {{ summary.status }} · {{ summary.total_event_count }} events ·
        {{ formatDuration(summary.duration_seconds ?? 0) }}
      </p>
    </div>

    <div class="timeline">
      <h3>Timeline</h3>
      <p v-if="!events.length" class="section-description">No events yet.</p>
      <ol v-else>
        <li v-for="event in events" :key="event.event_id">
          <span>{{ event.event_type }}</span>
          <small>{{ new Date(event.occurred_at).toLocaleString() }}</small>
          <em v-if="event.metadata?.note">{{ event.metadata.note }}</em>
        </li>
      </ol>
    </div>

    <div class="history">
      <h3>History</h3>
      <button
        type="button"
        class="secondary"
        :disabled="actionLoading.history"
        @click="refreshHistory"
      >
        Refresh
      </button>
      <p v-if="!history.length" class="section-description">
        No previous Sessions yet.
      </p>
      <div v-if="history.length" class="history-list">
        <button
          v-for="session in history"
          :key="session.session_id"
          type="button"
          class="history-item"
          @click="selectHistory(session.session_id)"
        >
          <span>{{ session.language }} · {{ session.status }}</span>
          <small>{{ new Date(session.started_at).toLocaleString() }}</small>
        </button>
      </div>
    </div>

    <div class="weekly-review" data-testid="weekly-review">
      <div class="section-header compact">
        <div>
          <h3>Weekly Review</h3>
          <p v-if="weeklyInsight" class="section-description">
            {{ new Date(weeklyInsight.week_start).toLocaleDateString() }} -
            {{ new Date(weeklyInsight.week_end).toLocaleDateString() }}
          </p>
        </div>
        <button type="button" class="secondary" @click="saveGoal">
          Save goals
        </button>
      </div>

      <div v-if="goal" class="goal-grid">
        <label>
          Daily minutes
          <input
            v-model.number="goal.daily_minutes"
            type="number"
            min="1"
            max="480"
          />
        </label>
        <label>
          Weekly sessions
          <input
            v-model.number="goal.weekly_sessions"
            type="number"
            min="1"
            max="28"
          />
        </label>
        <label>
          Weekly minutes
          <input
            v-model.number="goal.weekly_minutes"
            type="number"
            min="1"
            max="3360"
          />
        </label>
      </div>

      <div v-if="weeklyInsight" class="session-grid">
        <article class="stat-card">
          <p class="stat-label">Completed</p>
          <p class="stat-value">{{ weeklyInsight.completed_session_count }}</p>
        </article>
        <article class="stat-card">
          <p class="stat-label">Time</p>
          <p class="stat-value">
            {{ formatDuration(weeklyInsight.total_completed_duration_seconds) }}
          </p>
        </article>
        <article class="stat-card">
          <p class="stat-label">Active days</p>
          <p class="stat-value">{{ weeklyInsight.active_learning_days }}</p>
        </article>
        <article class="stat-card">
          <p class="stat-label">Review</p>
          <p class="stat-value">
            {{
              weeklyInsight.review_correctness_rate == null
                ? 'n/a'
                : `${weeklyInsight.review_correctness_rate.toFixed(0)}%`
            }}
          </p>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { learningGoalApi, learningSessionApi } from '@/services/api'
import type {
  Language,
  LearningGoal,
  LearningSessionEventRecord,
  LearningSessionRecord,
  LearningSessionSummary,
  WeeklyLearningInsight,
} from '@/types'

type PendingNoteOperation = {
  sessionId: string
  note: string
  operationId: string
}

const language = ref<Language>('EN')
const plannedMinutes = ref(20)
const activeSession = ref<LearningSessionRecord | null>(null)
const events = ref<LearningSessionEventRecord[]>([])
const history = ref<LearningSessionRecord[]>([])
const summary = ref<LearningSessionSummary | null>(null)
const goal = ref<LearningGoal | null>(null)
const weeklyInsight = ref<WeeklyLearningInsight | null>(null)
const noteText = ref('')
const pendingNoteOperation = ref<PendingNoteOperation | null>(null)
const nowMs = ref(Date.now())
const loading = ref(false)
const error = ref<string | null>(null)
const actionLoading = ref({
  note: false,
  complete: false,
  abandon: false,
  history: false,
  goal: false,
})

let timer: number | undefined
let reloadSequence = 0
let historySelectionSequence = 0

const elapsedSeconds = computed(() => {
  if (!activeSession.value) return 0
  return Math.max(
    0,
    Math.floor(
      (nowMs.value - new Date(activeSession.value.started_at).getTime()) / 1000,
    ),
  )
})

const canAddNote = computed(
  () =>
    activeSession.value?.status === 'active' &&
    !!noteText.value.trim() &&
    !actionLoading.value.note,
)

const setError = (fallback: string, err: unknown) => {
  console.error(err)
  if (err && typeof err === 'object' && 'response' in err) {
    const response = (err as { response?: { data?: unknown } }).response
    const data = response?.data
    if (data && typeof data === 'object' && 'message' in data) {
      const message = (data as { message?: unknown }).message
      if (typeof message === 'string' && message.trim()) {
        error.value = message
        return
      }
    }
  }
  error.value = fallback
}

const goalIsValid = (value: LearningGoal) => {
  return (
    Number.isInteger(value.daily_minutes) &&
    value.daily_minutes >= 1 &&
    value.daily_minutes <= 480 &&
    Number.isInteger(value.weekly_sessions) &&
    value.weekly_sessions >= 1 &&
    value.weekly_sessions <= 28 &&
    (value.weekly_minutes == null ||
      (Number.isInteger(value.weekly_minutes) &&
        value.weekly_minutes >= 1 &&
        value.weekly_minutes <= 3360))
  )
}

const clientKey = (prefix: string, id: string) => {
  const storageKey = `learning-session:${prefix}:${id}`
  const existing = window.localStorage.getItem(storageKey)
  if (existing) return existing
  const random =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
  const created = `${prefix}:${id}:${random}`
  window.localStorage.setItem(storageKey, created)
  return created
}

const randomOperationId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 18)}`
}

const noteOperationFor = (sessionId: string, note: string) => {
  if (
    pendingNoteOperation.value?.sessionId === sessionId &&
    pendingNoteOperation.value.note === note
  ) {
    return pendingNoteOperation.value
  }
  const operation = {
    sessionId,
    note,
    operationId: `note-${randomOperationId()}`,
  }
  pendingNoteOperation.value = operation
  return operation
}

const mergeCanonicalEvent = (event: LearningSessionEventRecord) => {
  const byEventId = events.value.filter(
    (existing) => existing.event_id !== event.event_id,
  )
  events.value = [...byEventId, event].sort(
    (a, b) => a.sequence_number - b.sequence_number,
  )
}

const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}:${rest.toString().padStart(2, '0')}`
}

const loadEvents = async (sessionId = activeSession.value?.session_id) => {
  if (!sessionId) return []
  return (await learningSessionApi.listEvents(sessionId)).events
}

const loadHistory = async (selectedLanguage = language.value) => {
  return (await learningSessionApi.list(selectedLanguage, 10)).sessions
}

const refreshHistory = async () => {
  if (actionLoading.value.history) return
  actionLoading.value.history = true
  error.value = null
  try {
    history.value = await loadHistory()
  } catch (err) {
    setError('Unable to refresh Session history.', err)
  } finally {
    actionLoading.value.history = false
  }
}

const loadGoalAndInsight = async (selectedLanguage = language.value) => {
  const [goalResponse, insightResponse] = await Promise.all([
    learningGoalApi.get(selectedLanguage),
    learningGoalApi.weeklyInsight(selectedLanguage),
  ])
  return {
    goal: goalResponse.goal,
    insight: insightResponse.insight,
  }
}

const reload = async () => {
  const requestId = ++reloadSequence
  const selectedLanguage = language.value
  loading.value = true
  error.value = null
  summary.value = null
  try {
    const active = await learningSessionApi.getActive(selectedLanguage)
    if (requestId !== reloadSequence || selectedLanguage !== language.value)
      return
    const [loadedEvents, loadedHistory, loadedGoalAndInsight] =
      await Promise.all([
        loadEvents(active.session?.session_id),
        loadHistory(selectedLanguage),
        loadGoalAndInsight(selectedLanguage),
      ])
    if (requestId !== reloadSequence || selectedLanguage !== language.value)
      return
    activeSession.value = active.session
    events.value = loadedEvents
    history.value = loadedHistory
    goal.value = loadedGoalAndInsight.goal
    weeklyInsight.value = loadedGoalAndInsight.insight
  } catch (err) {
    setError('Unable to load session state.', err)
  } finally {
    if (requestId === reloadSequence) loading.value = false
  }
}

const startOrResume = async () => {
  if (loading.value) return
  if (activeSession.value) {
    await reload()
    return
  }
  if (
    !Number.isInteger(plannedMinutes.value) ||
    plannedMinutes.value < 1 ||
    plannedMinutes.value > 480
  ) {
    error.value = 'Planned minutes must be between 1 and 480.'
    return
  }
  loading.value = true
  error.value = null
  const selectedLanguage = language.value
  try {
    activeSession.value = (
      await learningSessionApi.start(selectedLanguage, plannedMinutes.value)
    ).session
    if (selectedLanguage !== language.value) return
    const [loadedEvents, loadedHistory] = await Promise.all([
      loadEvents(),
      loadHistory(selectedLanguage),
    ])
    if (selectedLanguage !== language.value) return
    events.value = loadedEvents
    history.value = loadedHistory
  } catch (err) {
    setError('Unable to start session.', err)
    await reload()
  } finally {
    loading.value = false
  }
}

const addNote = async () => {
  if (actionLoading.value.note) return
  if (!activeSession.value || activeSession.value.status !== 'active') return
  if (!noteText.value.trim()) return
  actionLoading.value.note = true
  error.value = null
  const sessionId = activeSession.value.session_id
  const note = noteText.value.trim()
  const operation = noteOperationFor(sessionId, note)
  const key = `session-note:${operation.operationId}`
  try {
    const created = await learningSessionApi.addNote(sessionId, note, key)
    pendingNoteOperation.value = null
    noteText.value = ''
    mergeCanonicalEvent(created.event)
  } catch (err) {
    setError('Unable to add note.', err)
  } finally {
    actionLoading.value.note = false
  }
}

const completeSession = async () => {
  if (actionLoading.value.complete) return
  if (!activeSession.value || !window.confirm('Complete this Session?')) return
  const sessionId = activeSession.value.session_id
  const key = clientKey('complete', sessionId)
  actionLoading.value.complete = true
  error.value = null
  try {
    const completed = await learningSessionApi.complete(sessionId, key)
    activeSession.value = completed.session
    summary.value = (await learningSessionApi.summary(sessionId)).summary
    activeSession.value = null
    events.value = await loadEvents(sessionId)
    const [loadedHistory, loadedGoalAndInsight] = await Promise.all([
      loadHistory(),
      loadGoalAndInsight(),
    ])
    history.value = loadedHistory
    goal.value = loadedGoalAndInsight.goal
    weeklyInsight.value = loadedGoalAndInsight.insight
  } catch (err) {
    setError('Unable to complete Session.', err)
  } finally {
    actionLoading.value.complete = false
  }
}

const abandonSession = async () => {
  if (actionLoading.value.abandon) return
  if (!activeSession.value || !window.confirm('Abandon this Session?')) return
  const sessionId = activeSession.value.session_id
  actionLoading.value.abandon = true
  error.value = null
  try {
    const abandoned = await learningSessionApi.abandon(sessionId)
    activeSession.value = abandoned.session
    summary.value = (await learningSessionApi.summary(sessionId)).summary
    const [loadedHistory, loadedGoalAndInsight] = await Promise.all([
      loadHistory(),
      loadGoalAndInsight(),
    ])
    history.value = loadedHistory
    goal.value = loadedGoalAndInsight.goal
    weeklyInsight.value = loadedGoalAndInsight.insight
  } catch (err) {
    setError('Unable to abandon Session.', err)
  } finally {
    actionLoading.value.abandon = false
  }
}

const selectHistory = async (sessionId: string) => {
  const requestId = ++historySelectionSequence
  actionLoading.value.history = true
  error.value = null
  try {
    const [selectedSummary, selectedEvents] = await Promise.all([
      learningSessionApi.summary(sessionId),
      loadEvents(sessionId),
    ])
    if (requestId !== historySelectionSequence) return
    summary.value = selectedSummary.summary
    events.value = selectedEvents
  } catch (err) {
    setError('Unable to load Session summary.', err)
  } finally {
    if (requestId === historySelectionSequence) {
      actionLoading.value.history = false
    }
  }
}

const saveGoal = async () => {
  if (!goal.value) return
  if (actionLoading.value.goal) return
  if (!goalIsValid(goal.value)) {
    error.value = 'Goal values are outside the supported range.'
    return
  }
  const selectedLanguage = language.value
  actionLoading.value.goal = true
  error.value = null
  try {
    const saved = await learningGoalApi.update(selectedLanguage, {
      daily_minutes: goal.value.daily_minutes,
      weekly_sessions: goal.value.weekly_sessions,
      weekly_minutes: goal.value.weekly_minutes,
    })
    if (selectedLanguage !== language.value) return
    goal.value = saved.goal
    weeklyInsight.value = (
      await learningGoalApi.weeklyInsight(selectedLanguage)
    ).insight
  } catch (err) {
    setError('Unable to save goals.', err)
  } finally {
    actionLoading.value.goal = false
  }
}

onMounted(() => {
  timer = window.setInterval(() => {
    nowMs.value = Date.now()
  }, 1000)
  void reload()
})

onUnmounted(() => {
  if (timer !== undefined) window.clearInterval(timer)
})
</script>

<style scoped>
.session-panel {
  display: grid;
  gap: 16px;
}

.session-controls,
.note-row,
.session-actions,
.goal-grid,
.session-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.session-controls button.active {
  border-color: #1d4ed8;
}

.timeline ol {
  display: grid;
  gap: 8px;
  padding-left: 20px;
}

.timeline li {
  display: grid;
  gap: 2px;
}

.timeline small,
.history-item small {
  color: #64748b;
}

.history-list {
  display: grid;
  gap: 8px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.summary-box {
  padding: 12px;
}

.compact {
  margin-bottom: 0;
}
</style>
