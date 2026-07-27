<template>
  <div class="section-card session-panel" data-testid="learning-session-panel">
    <div class="section-header">
      <div>
        <h2>{{ tr('learningSession.title') }}</h2>
      </div>
      <select
        v-model="language"
        :aria-label="tr('learningSession.labels.language')"
        data-testid="learning-session-language"
        @change="reload"
      >
        <option value="EN">{{ tr('common.english') }}</option>
        <option value="JP">{{ tr('common.japanese') }}</option>
      </select>
    </div>

    <div class="session-controls">
      <button
        v-for="minutes in quickMinutes"
        :key="minutes"
        type="button"
        :class="{ active: plannedMinutes === minutes }"
        :aria-label="
          tr('learningSession.accessibility.quickMinutes', { minutes })
        "
        @click="plannedMinutes = minutes"
      >
        {{ tr('learningSession.plannedMinutesOption', { minutes }) }}
      </button>
      <input
        v-model.number="plannedMinutes"
        type="number"
        min="1"
        max="480"
        :aria-label="tr('learningSession.labels.plannedMinutes')"
        data-testid="learning-session-planned-minutes"
      />
      <button
        type="button"
        :disabled="loading"
        data-testid="learning-session-start"
        @click="startOrResume"
      >
        {{
          activeSession
            ? tr('learningSession.actions.resume')
            : tr('learningSession.actions.start')
        }}
      </button>
      <button
        type="button"
        class="secondary"
        :disabled="loading"
        @click="reload"
      >
        {{ loading ? 'Refreshing...' : 'Refresh' }}
      </button>
    </div>

    <div v-if="error" class="error-text" data-testid="learning-session-error">
      {{ error }}
    </div>

    <div v-if="activeSession" class="session-grid">
      <article class="stat-card">
        <p class="stat-label">{{ tr('learningSession.labels.language') }}</p>
        <p class="stat-value">{{ activeSession.language }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ tr('learningSession.labels.elapsed') }}</p>
        <p class="stat-value">{{ formatDuration(elapsedSeconds) }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ tr('learningSession.labels.events') }}</p>
        <p class="stat-value">{{ events.length }}</p>
      </article>
      <article class="stat-card">
        <p class="stat-label">{{ tr('learningSession.labels.status') }}</p>
        <p class="stat-value">
          {{ tr(`learningSession.statuses.${activeSession.status}`) }}
        </p>
      </article>
    </div>

    <div v-if="activeSession" class="note-row">
      <input
        v-model="noteText"
        maxlength="500"
        :placeholder="tr('learningSession.placeholders.note')"
        :aria-label="tr('learningSession.labels.note')"
        data-testid="learning-session-note-input"
      />
      <button
        type="button"
        :disabled="!canAddNote"
        data-testid="learning-session-add-note"
        @click="addNote"
      >
        {{
          actionLoading.note
            ? tr('learningSession.actions.addingNote')
            : tr('learningSession.actions.addNote')
        }}
      </button>
    </div>

    <div v-if="activeSession" class="session-actions">
      <button
        type="button"
        :disabled="actionLoading.complete || activeSession.status !== 'active'"
        data-testid="learning-session-complete"
        @click="openConfirmation('complete')"
      >
        {{ tr('learningSession.actions.complete') }}
      </button>
      <button
        type="button"
        class="secondary"
        :disabled="actionLoading.abandon || activeSession.status !== 'active'"
        data-testid="learning-session-abandon"
        @click="openConfirmation('abandon')"
      >
        {{ tr('learningSession.actions.abandon') }}
      </button>
    </div>

    <div
      v-if="summary"
      class="surface-muted summary-box"
      data-testid="learning-session-summary"
    >
      <strong>{{ tr('learningSession.summary.title') }}</strong>
      <p>
        {{
          tr('learningSession.summary.details', {
            status: tr(`learningSession.statuses.${summary.status}`),
            events: summary.total_event_count,
            duration: formatDuration(summary.duration_seconds ?? 0),
          })
        }}
      </p>
    </div>

    <div class="timeline">
      <div class="section-header compact">
        <div>
          <h3>{{ tr('learningSession.timeline.title') }}</h3>
          <p v-if="eventProgressText" class="section-description">
            {{ eventProgressText }}
          </p>
        </div>
      </div>
      <p
        v-if="!events.length"
        class="section-description"
        data-testid="learning-session-events-empty"
      >
        {{ tr('learningSession.timeline.empty') }}
      </p>
      <ol v-else data-testid="learning-session-events">
        <li
          v-for="event in events"
          :key="event.event_id"
          :data-testid="`learning-session-event-${event.event_id}`"
        >
          <span>{{
            tr(`learningSession.eventTypes.${event.event_type}`)
          }}</span>
          <small>{{ formatDateTime(event.occurred_at) }}</small>
          <em v-if="event.metadata?.note">{{ event.metadata.note }}</em>
        </li>
      </ol>
      <div v-if="eventsError" class="error-text">
        {{ eventsError }}
      </div>
      <button
        v-if="hasMoreEvents"
        type="button"
        class="secondary"
        :disabled="actionLoading.events"
        data-testid="learning-session-events-load-more"
        @click="loadMoreEvents"
      >
        {{
          actionLoading.events
            ? tr('learningSession.pagination.loadingMore')
            : tr('learningSession.pagination.loadMoreEvents')
        }}
      </button>
    </div>

    <div class="history">
      <div class="section-header compact">
        <div>
          <h3>{{ tr('learningSession.history.title') }}</h3>
        </div>
        <button
          type="button"
          class="secondary"
          :disabled="actionLoading.history"
          data-testid="learning-session-history-refresh"
          @click="refreshHistory"
        >
          {{ tr('common.refresh') }}
        </button>
      </div>
      <p
        v-if="!history.length"
        class="section-description"
        data-testid="learning-session-history-empty"
      >
        {{ tr('learningSession.history.empty') }}
      </p>
      <div v-else class="history-list" data-testid="learning-session-history">
        <button
          v-for="session in history"
          :key="session.session_id"
          type="button"
          class="history-item"
          :class="{ selected: session.session_id === selectedSessionId }"
          :data-testid="`learning-session-history-${session.session_id}`"
          @click="selectHistory(session.session_id)"
        >
          <span>
            {{
              tr('learningSession.history.item', {
                language: session.language,
                status: tr(`learningSession.statuses.${session.status}`),
              })
            }}
          </span>
          <small>{{ formatDateTime(session.started_at) }}</small>
        </button>
      </div>
      <div v-if="historyError" class="error-text">
        {{ historyError }}
      </div>
      <button
        v-if="hasMoreHistory"
        type="button"
        class="secondary"
        :disabled="actionLoading.history"
        data-testid="learning-session-history-load-more"
        @click="loadMoreHistory"
      >
        {{
          actionLoading.history
            ? tr('learningSession.pagination.loadingMore')
            : tr('learningSession.pagination.loadMoreSessions')
        }}
      </button>
    </div>

    <div class="weekly-review" data-testid="weekly-review">
      <div class="section-header compact">
        <div>
          <h3>{{ tr('learningSession.weeklyReview.title') }}</h3>
          <p v-if="weeklyInsight" class="section-description">
            {{
              tr('learningSession.weeklyReview.range', {
                start: formatDate(weeklyInsight.week_start),
                end: formatDate(weeklyInsight.week_end),
              })
            }}
          </p>
        </div>
        <button
          type="button"
          class="secondary"
          :disabled="actionLoading.goal"
          data-testid="learning-session-save-goal"
          @click="saveGoal"
        >
          {{
            actionLoading.goal
              ? tr('learningSession.weeklyGoal.saving')
              : tr('learningSession.weeklyGoal.save')
          }}
        </button>
      </div>

      <div v-if="goalDraft" class="goal-grid">
        <label>
          {{ tr('learningSession.weeklyGoal.dailyMinutes') }}
          <input
            :value="goalDraft.daily_minutes"
            type="number"
            min="1"
            max="480"
            :aria-label="tr('learningSession.weeklyGoal.dailyMinutes')"
            data-testid="learning-goal-daily-minutes"
            @input="updateGoalField('daily_minutes', $event)"
          />
        </label>
        <label>
          {{ tr('learningSession.weeklyGoal.weeklySessions') }}
          <input
            :value="goalDraft.weekly_sessions"
            type="number"
            min="1"
            max="28"
            :aria-label="tr('learningSession.weeklyGoal.weeklySessions')"
            data-testid="learning-goal-weekly-sessions"
            @input="updateGoalField('weekly_sessions', $event)"
          />
        </label>
        <label>
          {{ tr('learningSession.weeklyGoal.weeklyMinutes') }}
          <input
            :value="goalDraft.weekly_minutes ?? ''"
            type="number"
            min="1"
            max="3360"
            :aria-label="tr('learningSession.weeklyGoal.weeklyMinutes')"
            data-testid="learning-goal-weekly-minutes"
            @input="updateGoalField('weekly_minutes', $event)"
          />
        </label>
      </div>

      <div v-if="weeklyInsight" class="session-grid">
        <article class="stat-card">
          <p class="stat-label">
            {{ tr('learningSession.weeklyReview.completedSessions') }}
          </p>
          <p class="stat-value">{{ weeklyInsight.completed_session_count }}</p>
        </article>
        <article class="stat-card">
          <p class="stat-label">
            {{ tr('learningSession.weeklyReview.time') }}
          </p>
          <p class="stat-value">
            {{ formatDuration(weeklyInsight.total_completed_duration_seconds) }}
          </p>
        </article>
        <article class="stat-card">
          <p class="stat-label">
            {{ tr('learningSession.weeklyReview.activeDays') }}
          </p>
          <p class="stat-value">{{ weeklyInsight.active_learning_days }}</p>
        </article>
        <article class="stat-card">
          <p class="stat-label">
            {{ tr('learningSession.weeklyReview.review') }}
          </p>
          <p class="stat-value">
            {{
              weeklyInsight.review_correctness_rate == null
                ? tr('learningSession.weeklyReview.notAvailable')
                : tr('learningSession.weeklyReview.reviewRate', {
                    rate: weeklyInsight.review_correctness_rate.toFixed(0),
                  })
            }}
          </p>
        </article>
      </div>
    </div>

    <div
      v-if="confirmationDialog"
      class="dialog-backdrop"
      data-testid="learning-session-confirmation"
      @click.self="closeConfirmation"
    >
      <div
        class="dialog-panel"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`learning-session-confirm-title-${confirmationDialog.kind}`"
        :aria-describedby="`learning-session-confirm-body-${confirmationDialog.kind}`"
        @keydown="handleDialogKeydown"
      >
        <h3
          :id="`learning-session-confirm-title-${confirmationDialog.kind}`"
          :class="[
            'dialog-title',
            confirmationDialog.kind === 'abandon' ? 'danger' : 'success',
          ]"
        >
          {{ confirmationTitle }}
        </h3>
        <p :id="`learning-session-confirm-body-${confirmationDialog.kind}`">
          {{ confirmationMessage }}
        </p>
        <div v-if="confirmationError" class="error-text">
          {{ confirmationError }}
        </div>
        <div class="dialog-actions">
          <button
            ref="cancelButton"
            type="button"
            class="secondary"
            :disabled="confirmationBusy"
            data-testid="learning-session-confirm-cancel"
            @click="closeConfirmation"
          >
            {{ tr('common.cancel') }}
          </button>
          <button
            ref="confirmButton"
            type="button"
            :class="
              confirmationDialog.kind === 'abandon' ? 'danger-button' : ''
            "
            :disabled="confirmationBusy"
            data-testid="learning-session-confirm-accept"
            @click="confirmCurrentAction"
          >
            {{ confirmationActionLabel }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
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

type GoalDraft = {
  daily_minutes: number | ''
  weekly_sessions: number | ''
  weekly_minutes: number | null | ''
}

type ConfirmationKind = 'complete' | 'abandon'

const quickMinutes = [10, 20, 30]
const { t } = useI18n()
const language = ref<Language>('EN')
const plannedMinutes = ref(20)
const activeSession = ref<LearningSessionRecord | null>(null)
const selectedSessionId = ref<string | null>(null)
const events = ref<LearningSessionEventRecord[]>([])
const history = ref<LearningSessionRecord[]>([])
const summary = ref<LearningSessionSummary | null>(null)
const goal = ref<LearningGoal | null>(null)
const goalDraft = ref<GoalDraft | null>(null)
const weeklyInsight = ref<WeeklyLearningInsight | null>(null)
const noteText = ref('')
const pendingNoteOperation = ref<PendingNoteOperation | null>(null)
const nowMs = ref(Date.now())
const loading = ref(false)
const error = ref<string | null>(null)
const historyError = ref<string | null>(null)
const eventsError = ref<string | null>(null)
const confirmationError = ref<string | null>(null)
const historyCursor = ref<string | null>(null)
const hasMoreHistory = ref(false)
const eventCursor = ref<string | null>(null)
const hasMoreEvents = ref(false)
const confirmationDialog = ref<{
  kind: ConfirmationKind
  sessionId: string
} | null>(null)
const cancelButton = ref<HTMLButtonElement | null>(null)
const confirmButton = ref<HTMLButtonElement | null>(null)
const lastFocusedElement = ref<HTMLElement | null>(null)
const actionLoading = ref({
  note: false,
  complete: false,
  abandon: false,
  history: false,
  events: false,
  goal: false,
})

let timer: number | undefined
let reloadSequence = 0
let historySelectionSequence = 0

const tr = (key: string, values?: Record<string, unknown>) =>
  values ? t(key, values) : t(key)

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

const confirmationBusy = computed(() => {
  if (!confirmationDialog.value) return false
  return confirmationDialog.value.kind === 'complete'
    ? actionLoading.value.complete
    : actionLoading.value.abandon
})

const confirmationTitle = computed(() => {
  if (!confirmationDialog.value) return ''
  return tr(
    `learningSession.confirmation.${confirmationDialog.value.kind}.title`,
  )
})

const confirmationMessage = computed(() => {
  if (!confirmationDialog.value) return ''
  return tr(
    `learningSession.confirmation.${confirmationDialog.value.kind}.message`,
  )
})

const confirmationActionLabel = computed(() => {
  if (!confirmationDialog.value) return ''
  return tr(
    `learningSession.confirmation.${confirmationDialog.value.kind}.confirm`,
  )
})

const eventProgressText = computed(() => {
  if (summary.value) {
    return tr('learningSession.pagination.eventsLoaded', {
      loaded: events.value.length,
      total: summary.value.total_event_count,
    })
  }
  if (events.value.length > 0) {
    return tr('learningSession.pagination.eventsLoaded', {
      loaded: events.value.length,
      total: events.value.length,
    })
  }
  return ''
})

const setError = (fallbackKey: string, err: unknown) => {
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
  error.value = tr(fallbackKey)
}

const setScopedError = (
  target: typeof historyError | typeof eventsError | typeof confirmationError,
  fallbackKey: string,
  err: unknown,
) => {
  if (err && typeof err === 'object' && 'response' in err) {
    const response = (err as { response?: { data?: unknown } }).response
    const data = response?.data
    if (data && typeof data === 'object' && 'message' in data) {
      const message = (data as { message?: unknown }).message
      if (typeof message === 'string' && message.trim()) {
        target.value = message
        return
      }
    }
  }
  target.value = tr(fallbackKey)
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

const mergeUniqueSessions = (
  existing: LearningSessionRecord[],
  incoming: LearningSessionRecord[],
) => {
  const byId = new Map(existing.map((session) => [session.session_id, session]))
  for (const session of incoming) {
    byId.set(session.session_id, session)
  }
  return [...byId.values()].sort((left, right) => {
    const startedDelta =
      new Date(right.started_at).getTime() - new Date(left.started_at).getTime()
    if (startedDelta !== 0) return startedDelta
    return right.session_id.localeCompare(left.session_id)
  })
}

const mergeCanonicalEvent = (event: LearningSessionEventRecord) => {
  const idempotencyKey =
    typeof event.metadata?.idempotency_key === 'string'
      ? event.metadata.idempotency_key
      : null
  const withoutDuplicate = events.value.filter((existing) => {
    if (existing.event_id === event.event_id) return false
    if (
      idempotencyKey &&
      typeof existing.metadata?.idempotency_key === 'string' &&
      existing.metadata.idempotency_key === idempotencyKey
    ) {
      return false
    }
    return true
  })
  events.value = [...withoutDuplicate, event].sort(
    (a, b) => a.sequence_number - b.sequence_number,
  )
}

const mergeUniqueEvents = (
  existing: LearningSessionEventRecord[],
  incoming: LearningSessionEventRecord[],
) => {
  const byId = new Map(existing.map((event) => [event.event_id, event]))
  for (const event of incoming) {
    byId.set(event.event_id, event)
  }
  return [...byId.values()].sort(
    (left, right) => left.sequence_number - right.sequence_number,
  )
}

const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}:${rest.toString().padStart(2, '0')}`
}

const formatDateTime = (value: string) => new Date(value).toLocaleString()
const formatDate = (value: string) => new Date(value).toLocaleDateString()

const buildGoalDraft = (value: LearningGoal): GoalDraft => ({
  daily_minutes: value.daily_minutes,
  weekly_sessions: value.weekly_sessions,
  weekly_minutes: value.weekly_minutes ?? null,
})

const loadEventsPage = async (sessionId: string, cursor?: string | null) =>
  learningSessionApi.listEvents(sessionId, 50, cursor)

const loadHistoryPage = async (
  selectedLanguage = language.value,
  cursor?: string | null,
) => learningSessionApi.list(selectedLanguage, 10, cursor)

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

const resetHistoryState = () => {
  history.value = []
  historyCursor.value = null
  hasMoreHistory.value = false
  historyError.value = null
}

const resetEventState = () => {
  events.value = []
  eventCursor.value = null
  hasMoreEvents.value = false
  eventsError.value = null
}

const assignHistoryPage = (
  page: Awaited<ReturnType<typeof loadHistoryPage>>,
  append: boolean,
) => {
  history.value = append
    ? mergeUniqueSessions(history.value, page.sessions)
    : page.sessions
  historyCursor.value = page.next_cursor ?? null
  hasMoreHistory.value = page.has_more
}

const assignEventPage = (
  page: Awaited<ReturnType<typeof loadEventsPage>>,
  append: boolean,
) => {
  events.value = append
    ? mergeUniqueEvents(events.value, page.events)
    : page.events
  eventCursor.value = page.next_cursor ?? null
  hasMoreEvents.value = page.has_more
}

const refreshHistory = async () => {
  if (actionLoading.value.history) return
  actionLoading.value.history = true
  historyError.value = null
  try {
    const page = await loadHistoryPage(language.value)
    assignHistoryPage(page, false)
  } catch (err) {
    setScopedError(historyError, 'learningSession.history.errors.refresh', err)
  } finally {
    actionLoading.value.history = false
  }
}

const loadMoreHistory = async () => {
  if (
    actionLoading.value.history ||
    !hasMoreHistory.value ||
    !historyCursor.value
  ) {
    return
  }
  actionLoading.value.history = true
  historyError.value = null
  const cursor = historyCursor.value
  const selectedLanguage = language.value
  try {
    const page = await loadHistoryPage(selectedLanguage, cursor)
    if (selectedLanguage !== language.value) return
    assignHistoryPage(page, true)
  } catch (err) {
    setScopedError(historyError, 'learningSession.history.errors.retry', err)
  } finally {
    actionLoading.value.history = false
  }
}

const loadMoreEvents = async () => {
  if (
    actionLoading.value.events ||
    !selectedSessionId.value ||
    !hasMoreEvents.value ||
    !eventCursor.value
  ) {
    return
  }
  actionLoading.value.events = true
  eventsError.value = null
  const sessionId = selectedSessionId.value
  const cursor = eventCursor.value
  try {
    const page = await loadEventsPage(sessionId, cursor)
    if (sessionId !== selectedSessionId.value) return
    assignEventPage(page, true)
  } catch (err) {
    setScopedError(eventsError, 'learningSession.timeline.errors.retry', err)
  } finally {
    actionLoading.value.events = false
  }
}

const reload = async () => {
  const requestId = ++reloadSequence
  const selectedLanguage = language.value
  loading.value = true
  error.value = null
  summary.value = null
  confirmationError.value = null
  selectedSessionId.value = null
  resetHistoryState()
  resetEventState()
  try {
    const active = await learningSessionApi.getActive(selectedLanguage)
    if (requestId !== reloadSequence || selectedLanguage !== language.value) {
      return
    }
    const activeId =
      active.session?.status === 'active' ? active.session.session_id : null
    const [historyPage, goalAndInsight, eventsPage] = await Promise.all([
      loadHistoryPage(selectedLanguage),
      loadGoalAndInsight(selectedLanguage),
      activeId ? loadEventsPage(activeId) : Promise.resolve(null),
    ])
    if (requestId !== reloadSequence || selectedLanguage !== language.value) {
      return
    }
    activeSession.value =
      active.session?.status === 'active' ? active.session : null
    selectedSessionId.value = activeId
    assignHistoryPage(historyPage, false)
    if (eventsPage) {
      assignEventPage(eventsPage, false)
    }
    goal.value = goalAndInsight.goal
    goalDraft.value = buildGoalDraft(goalAndInsight.goal)
    weeklyInsight.value = goalAndInsight.insight
  } catch (err) {
    setError('learningSession.errors.load', err)
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
    error.value = tr('learningSession.errors.invalidPlannedMinutes')
    return
  }
  loading.value = true
  error.value = null
  const selectedLanguage = language.value
  try {
    const started = await learningSessionApi.start(
      selectedLanguage,
      plannedMinutes.value,
    )
    if (selectedLanguage !== language.value) return
    activeSession.value = started.session
    selectedSessionId.value = started.session.session_id
    summary.value = null
    const [eventsPage, historyPage] = await Promise.all([
      loadEventsPage(started.session.session_id),
      loadHistoryPage(selectedLanguage),
    ])
    if (selectedLanguage !== language.value) return
    assignEventPage(eventsPage, false)
    assignHistoryPage(historyPage, false)
  } catch (err) {
    setError('learningSession.errors.start', err)
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
    setError('learningSession.errors.note', err)
  } finally {
    actionLoading.value.note = false
  }
}

const openConfirmation = (kind: ConfirmationKind) => {
  if (!activeSession.value || activeSession.value.status !== 'active') return
  lastFocusedElement.value = document.activeElement as HTMLElement | null
  confirmationError.value = null
  confirmationDialog.value = {
    kind,
    sessionId: activeSession.value.session_id,
  }
  void nextTick(() => {
    cancelButton.value?.focus()
  })
}

const closeConfirmation = () => {
  if (confirmationBusy.value) return
  confirmationDialog.value = null
  confirmationError.value = null
  void nextTick(() => {
    lastFocusedElement.value?.focus()
  })
}

const finishSession = async (kind: ConfirmationKind, sessionId: string) => {
  summary.value = null
  eventsError.value = null
  historyError.value = null
  error.value = null
  try {
    const sessionResponse =
      kind === 'complete'
        ? await learningSessionApi.complete(
            sessionId,
            clientKey('complete', sessionId),
          )
        : await learningSessionApi.abandon(sessionId)
    const [sessionSummary, eventsPage, historyPage, goalAndInsight] =
      await Promise.all([
        learningSessionApi.summary(sessionId),
        loadEventsPage(sessionId),
        loadHistoryPage(language.value),
        loadGoalAndInsight(language.value),
      ])
    activeSession.value = null
    selectedSessionId.value = sessionId
    summary.value = sessionSummary.summary
    assignEventPage(eventsPage, false)
    assignHistoryPage(historyPage, false)
    goal.value = goalAndInsight.goal
    goalDraft.value = buildGoalDraft(goalAndInsight.goal)
    weeklyInsight.value = goalAndInsight.insight
    if (kind === 'complete') {
      actionLoading.value.complete = false
    } else {
      actionLoading.value.abandon = false
    }
    confirmationDialog.value = null
    confirmationError.value = null
    lastFocusedElement.value?.focus()
    return sessionResponse.session
  } catch (err) {
    setScopedError(
      confirmationError,
      kind === 'complete'
        ? 'learningSession.errors.complete'
        : 'learningSession.errors.abandon',
      err,
    )
    throw err
  }
}

const confirmCurrentAction = async () => {
  if (!confirmationDialog.value || confirmationBusy.value) return
  const { kind, sessionId } = confirmationDialog.value
  if (kind === 'complete') {
    actionLoading.value.complete = true
  } else {
    actionLoading.value.abandon = true
  }
  try {
    await finishSession(kind, sessionId)
  } catch {
    // Error is surfaced in the dialog for retry.
  } finally {
    if (kind === 'complete') {
      actionLoading.value.complete = false
    } else {
      actionLoading.value.abandon = false
    }
  }
}

const handleDialogKeydown = (event: KeyboardEvent) => {
  if (!confirmationDialog.value) return
  if (event.key === 'Escape') {
    event.preventDefault()
    closeConfirmation()
    return
  }
  if (event.key !== 'Tab') return

  const focusable = [cancelButton.value, confirmButton.value].filter(
    (element): element is HTMLButtonElement => element !== null,
  )
  if (focusable.length === 0) return
  const currentIndex = focusable.findIndex(
    (element) => element === document.activeElement,
  )
  const nextIndex = event.shiftKey
    ? currentIndex <= 0
      ? focusable.length - 1
      : currentIndex - 1
    : currentIndex === focusable.length - 1
      ? 0
      : currentIndex + 1
  event.preventDefault()
  focusable[nextIndex]?.focus()
}

const selectHistory = async (sessionId: string) => {
  const requestId = ++historySelectionSequence
  actionLoading.value.history = true
  error.value = null
  eventsError.value = null
  historyError.value = null
  selectedSessionId.value = sessionId
  resetEventState()
  try {
    const [selectedSummary, eventsPage] = await Promise.all([
      learningSessionApi.summary(sessionId),
      loadEventsPage(sessionId),
    ])
    if (
      requestId !== historySelectionSequence ||
      selectedSessionId.value !== sessionId
    ) {
      return
    }
    summary.value = selectedSummary.summary
    assignEventPage(eventsPage, false)
  } catch (err) {
    setError('learningSession.history.errors.summary', err)
  } finally {
    if (requestId === historySelectionSequence) {
      actionLoading.value.history = false
    }
  }
}

const updateGoalField = (field: keyof GoalDraft, event: Event) => {
  if (!goalDraft.value) return
  const nextValue = (event.target as HTMLInputElement).value
  if (nextValue === '') {
    goalDraft.value = {
      ...goalDraft.value,
      [field]: '',
    }
    return
  }
  const parsed = Number(nextValue)
  goalDraft.value = {
    ...goalDraft.value,
    [field]: Number.isFinite(parsed) ? parsed : nextValue,
  }
}

const normalizeGoalPayload = (draft: GoalDraft) => {
  const normalizeRequiredInteger = (
    value: number | '',
    min: number,
    max: number,
  ) => {
    if (
      value === '' ||
      !Number.isInteger(value) ||
      value < min ||
      value > max
    ) {
      return null
    }
    return value
  }

  const dailyMinutes = normalizeRequiredInteger(draft.daily_minutes, 1, 480)
  const weeklySessions = normalizeRequiredInteger(draft.weekly_sessions, 1, 28)
  if (dailyMinutes == null || weeklySessions == null) {
    return null
  }

  if (draft.weekly_minutes === '' || draft.weekly_minutes === null) {
    return {
      daily_minutes: dailyMinutes,
      weekly_sessions: weeklySessions,
      weekly_minutes: null,
    }
  }
  if (
    !Number.isInteger(draft.weekly_minutes) ||
    draft.weekly_minutes < 1 ||
    draft.weekly_minutes > 3360
  ) {
    return null
  }
  return {
    daily_minutes: dailyMinutes,
    weekly_sessions: weeklySessions,
    weekly_minutes: draft.weekly_minutes,
  }
}

const saveGoal = async () => {
  if (!goalDraft.value || actionLoading.value.goal) return
  const payload = normalizeGoalPayload(goalDraft.value)
  if (!payload) {
    error.value = tr('learningSession.weeklyGoal.invalid')
    return
  }
  const selectedLanguage = language.value
  actionLoading.value.goal = true
  error.value = null
  try {
    const saved = await learningGoalApi.update(selectedLanguage, payload)
    if (selectedLanguage !== language.value) return
    goal.value = saved.goal
    goalDraft.value = buildGoalDraft(saved.goal)
    weeklyInsight.value = (
      await learningGoalApi.weeklyInsight(selectedLanguage)
    ).insight
  } catch (err) {
    setError('learningSession.weeklyGoal.errors.save', err)
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

.history-item.selected {
  border-color: #1d4ed8;
  background: #eff6ff;
}

.summary-box {
  padding: 12px;
}

.compact {
  margin-bottom: 0;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgb(15 23 42 / 45%);
}

.dialog-panel {
  width: min(100%, 420px);
  padding: 20px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 25px 50px -12px rgb(15 23 42 / 35%);
}

.dialog-title {
  margin: 0 0 8px;
}

.dialog-title.success {
  color: #166534;
}

.dialog-title.danger {
  color: #b91c1c;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

.danger-button {
  background: #b91c1c;
  border-color: #b91c1c;
  color: #fff;
}
</style>
