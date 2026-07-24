import { expect, test, type Page, type Route } from '@playwright/test'
import type {
  Language,
  LearningGoal,
  LearningSessionEventRecord,
  LearningSessionRecord,
  LearningSessionSummary,
  ProgressResponse,
  WeeklyLearningInsight,
} from '../src/types'

test.skip(
  process.env.RUN_E2E === '0',
  'RUN_E2E=0 disables browser e2e in CI and local quick checks.',
)

const startedAt = '2026-07-24T08:00:00.000Z'
const completedAt = '2026-07-24T08:25:00.000Z'

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

const buildProgress = (): ProgressResponse => ({
  success: true,
  progress: {
    user_id: 'default_user',
    english_progress: {
      language: 'EN',
      current_level: 'A1',
      target_level: 'A2',
      completed_lessons: 0,
      total_exercises: 0,
      correct_exercises: 0,
      accuracy_rate: 100,
      last_study_date: null,
    },
    japanese_progress: {
      language: 'JP',
      current_level: 'N5',
      target_level: 'N4',
      completed_lessons: 0,
      total_exercises: 0,
      correct_exercises: 0,
      accuracy_rate: 0,
      last_study_date: null,
    },
    rpg_stats: {
      level: 1,
      current_xp: 0,
      next_level_xp: 100,
      total_xp: 0,
      avatar_url: '',
      title: 'Focused Learner',
      unlocked_skills: [],
      achievements: [],
      word_cards: [],
      streak_days: 0,
      difficulty_mode: 'normal',
      is_onboarded: true,
      error_distribution: {},
    },
    updated_at: startedAt,
  },
  streak: {
    current_streak: 0,
    longest_streak: 0,
    last_active_date: null,
    today_completed: false,
  },
})

const buildSession = (
  language: Language,
  status: LearningSessionRecord['status'] = 'active',
): LearningSessionRecord => ({
  session_id: `session-${language.toLowerCase()}`,
  language,
  status,
  planned_minutes: language === 'EN' ? 10 : 20,
  started_at: startedAt,
  ended_at: status === 'active' ? null : completedAt,
  duration_seconds: status === 'active' ? null : 1500,
  created_at: startedAt,
  updated_at: status === 'active' ? startedAt : completedAt,
})

const buildGoal = (language: Language): LearningGoal => ({
  language,
  daily_minutes: language === 'EN' ? 20 : 15,
  weekly_sessions: language === 'EN' ? 4 : 3,
  weekly_minutes: language === 'EN' ? 120 : 90,
  created_at: '2026-07-20T00:00:00.000Z',
  updated_at: '2026-07-20T00:00:00.000Z',
})

const buildSummary = (
  session: LearningSessionRecord,
  eventCount: number,
): LearningSessionSummary => ({
  session_id: session.session_id,
  language: session.language,
  status: session.status,
  started_at: session.started_at,
  ended_at: session.ended_at,
  duration_seconds: session.duration_seconds,
  planned_minutes: session.planned_minutes,
  total_event_count: eventCount,
  counts_by_event_type: {
    lesson_started: 0,
    lesson_completed: 0,
    review_answered: 0,
    srs_reviewed: 0,
    chat_turn_completed: 0,
    feynman_completed: 0,
    micro_lesson_completed: 0,
    session_note: eventCount,
  },
  lesson_completion_count: 0,
  review_answer_count: 0,
  srs_review_count: 0,
  chat_turn_count: 0,
  feynman_completion_count: 0,
  micro_lesson_completion_count: 0,
  first_event_at: eventCount ? '2026-07-24T08:01:00.000Z' : null,
  last_event_at: eventCount ? '2026-07-24T08:01:00.000Z' : null,
  planned_duration_goal_reached: true,
  correct_event_count: null,
})

