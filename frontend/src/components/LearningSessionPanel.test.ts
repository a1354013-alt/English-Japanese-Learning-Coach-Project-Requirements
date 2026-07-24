import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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

const completedSession = {
  ...activeSession,
  status: 'completed',
  ended_at: '2026-07-24T08:25:00.000Z',
  duration_seconds: 1500,
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

function defaultApiState(session: unknown = activeSession) {
  apiMocks.getActive.mockResolvedValue({ success: true, session })
  apiMocks.listEvents.mockResolvedValue({ success: true, events: [] })
  apiMocks.list.mockResolvedValue({
    success: true,
    sessions: [],
    limit: 10,
    has_more: false,
    next_cursor: null,
  })
  apiMocks.getGoal.mockResolvedValue({ success: true, goal })
  apiMocks.weeklyInsight.mockResolvedValue({ success: true, insight })
  apiMocks.addNote.mockResolvedValue({ success: true, event: noteEvent })
}

async function mountReady(session: unknown = activeSession) {
  defaultApiState(session)
  const wrapper = mount(LearningSessionPanel)
  await flushPromises()
  return wrapper
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
    vi.stubGlobal('crypto', {
      randomUUID: vi
        .fn()
        .mockReturnValueOnce('11111111-1111-4111-8111-111111111111')
        .mockReturnValueOnce('22222222-2222-4222-8222-222222222222')
        .mockReturnValueOnce('33333333-3333-4333-8333-333333333333'),
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

  it.each([1, 49, 500])(
    'uses a bounded operation id for a %i-character manual note',
    async (length) => {
      const wrapper = await mountReady()
      const note = 'x'.repeat(length)

      await wrapper.find('input[placeholder="Session note"]').setValue(note)
      await findButton(wrapper, 'Add note').trigger('click')
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

    await wrapper.find('input[placeholder="Session note"]').setValue('retry me')
    await findButton(wrapper, 'Add note').trigger('click')
    await flushPromises()
    await findButton(wrapper, 'Add note').trigger('click')
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

    await wrapper
      .find('input[placeholder="Session note"]')
      .setValue('first note')
    await findButton(wrapper, 'Add note').trigger('click')
    await flushPromises()
    await wrapper
      .find('input[placeholder="Session note"]')
      .setValue('edited note')
    await findButton(wrapper, 'Add note').trigger('click')
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

    await wrapper
      .find('input[placeholder="Session note"]')
      .setValue('same note')
    await findButton(wrapper, 'Add note').trigger('click')
    await flushPromises()
    await wrapper.find('select').setValue('JP')
    await flushPromises()
    await wrapper
      .find('input[placeholder="Session note"]')
      .setValue('same note')
    await findButton(wrapper, 'Add note').trigger('click')
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
    apiMocks.addNote.mockResolvedValue({ success: true, event: noteEvent })

    await wrapper.find('input[placeholder="Session note"]').setValue('same')
    await findButton(wrapper, 'Add note').trigger('click')
    await flushPromises()
    await wrapper.find('input[placeholder="Session note"]').setValue('same')
    await findButton(wrapper, 'Add note').trigger('click')
    await flushPromises()

    expect(apiMocks.addNote.mock.calls[0][2]).not.toBe(
      apiMocks.addNote.mock.calls[1][2],
    )
    expect(wrapper.findAll('.timeline li')).toHaveLength(1)
  })

  it('rejects notes when the visible session is already finalized', async () => {
    const wrapper = await mountReady({ ...activeSession, status: 'completed' })

    await wrapper.find('input[placeholder="Session note"]').setValue('blocked')
    const addButton = wrapper
      .findAll('button')
      .find((button) => button.text() === 'Add note')
    expect(addButton?.attributes('disabled')).toBeDefined()
    await addButton?.trigger('click')

    expect(apiMocks.addNote).not.toHaveBeenCalled()
  })

  it('reuses the stable completion idempotency key after a timeout retry', async () => {
    const wrapper = await mountReady()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    apiMocks.complete
      .mockRejectedValueOnce(new Error('timeout'))
      .mockResolvedValueOnce({ success: true, session: completedSession })
    apiMocks.summary.mockResolvedValue({
      success: true,
      summary: completedSummary,
    })

    await findButton(wrapper, 'Complete').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Unable to complete Session.')
    await findButton(wrapper, 'Complete').trigger('click')
    await flushPromises()

    expect(apiMocks.complete).toHaveBeenCalledTimes(2)
    expect(apiMocks.complete.mock.calls[0][1]).toBe(
      apiMocks.complete.mock.calls[1][1],
    )
    expect(wrapper.text()).toContain('completed')
    expect(wrapper.text()).toContain('25:00')
  })

  it('does not erase the active session when historical summary loading fails', async () => {
    const wrapper = await mountReady()
    apiMocks.summary.mockRejectedValueOnce(new Error('history failed'))
    apiMocks.list.mockResolvedValue({
      success: true,
      sessions: [completedSession],
      limit: 10,
      has_more: false,
      next_cursor: null,
    })

    await findButton(wrapper, 'Refresh').trigger('click')
    await flushPromises()
    await flushPromises()
    const historyItem = wrapper.find('.history-item')
    expect(historyItem.exists()).toBe(true)
    await historyItem.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Unable to load Session summary.')
    expect(wrapper.text()).toContain('5:00')
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
    apiMocks.listEvents.mockResolvedValue({ success: true, events: [] })
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

    const wrapper = mount(LearningSessionPanel)
    await wrapper.find('select').setValue('JP')
    resolveEnglish?.()
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('JP')
    expect(wrapper.text()).not.toContain('session-en')
  })
})
