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
      <button type="button" :disabled="!noteText.trim()" @click="addNote">
        Add note
      </button>
    </div>

    <div v-if="activeSession" class="session-actions">
      <button type="button" @click="completeSession">Complete</button>
      <button type="button" class="secondary" @click="abandonSession">
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
      <button type="button" class="secondary" @click="loadHistory">
        Refresh
      </button>
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

const language = ref<Language>('EN')
const plannedMinutes = ref(20)
const activeSession = ref<LearningSessionRecord | null>(null)
const events = ref<LearningSessionEventRecord[]>([])
const history = ref<LearningSessionRecord[]>([])
const summary = ref<LearningSessionSummary | null>(null)
const goal = ref<LearningGoal | null>(null)
const weeklyInsight = ref<WeeklyLearningInsight | null>(null)
const noteText = ref('')
const nowMs = ref(Date.now())
const loading = ref(false)
const error = ref<string | null>(null)

let timer: number | undefined

const elapsedSeconds = computed(() => {
  if (!activeSession.value) return 0
  return Math.max(
    0,
    Math.floor(
      (nowMs.value - new Date(activeSession.value.started_at).getTime()) / 1000,
    ),
  )
})

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

const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}:${rest.toString().padStart(2, '0')}`
}

const loadEvents = async () => {
  if (!activeSession.value) {
    events.value = []
    return
  }
  events.value = (
    await learningSessionApi.listEvents(activeSession.value.session_id)
  ).events
}

const loadHistory = async () => {
  history.value = (await learningSessionApi.list(language.value, 10)).sessions
}

const loadGoalAndInsight = async () => {
  goal.value = (await learningGoalApi.get(language.value)).goal
  weeklyInsight.value = (
    await learningGoalApi.weeklyInsight(language.value)
  ).insight
}

const reload = async () => {
  loading.value = true
  error.value = null
  summary.value = null
  try {
    activeSession.value = (
      await learningSessionApi.getActive(language.value)
    ).session
    await Promise.all([loadEvents(), loadHistory(), loadGoalAndInsight()])
  } catch (err) {
    console.error(err)
    error.value = 'Unable to load session state.'
  } finally {
    loading.value = false
  }
}

const startOrResume = async () => {
  if (activeSession.value) {
    await reload()
    return
  }
  loading.value = true
  error.value = null
  try {
    activeSession.value = (
      await learningSessionApi.start(language.value, plannedMinutes.value)
    ).session
    await Promise.all([loadEvents(), loadHistory()])
  } catch (err) {
    console.error(err)
    error.value = 'Unable to start session.'
    await reload()
  } finally {
    loading.value = false
  }
}

const addNote = async () => {
  if (!activeSession.value || !noteText.value.trim()) return
  const note = noteText.value.trim()
  const key = clientKey('note', `${activeSession.value.session_id}:${note}`)
  const created = await learningSessionApi.addNote(
    activeSession.value.session_id,
    note,
    key,
  )
  noteText.value = ''
  events.value = [...events.value, created.event].sort(
    (a, b) => a.sequence_number - b.sequence_number,
  )
}

const completeSession = async () => {
  if (!activeSession.value || !window.confirm('Complete this Session?')) return
  const sessionId = activeSession.value.session_id
  const key = clientKey('complete', sessionId)
  activeSession.value = (
    await learningSessionApi.complete(sessionId, key)
  ).session
  summary.value = (await learningSessionApi.summary(sessionId)).summary
  activeSession.value = null
  await Promise.all([loadHistory(), loadGoalAndInsight()])
}

const abandonSession = async () => {
  if (!activeSession.value || !window.confirm('Abandon this Session?')) return
  const sessionId = activeSession.value.session_id
  await learningSessionApi.abandon(sessionId)
  activeSession.value = null
  events.value = []
  await Promise.all([loadHistory(), loadGoalAndInsight()])
}

const selectHistory = async (sessionId: string) => {
  summary.value = (await learningSessionApi.summary(sessionId)).summary
  events.value = (await learningSessionApi.listEvents(sessionId)).events
}

const saveGoal = async () => {
  if (!goal.value) return
  goal.value = (
    await learningGoalApi.update(language.value, {
      daily_minutes: goal.value.daily_minutes,
      weekly_sessions: goal.value.weekly_sessions,
      weekly_minutes: goal.value.weekly_minutes,
    })
  ).goal
  weeklyInsight.value = (
    await learningGoalApi.weeklyInsight(language.value)
  ).insight
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
