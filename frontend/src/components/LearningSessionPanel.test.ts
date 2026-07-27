import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import i18n from '@/i18n'
import LearningSessionPanel from '@/components/LearningSessionPanel.vue'

const apiMocks = vi.hoisted(() => ({
  getActive: vi.fn(),
  start: vi.fn(),
  list: vi.fn(),
  listEvents: vi.fn(),
  addNote: vi.fn(),
  complete: vi.fn(),
  abandon: vi.fn(),
  summary: vi.fn(),
  getGoal: vi.fn(),
  updateGoal: vi.fn(),
  weeklyInsight: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  learningSessionApi: {
    getActive: apiMocks.getActive,
    start: apiMocks.start,
    list: apiMocks.list,
    listEvents: apiMocks.listEvents,
    addNote: apiMocks.addNote,
    complete: apiMocks.complete,
    abandon: apiMocks.abandon,
    summary: apiMocks.summary,
  },
  learningGoalApi: {
    get: apiMocks.getGoal,
    update: apiMocks.updateGoal,
    weeklyInsight: apiMocks.weeklyInsight,
  },
}))

const flushPromises = async () => {
  for (let index = 0; index < 5; index += 1) {
    await Promise.resolve()
  }
  await nextTick()
}

const activeSession = {
  session_id: 'session-en',
  language: 'EN',
  status: 'active',
  planned_minutes: 20,
  started_at: '2026-07-24T08:00:00.000Z',
  ended_at: null,
  duration_seconds: null,
  created_at: '2026-07-24T08:00:00.000Z',
  updated_at: '2026-07-24T08:00:00.000Z',
}

const goal = {
  language: 'EN',
  daily_minutes: 20,
  weekly_sessions: 4,
  weekly_minutes: 120,
  created_at: '2026-07-20T00:00:00.000Z',
  updated_at: '2026-07-20T00:00:00.000Z',
}

const insight = {
  week_start: '2026-07-20T00:00:00.000Z',
  week_end: '2026-07-27T00:00:00.000Z',
  language: 'EN',
  completed_session_count: 0,
  abandoned_session_count: 0,
  total_completed_duration_seconds: 0,
  active_learning_days: 0,
  average_completed_session_duration_seconds: null,
  daily_minute_goal_progress: 0,
  weekly_session_goal_progress: 0,
  weekly_minute_goal_progress: 0,
  event_counts_by_type: {
    lesson_started: 0,
    lesson_completed: 0,
    review_answered: 0,
    srs_reviewed: 0,
    chat_turn_completed: 0,
    feynman_completed: 0,
    micro_lesson_completed: 0,
    session_note: 0,
  },
  lesson_completion_count: 0,
  review_answer_count: 0,
  correct_review_answer_count: 0,
  review_correctness_rate: null,
  srs_review_count: 0,
  chat_turn_count: 0,
  feynman_completion_count: 0,
  micro_lesson_completion_count: 0,
  most_active_day: null,
  recent_completed_sessions: [],
  goal,
}

const noteEvent = {
  event_id: 'event-note-1',
  session_id: 'session-en',
  event_type: 'session_note',
  entity_type: null,
  entity_id: null,
  sequence_number: 1,
  metadata: { note: 'hello' },
  occurred_at: '2026-07-24T08:01:00.000Z',
  created_at: '2026-07-24T08:01:00.000Z',
}

const noteEventPage = {
  success: true,
  events: [noteEvent],
  limit: 50,
  has_more: false,
  next_cursor: null,
}

const completedSession = {
  ...activeSession,
  status: 'completed',
  ended_at: '2026-07-24T08:25:00.000Z',
  duration_seconds: 1500,
}

const abandonedSession = {
  ...activeSession,
  status: 'abandoned',
  ended_at: '2026-07-24T08:15:00.000Z',
  duration_seconds: 900,
}

