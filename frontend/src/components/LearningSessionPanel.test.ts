import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
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
      await wrapper
        .findAll('button')
        .find((button) => button.text() === 'Add note')
        ?.trigger('click')
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
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Add note')
      ?.trigger('click')
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Add note')
      ?.trigger('click')
    await flushPromises()

    expect(apiMocks.addNote).toHaveBeenCalledTimes(2)
    expect(apiMocks.addNote.mock.calls[0][2]).toBe(
      apiMocks.addNote.mock.calls[1][2],
    )
  })

  it('creates separate operation ids for intentional identical notes and de-duplicates canonical events', async () => {
    const wrapper = await mountReady()
    apiMocks.addNote.mockResolvedValue({ success: true, event: noteEvent })

    await wrapper.find('input[placeholder="Session note"]').setValue('same')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Add note')
      ?.trigger('click')
    await flushPromises()
    await wrapper.find('input[placeholder="Session note"]').setValue('same')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Add note')
      ?.trigger('click')
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

  it('does not let a slow previous-language reload overwrite the current language', async () => {
    let resolveEnglish: ((value: unknown) => void) | undefined
    apiMocks.getActive
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveEnglish = resolve
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
    resolveEnglish?.({ success: true, session: activeSession })
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('JP')
    expect(wrapper.text()).not.toContain('session-en')
  })
})