const buildInsight = (
  language: Language,
  completedSessions: number,
): WeeklyLearningInsight => ({
  week_start: '2026-07-20T00:00:00.000+08:00',
  week_end: '2026-07-27T00:00:00.000+08:00',
  language,
  completed_session_count: completedSessions,
  abandoned_session_count: 0,
  total_completed_duration_seconds: completedSessions ? 1500 : 0,
  active_learning_days: completedSessions ? 1 : 0,
  average_completed_session_duration_seconds: completedSessions ? 1500 : null,
  daily_minute_goal_progress: completedSessions ? 0.18 : 0,
  weekly_session_goal_progress: completedSessions ? 0.25 : 0,
  weekly_minute_goal_progress: completedSessions ? 0.21 : 0,
  event_counts_by_type: {
    lesson_started: 0,
    lesson_completed: 0,
    review_answered: 1,
    srs_reviewed: 0,
    chat_turn_completed: 0,
    feynman_completed: 0,
    micro_lesson_completed: 0,
    session_note: completedSessions ? 1 : 0,
  },
  lesson_completion_count: 0,
  review_answer_count: 1,
  correct_review_answer_count: 0,
  review_correctness_rate: null,
  srs_review_count: 0,
  chat_turn_count: 0,
  feynman_completion_count: 0,
  micro_lesson_completion_count: 0,
  most_active_day: completedSessions ? '2026-07-24' : null,
  recent_completed_sessions: completedSessions
    ? [
        {
          session_id: 'session-en',
          status: 'completed',
          started_at: startedAt,
          ended_at: completedAt,
          duration_seconds: 1500,
          planned_minutes: 10,
          total_event_count: 1,
        },
      ]
    : [],
  goal: buildGoal(language),
})

async function installLearningSessionMocks(page: Page) {
  let enSession: LearningSessionRecord | null = null
  let jpSession: LearningSessionRecord | null = null
  let enEvents: LearningSessionEventRecord[] = []
  let jpEvents: LearningSessionEventRecord[] = []
  let noteAttempts = 0
  let completedSessions = 0
  let completeCalls = 0
  let abandonCalls = 0

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()

    if (path === '/api/progress' && method === 'GET') {
      await fulfillJson(route, buildProgress())
      return
    }

    if (path === '/api/learning-sessions/active' && method === 'GET') {
      const language = url.searchParams.get('language') === 'JP' ? 'JP' : 'EN'
      await fulfillJson(route, {
        success: true,
        session: language === 'EN' ? enSession : jpSession,
      })
      return
    }

    if (path === '/api/learning-sessions' && method === 'POST') {
      const body = request.postDataJSON() as {
        language: Language
        planned_minutes?: number
      }
      const session = {
        ...buildSession(body.language),
        planned_minutes: body.planned_minutes ?? null,
      }
      if (body.language === 'EN') enSession = session
      else jpSession = session
      await fulfillJson(route, { success: true, session })
      return
    }

    if (path === '/api/learning-sessions' && method === 'GET') {
      const language = url.searchParams.get('language') === 'JP' ? 'JP' : 'EN'
      await fulfillJson(route, {
        success: true,
        sessions:
          language === 'EN' && completedSessions
            ? [buildSession('EN', 'completed')]
            : [],
        limit: 10,
        has_more: false,
        next_cursor: null,
      })
      return
    }

    const eventMatch = path.match(/^\/api\/learning-sessions\/([^/]+)\/events$/)
    if (eventMatch && method === 'GET') {
      const sessionId = decodeURIComponent(eventMatch[1])
      await fulfillJson(route, {
        success: true,
        events: sessionId === 'session-jp' ? jpEvents : enEvents,
        limit: 50,
        has_more: false,
        next_cursor: null,
      })
      return
    }

    if (eventMatch && method === 'POST') {
      noteAttempts += 1
      if (noteAttempts === 1) {
        await fulfillJson(
          route,
          { error: true, message: 'simulated timeout', code: 'timeout' },
          504,
        )
        return
      }
      const sessionId = decodeURIComponent(eventMatch[1])
      const body = request.postDataJSON() as {
        metadata: { note: string }
      }
      const event: LearningSessionEventRecord = {
        event_id: `note-${sessionId}-1`,
        session_id: sessionId,
        event_type: 'session_note',
        entity_type: null,
        entity_id: null,
        sequence_number: 1,
        metadata: { note: body.metadata.note },
        occurred_at: '2026-07-24T08:01:00.000Z',
        created_at: '2026-07-24T08:01:00.000Z',
      }
      if (sessionId === 'session-jp') jpEvents = [event]
      else enEvents = [event]
      await fulfillJson(route, { success: true, event })
      return
    }

    const completeMatch = path.match(
      /^\/api\/learning-sessions\/([^/]+)\/complete$/,
    )
    if (completeMatch && method === 'POST') {
      completeCalls += 1
      enSession = buildSession('EN', 'completed')
      completedSessions = 1
      await fulfillJson(route, { success: true, session: enSession })
      return
    }

    const abandonMatch = path.match(
      /^\/api\/learning-sessions\/([^/]+)\/abandon$/,
    )
    if (abandonMatch && method === 'POST') {
      abandonCalls += 1
      jpSession = buildSession('JP', 'abandoned')
      await fulfillJson(route, { success: true, session: jpSession })
      return
    }

    const summaryMatch = path.match(
      /^\/api\/learning-sessions\/([^/]+)\/summary$/,
    )
    if (summaryMatch && method === 'GET') {
      const sessionId = decodeURIComponent(summaryMatch[1])
      const session =
        sessionId === 'session-jp'
          ? (jpSession ?? buildSession('JP', 'abandoned'))
          : (enSession ?? buildSession('EN', 'completed'))
      await fulfillJson(route, {
        success: true,
        summary: buildSummary(session, sessionId === 'session-jp' ? 0 : 1),
      })
      return
    }

    if (path === '/api/learning-goals' && method === 'GET') {
      const language = url.searchParams.get('language') === 'JP' ? 'JP' : 'EN'
      await fulfillJson(route, { success: true, goal: buildGoal(language) })
      return
    }

    if (path === '/api/learning-goals' && method === 'PUT') {
      const language = url.searchParams.get('language') === 'JP' ? 'JP' : 'EN'
      await fulfillJson(route, { success: true, goal: buildGoal(language) })
      return
    }

    if (path === '/api/learning-insights/weekly' && method === 'GET') {
      const language = url.searchParams.get('language') === 'JP' ? 'JP' : 'EN'
      await fulfillJson(route, {
        success: true,
        insight: buildInsight(
          language,
          language === 'EN' ? completedSessions : 0,
        ),
      })
      return
    }

    await fulfillJson(
      route,
      {
        error: true,
        message: `Unhandled mock API request: ${method} ${path}`,
        code: 'UNHANDLED_E2E_ROUTE',
      },
      500,
    )
  })

  return {
    counts: () => ({ noteAttempts, completeCalls, abandonCalls }),
  }
}