const completedSummary = {
  session_id: 'session-en',
  language: 'EN',
  status: 'completed',
  started_at: '2026-07-24T08:00:00.000Z',
  ended_at: '2026-07-24T08:25:00.000Z',
  duration_seconds: 1500,
  planned_minutes: 20,
  total_event_count: 1,
  counts_by_event_type: {
    lesson_started: 0,
    lesson_completed: 0,
    review_answered: 0,
    srs_reviewed: 0,
    chat_turn_completed: 0,
    feynman_completed: 0,
    micro_lesson_completed: 0,
    session_note: 1,
  },
  lesson_completion_count: 0,
  review_answer_count: 0,
  srs_review_count: 0,
  chat_turn_count: 0,
  feynman_completion_count: 0,
  micro_lesson_completion_count: 0,
  first_event_at: '2026-07-24T08:01:00.000Z',
  last_event_at: '2026-07-24T08:01:00.000Z',
  planned_duration_goal_reached: true,
  correct_event_count: null,
}

const abandonedSummary = {
  ...completedSummary,
  status: 'abandoned',
  ended_at: '2026-07-24T08:15:00.000Z',
  duration_seconds: 900,
}

const historyPage = {
  success: true,
  sessions: [],
  limit: 10,
  has_more: false,
  next_cursor: null,
}

function defaultApiState(session: unknown = activeSession) {
  apiMocks.getActive.mockResolvedValue({ success: true, session })
  apiMocks.listEvents.mockResolvedValue({
    success: true,
    events: [],
    limit: 50,
    has_more: false,
    next_cursor: null,
  })
  apiMocks.list.mockResolvedValue(historyPage)
  apiMocks.getGoal.mockResolvedValue({ success: true, goal })
  apiMocks.weeklyInsight.mockResolvedValue({ success: true, insight })
  apiMocks.addNote.mockResolvedValue({ success: true, event: noteEvent })
}

async function mountReady(session: unknown = activeSession) {
  defaultApiState(session)
  const wrapper = mount(LearningSessionPanel, {
    global: {
      plugins: [i18n],
    },
  })
  await flushPromises()
  return wrapper
}

function byTestId(wrapper: ReturnType<typeof mount>, testId: string) {
  return wrapper.find(`[data-testid="${testId}"]`)
}

function findButton(wrapper: ReturnType<typeof mount>, text: string) {
  const button = wrapper
    .findAll('button')
    .find((candidate) => candidate.text() === text)
  if (!button) throw new Error(`Missing button: ${text}`)
  return button
}

describe('LearningSessionPanel.vue', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-24T08:05:00.000Z'))
    window.localStorage.clear()
    i18n.global.locale.value = 'en'
    vi.stubGlobal('crypto', {
      randomUUID: vi
        .fn()
        .mockReturnValueOnce('11111111-1111-4111-8111-111111111111')
        .mockReturnValueOnce('22222222-2222-4222-8222-222222222222')
        .mockReturnValueOnce('33333333-3333-4333-8333-333333333333')
        .mockReturnValueOnce('44444444-4444-4444-8444-444444444444'),
    })
    apiMocks.getActive.mockReset()
    apiMocks.start.mockReset()
    apiMocks.list.mockReset()
    apiMocks.listEvents.mockReset()
    apiMocks.addNote.mockReset()
    apiMocks.complete.mockReset()
    apiMocks.abandon.mockReset()
    apiMocks.summary.mockReset()
    apiMocks.getGoal.mockReset()
    apiMocks.updateGoal.mockReset()
    apiMocks.weeklyInsight.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('derives the timer from server started_at and loads goals and weekly insight', async () => {
    const wrapper = await mountReady()

    expect(wrapper.text()).toContain('5:00')
    expect(wrapper.text()).toContain('Weekly Review')
    expect(apiMocks.getGoal).toHaveBeenCalledWith('EN')
    expect(apiMocks.weeklyInsight).toHaveBeenCalledWith('EN')

    vi.advanceTimersByTime(2000)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('5:02')
  })

  it('starts an English session with a planned preset and blocks duplicate creation while loading', async () => {
    defaultApiState(null)
    const resolveStart = vi.fn()
    apiMocks.start.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveStart.mockImplementation(resolve)
      }),
    )
    const wrapper = mount(LearningSessionPanel, {
      global: {
        plugins: [i18n],
      },
    })
    await flushPromises()

    await findButton(wrapper, '10 min').trigger('click')
    await findButton(wrapper, 'Start').trigger('click')
    await findButton(wrapper, 'Start').trigger('click')

    expect(apiMocks.start).toHaveBeenCalledTimes(1)
    expect(apiMocks.start).toHaveBeenCalledWith('EN', 10)

    resolveStart({ success: true, session: activeSession })
    await flushPromises()
    expect(wrapper.text()).toContain('EN')
  })

  it('starts a Japanese session after switching languages', async () => {
    defaultApiState(null)
    apiMocks.getActive.mockResolvedValueOnce({ success: true, session: null })
    apiMocks.getActive.mockResolvedValueOnce({ success: true, session: null })
    apiMocks.start.mockResolvedValueOnce({
      success: true,
      session: { ...activeSession, session_id: 'session-jp', language: 'JP' },
    })
    const wrapper = mount(LearningSessionPanel, {
      global: {
        plugins: [i18n],
      },
    })
    await flushPromises()

    await wrapper.find('select').setValue('JP')
    await flushPromises()
    await findButton(wrapper, 'Start').trigger('click')
    await flushPromises()

    expect(apiMocks.start).toHaveBeenCalledWith('JP', 20)
    expect(wrapper.text()).toContain('JP')
  })

  it('shows a validation error for invalid custom duration', async () => {
    const wrapper = await mountReady(null)

    await wrapper.find('input[type="number"]').setValue(0)
    await findButton(wrapper, 'Start').trigger('click')

    expect(apiMocks.start).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain(
      'Planned minutes must be between 1 and 480.',
    )
  })

  it.each([1, 49, 500])(
    'uses a bounded operation id for a %i-character manual note',
    async (length) => {
      const wrapper = await mountReady()
      const note = 'x'.repeat(length)

      await byTestId(wrapper, 'learning-session-note-input').setValue(note)
      await byTestId(wrapper, 'learning-session-add-note').trigger('click')
      await flushPromises()

      expect(apiMocks.addNote).toHaveBeenCalledWith(
        'session-en',
        note,
        'session-note:note-11111111-1111-4111-8111-111111111111',
      )
      expect(apiMocks.addNote.mock.calls[0][2]).toHaveLength(54)
    },
  )

  it('reuses the same pending note operation id after a timeout retry', async () => {
    const wrapper = await mountReady()
    apiMocks.addNote
      .mockRejectedValueOnce(new Error('timeout'))
      .mockResolvedValueOnce({ success: true, event: noteEvent })

    await byTestId(wrapper, 'learning-session-note-input').setValue('retry me')
    await byTestId(wrapper, 'learning-session-add-note').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-add-note').trigger('click')
    await flushPromises()

    expect(apiMocks.addNote).toHaveBeenCalledTimes(2)
    expect(apiMocks.addNote.mock.calls[0][2]).toBe(
      apiMocks.addNote.mock.calls[1][2],
    )
  })

  it('creates a new note operation when edited text is submitted after a timeout', async () => {
    const wrapper = await mountReady()
    apiMocks.addNote
      .mockRejectedValueOnce(new Error('timeout'))
      .mockResolvedValueOnce({
        success: true,
        event: { ...noteEvent, metadata: { note: 'edited note' } },
      })

    await byTestId(wrapper, 'learning-session-note-input').setValue(
      'first note',
    )
    await byTestId(wrapper, 'learning-session-add-note').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-note-input').setValue(
      'edited note',
    )
    await byTestId(wrapper, 'learning-session-add-note').trigger('click')
    await flushPromises()

    expect(apiMocks.addNote).toHaveBeenCalledTimes(2)
    expect(apiMocks.addNote.mock.calls[0][1]).toBe('first note')
    expect(apiMocks.addNote.mock.calls[1][1]).toBe('edited note')
    expect(apiMocks.addNote.mock.calls[0][2]).not.toBe(
      apiMocks.addNote.mock.calls[1][2],
    )
  })

  it('creates a new note operation when the active session changes after a timeout', async () => {
    const wrapper = await mountReady()
    apiMocks.addNote
      .mockRejectedValueOnce(new Error('timeout'))
      .mockResolvedValueOnce({
        success: true,
        event: {
          ...noteEvent,
          event_id: 'event-note-jp',
          session_id: 'session-jp',
        },
      })
    apiMocks.getActive.mockResolvedValueOnce({
      success: true,
      session: { ...activeSession, session_id: 'session-jp', language: 'JP' },
    })
    apiMocks.getGoal.mockResolvedValue({
      success: true,
      goal: { ...goal, language: 'JP' },
    })
    apiMocks.weeklyInsight.mockResolvedValue({
      success: true,
      insight: { ...insight, language: 'JP' },
    })

    await byTestId(wrapper, 'learning-session-note-input').setValue('same note')
    await byTestId(wrapper, 'learning-session-add-note').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-language').setValue('JP')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-note-input').setValue('same note')
    await byTestId(wrapper, 'learning-session-add-note').trigger('click')
    await flushPromises()

    expect(apiMocks.addNote).toHaveBeenCalledTimes(2)
    expect(apiMocks.addNote.mock.calls[0][0]).toBe('session-en')
    expect(apiMocks.addNote.mock.calls[1][0]).toBe('session-jp')
    expect(apiMocks.addNote.mock.calls[0][2]).not.toBe(
      apiMocks.addNote.mock.calls[1][2],
    )
  })

  it('creates separate operation ids for intentional identical notes and de-duplicates canonical events', async () => {
    const wrapper = await mountReady()
    apiMocks.addNote.mockResolvedValue({
      success: true,
      event: {
        ...noteEvent,
        metadata: {
          ...noteEvent.metadata,
          idempotency_key: 'session-note:duplicate-key',
        },
      },
    })

    await byTestId(wrapper, 'learning-session-note-input').setValue('same')
    await byTestId(wrapper, 'learning-session-add-note').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-note-input').setValue('same')
    await byTestId(wrapper, 'learning-session-add-note').trigger('click')
    await flushPromises()

    expect(apiMocks.addNote.mock.calls[0][2]).not.toBe(
      apiMocks.addNote.mock.calls[1][2],
    )
    expect(
      wrapper.findAll('[data-testid^="learning-session-event-"]'),
    ).toHaveLength(1)
  })

  it('rejects notes when the visible session is already finalized', async () => {
    const wrapper = await mountReady({ ...activeSession, status: 'completed' })

    expect(byTestId(wrapper, 'learning-session-note-input').exists()).toBe(false)
    expect(byTestId(wrapper, 'learning-session-add-note').exists()).toBe(false)
    expect(apiMocks.addNote).not.toHaveBeenCalled()
  })

  it('clears the active session after abandon but keeps summary and history available', async () => {
    const wrapper = await mountReady()
    apiMocks.abandon.mockResolvedValueOnce({
      success: true,
      session: abandonedSession,
    })
    apiMocks.summary.mockResolvedValueOnce({
      success: true,
      summary: abandonedSummary,
    })
    apiMocks.listEvents.mockResolvedValueOnce(noteEventPage)
    apiMocks.list.mockResolvedValueOnce({
      ...historyPage,
      sessions: [abandonedSession],
    })

    await byTestId(wrapper, 'learning-session-abandon').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-confirm-accept').trigger('click')
    await flushPromises()
    await flushPromises()

    expect(apiMocks.abandon).toHaveBeenCalledWith('session-en')
    expect(wrapper.text()).not.toContain('Elapsed')
    expect(wrapper.text()).toContain('Summary')
    expect(wrapper.text()).toContain('Abandoned')
    expect(
      wrapper.find('[data-testid="learning-session-start"]').exists(),
    ).toBe(true)
  })

  it('does not clear the active session when abandon fails', async () => {
    const wrapper = await mountReady()
    apiMocks.abandon.mockRejectedValueOnce(new Error('boom'))

    await byTestId(wrapper, 'learning-session-abandon').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-confirm-accept').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Active')
    expect(apiMocks.summary).not.toHaveBeenCalled()
  })

  it('reuses the stable completion idempotency key after a timeout retry', async () => {
    const wrapper = await mountReady()
    apiMocks.complete
      .mockRejectedValueOnce(new Error('timeout'))
      .mockResolvedValueOnce({ success: true, session: completedSession })
    apiMocks.summary.mockResolvedValue({
      success: true,
      summary: completedSummary,
    })
    apiMocks.listEvents.mockResolvedValue(noteEventPage)
    apiMocks.list.mockResolvedValue({
      ...historyPage,
      sessions: [completedSession],
    })

    await byTestId(wrapper, 'learning-session-complete').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-confirm-accept').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-confirm-accept').trigger('click')
    await flushPromises()

    expect(apiMocks.complete).toHaveBeenCalledTimes(2)
    expect(apiMocks.complete.mock.calls[0][1]).toBe(
      apiMocks.complete.mock.calls[1][1],
    )
    expect(wrapper.text()).toContain('Completed')
    expect(wrapper.text()).toContain('25:00')
  })

  it('loads additional history pages and resets when language changes', async () => {
    const wrapper = await mountReady()
    apiMocks.list
      .mockResolvedValueOnce({
        ...historyPage,
        sessions: [completedSession],
        has_more: true,
        next_cursor: 'cursor-2',
      })
      .mockResolvedValueOnce({
        ...historyPage,
        sessions: [{ ...completedSession, session_id: 'session-en-2' }],
      })

    await byTestId(wrapper, 'learning-session-history-refresh').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-history-load-more').trigger(
      'click',
    )
    await flushPromises()

    expect(apiMocks.list).toHaveBeenLastCalledWith('EN', 10, 'cursor-2')
    expect(wrapper.findAll('.history-item')).toHaveLength(2)

    apiMocks.getActive.mockResolvedValueOnce({
      success: true,
      session: { ...activeSession, session_id: 'session-jp', language: 'JP' },
    })
    apiMocks.getGoal.mockResolvedValueOnce({
      success: true,
      goal: { ...goal, language: 'JP' },
    })
    apiMocks.weeklyInsight.mockResolvedValueOnce({
      success: true,
      insight: { ...insight, language: 'JP' },
    })
    apiMocks.list.mockResolvedValueOnce({
      ...historyPage,
      sessions: [],
    })
    apiMocks.listEvents.mockResolvedValueOnce({
      success: true,
      events: [],
      limit: 50,
      has_more: false,
      next_cursor: null,
    })

    await byTestId(wrapper, 'learning-session-language').setValue('JP')
    await flushPromises()

    expect(apiMocks.list).toHaveBeenLastCalledWith('JP', 10, undefined)
    expect(
      byTestId(wrapper, 'learning-session-history-load-more').exists(),
    ).toBe(false)
  })

  it('loads additional event pages without duplicating records', async () => {
    const wrapper = await mountReady()
    apiMocks.summary.mockResolvedValueOnce({
      success: true,
      summary: { ...completedSummary, total_event_count: 3 },
    })
    apiMocks.listEvents
      .mockResolvedValueOnce({
        success: true,
        events: [noteEvent],
        limit: 50,
        has_more: true,
        next_cursor: '1',
      })
      .mockResolvedValueOnce({
        success: true,
        events: [
          noteEvent,
          {
            ...noteEvent,
            event_id: 'event-note-2',
            sequence_number: 2,
            metadata: { note: 'next' },
          },
        ],
        limit: 50,
        has_more: false,
        next_cursor: null,
      })

    apiMocks.list.mockResolvedValueOnce({
      ...historyPage,
      sessions: [completedSession],
    })

    await byTestId(wrapper, 'learning-session-history-refresh').trigger('click')
    await flushPromises()
    await byTestId(wrapper, 'learning-session-history-session-en').trigger(
      'click',
    )
    await flushPromises()
    await byTestId(wrapper, 'learning-session-events-load-more').trigger(
      'click',
    )
    await flushPromises()

    expect(
      wrapper.findAll('[data-testid^="learning-session-event-"]'),
    ).toHaveLength(2)
    expect(wrapper.text()).toContain('Loaded 2 of 3 events')
  })

  it('does not let a slow previous-language reload overwrite the current language', async () => {
    let resolveEnglish: (() => void) | undefined
    apiMocks.getActive
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveEnglish = () =>
            resolve({ success: true, session: activeSession })
        }),
      )
      .mockResolvedValueOnce({
        success: true,
        session: { ...activeSession, session_id: 'session-jp', language: 'JP' },
      })
    apiMocks.listEvents.mockResolvedValue({
      success: true,
      events: [],
      limit: 50,
      has_more: false,
      next_cursor: null,
    })
    apiMocks.list.mockResolvedValue({
      success: true,
      sessions: [],
      limit: 10,
      has_more: false,
      next_cursor: null,
    })
    apiMocks.getGoal.mockResolvedValue({
      success: true,
      goal: { ...goal, language: 'JP' },
    })
    apiMocks.weeklyInsight.mockResolvedValue({
      success: true,
      insight: { ...insight, language: 'JP' },
    })

    const wrapper = mount(LearningSessionPanel, {
      global: {
        plugins: [i18n],
      },
    })
    await byTestId(wrapper, 'learning-session-language').setValue('JP')
    resolveEnglish?.()
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('JP')
  })

  it('normalizes cleared weekly minutes to null before saving', async () => {
    const wrapper = await mountReady()
    apiMocks.updateGoal.mockResolvedValueOnce({
      success: true,
      goal: { ...goal, weekly_minutes: null },
    })
    apiMocks.weeklyInsight.mockResolvedValueOnce({
      success: true,
      insight: { ...insight, goal: { ...goal, weekly_minutes: null } },
    })

    await byTestId(wrapper, 'learning-goal-weekly-minutes').setValue('')
    await byTestId(wrapper, 'learning-session-save-goal').trigger('click')
    await flushPromises()

    expect(apiMocks.updateGoal).toHaveBeenCalledWith('EN', {
      daily_minutes: 20,
      weekly_sessions: 4,
      weekly_minutes: null,
    })
  })

  it('validates goals locally and preserves canonical values after server validation failure', async () => {
    const wrapper = await mountReady()
    const inputs = wrapper.findAll('.goal-grid input')

    await inputs[0].setValue(481)
    await findButton(wrapper, 'Save goals').trigger('click')

    expect(apiMocks.updateGoal).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain(
      'Goal values are outside the supported range.',
    )

    await inputs[0].setValue(30)
    apiMocks.updateGoal.mockRejectedValueOnce({
      response: {
        data: {
          message: 'daily_minutes must be between 1 and 480',
          code: 'invalid_goal_value',
        },
      },
    })
    await findButton(wrapper, 'Save goals').trigger('click')
    await flushPromises()

    expect(apiMocks.updateGoal).toHaveBeenCalledWith('EN', {
      daily_minutes: 30,
      weekly_sessions: 4,
      weekly_minutes: 120,
    })
    expect(wrapper.text()).toContain('daily_minutes must be between 1 and 480')
  })
})