test('learning session panel restores, retries notes, completes, and isolates languages', async ({
  page,
}) => {
  const mocks = await installLearningSessionMocks(page)
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })
  page.on('dialog', async (dialog) => {
    await dialog.accept()
  })
  await page.clock.setFixedTime(new Date('2026-07-24T08:05:00.000Z'))

  await page.goto('/progress')
  await expect(page.getByTestId('learning-session-panel')).toBeVisible()

  await page.getByRole('button', { name: '10 min' }).click()
  await page.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByText('5:00').first()).toBeVisible()
  await expect(page.getByText('No events yet.')).toBeVisible()

  const longNote = 'x'.repeat(500)
  await page.getByPlaceholder('Session note').fill(longNote)
  await page.getByRole('button', { name: 'Add note' }).click()
  await expect(page.getByText('simulated timeout')).toBeVisible()
  await page.getByRole('button', { name: 'Add note' }).click()
  await expect(page.locator('.timeline li')).toHaveCount(1)
  await expect(page.locator('.timeline li')).toContainText(longNote)

  await page.reload()
  await expect(page.getByTestId('learning-session-panel')).toBeVisible()
  await expect(page.locator('.timeline li')).toHaveCount(1)
  await expect(page.getByText('5:00').first()).toBeVisible()

  await page.getByRole('button', { name: 'Complete' }).click()
  await expect(page.getByText(/completed/)).toBeVisible()
  await expect(page.getByText('25:00')).toBeVisible()
  await expect(
    page.getByTestId('weekly-review').getByText('Completed'),
  ).toBeVisible()
  await expect(
    page.getByTestId('weekly-review').getByText('1').first(),
  ).toBeVisible()
  expect(mocks.counts().noteAttempts).toBe(2)
  expect(mocks.counts().completeCalls).toBe(1)

  await page.getByRole('combobox').selectOption('JP')
  await expect(page.getByRole('button', { name: 'Start' })).toBeVisible()
  await page.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByText('JP')).toBeVisible()
  await page.getByRole('button', { name: 'Abandon' }).click()
  await expect(page.getByText(/abandoned/)).toBeVisible()
  expect(mocks.counts().abandonCalls).toBe(1)
})
