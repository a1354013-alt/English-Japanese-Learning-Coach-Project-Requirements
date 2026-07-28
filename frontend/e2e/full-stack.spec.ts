import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { expect, test, type APIRequestContext } from '@playwright/test'

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'
const E2E_DIR = path.dirname(fileURLToPath(import.meta.url))
const DB_PATH = path.resolve(
  E2E_DIR,
  '../../backend/.playwright-data/language_coach.db',
)

type DbRow = Record<string, string | number | null>

function queryDb(sql: string, params: Array<string | number | null> = []) {
  const script = `
import json
import sqlite3
import sys

conn = sqlite3.connect(sys.argv[1])
conn.row_factory = sqlite3.Row
try:
    cursor = conn.execute(sys.argv[2], json.loads(sys.argv[3]))
    rows = [dict(row) for row in cursor.fetchall()] if cursor.description else []
    conn.commit()
    print(json.dumps(rows, default=str))
finally:
    conn.close()
`
  const output = execFileSync('python', [
    '-c',
    script,
    DB_PATH,
    sql,
    JSON.stringify(params),
  ]).toString('utf8')
  return JSON.parse(output) as DbRow[]
}

function scalarNumber(sql: string, params: Array<string | number | null> = []) {
  const rows = queryDb(sql, params)
  return Number(Object.values(rows[0] ?? { value: 0 })[0] ?? 0)
}

async function resetDemoSeed(request: APIRequestContext) {
  const response = await request.post(`${BACKEND_BASE_URL}/api/demo/reset`)
  expect(response.ok()).toBeTruthy()
  const payload = await response.json()
  expect(payload.summary.today_lesson_id).toBe('demo-en-today')
  return payload
}

test('full-stack demo flow updates progress and serves pdf export', async ({
  page,
  request,
}) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })

  await resetDemoSeed(request)

  await page.goto('/')
  await expect(page.getByTestId('today-lesson-title')).toBeVisible()
  await expect(
    page.getByText('Daily Standup Conversations').first(),
  ).toBeVisible()

  const grammarWrongOption = page.getByTestId('grammar-option-0-1')
  await expect(grammarWrongOption).toBeVisible()
  await grammarWrongOption.check()

  const readingCorrectOption = page.getByTestId('reading-option-0-0')
  await expect(readingCorrectOption).toBeVisible()
  await readingCorrectOption.check()

  const reviewResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/review') &&
      response.request().method() === 'POST' &&
      response.status() === 200,
  )
  await page.getByTestId('submit-review').click()
  await reviewResponse

  await expect(page.getByTestId('review-result')).toBeVisible()

  await page.goto('/progress')
  await expect(page.getByTestId('progress-en-completed')).toHaveText('2')

  await page.goto('/progress?tab=mistakes')
  await expect(
    page.getByText('Choose the best standup update sentence.').first(),
  ).toBeVisible()

  const pdfResponse = await request.get(
    `${BACKEND_BASE_URL}/api/export/pdf/demo-en-today`,
  )
  expect(pdfResponse.ok()).toBeTruthy()
  expect(pdfResponse.headers()['content-type']).toContain('application/pdf')
  const pdfBytes = await pdfResponse.body()
  expect(pdfBytes.subarray(0, 4).toString()).toBe('%PDF')

  const ragMaterials = await request.get(
    `${BACKEND_BASE_URL}/api/rag/materials?language=EN`,
  )
  expect(ragMaterials.ok()).toBeTruthy()
  await page.goto('/workspace?tab=materials')
  await expect(page.getByText('No materials yet.')).toBeVisible()

  await resetDemoSeed(request)
})

test('full-stack persisted chat restores, isolates, renames, and deletes conversations', async ({
  page,
  request,
}) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })

  await resetDemoSeed(request)
  page.on('dialog', async (dialog) => {
    if (dialog.type() === 'prompt') {
      await dialog.accept('Travel Renamed')
      return
    }
    await dialog.accept()
  })

  await page.goto('/workspace?tab=chat')
  await page.getByTestId('chat-scenario-select').selectOption('travel')
  await page.getByTestId('chat-new-conversation').click()

  await page.getByTestId('chat-input').fill('Hello from Playwright')
  await page.getByTestId('chat-send').click()
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText(
    'Hello from Playwright',
  )
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText(
    '[Travel] I heard: Hello from Playwright',
  )

  await page.reload()
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText(
    'Hello from Playwright',
  )

  await page.getByTestId('chat-input').fill('Second turn')
  await page.getByTestId('chat-send').click()
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText(
    'Second turn',
  )
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText(
    '[Travel] I heard: Second turn',
  )

  const renameButtons = page.locator('[data-testid^="rename-conversation-"]')
  await renameButtons.first().click()
  await expect(
    page.locator('[data-testid^="conversation-item-"]').first(),
  ).toContainText('Travel Renamed')

  await page.locator('select.workspace-language').selectOption('JP')
  await expect(page.getByTestId('chat-empty-state')).toBeVisible()
  await page.getByTestId('chat-new-conversation').click()
  await expect(
    page.locator('[data-testid^="conversation-item-"]').first(),
  ).toBeVisible()

  await page.locator('select.workspace-language').selectOption('EN')
  await expect(
    page.locator('[data-testid^="conversation-item-"]').first(),
  ).toContainText('Travel Renamed')
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText(
    'Hello from Playwright',
  )

  const deleteButtons = page.locator('[data-testid^="delete-conversation-"]')
  await deleteButtons.first().click()
  await expect(page.getByTestId('chat-empty-state')).toBeVisible()
})

test('learning session full-stack persists events, retries, goals, weekly insight, and finalization', async ({
  page,
  request,
}) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })

  await resetDemoSeed(request)

  const migrations = queryDb(
    'SELECT version FROM schema_migrations WHERE version IN (?, ?, ?) ORDER BY version',
    [
      '0012_learning_sessions_and_events.sql',
      '0013_review_and_srs_operation_ids.sql',
      '0014_learning_goals.sql',
    ],
  ).map((row) => row.version)
  expect(migrations).toEqual([
    '0012_learning_sessions_and_events.sql',
    '0013_review_and_srs_operation_ids.sql',
    '0014_learning_goals.sql',
  ])

  await page.goto('/progress')
  await page.getByTestId('learning-session-language').selectOption('EN')
  await page.getByTestId('learning-session-planned-minutes').fill('10')
  await page.getByTestId('learning-session-start').click()
  await expect(page.getByTestId('learning-session-active')).toContainText('EN')

  const active = await request.get(
    `${BACKEND_BASE_URL}/api/learning-sessions/active?language=EN`,
  )
  expect(active.ok()).toBeTruthy()
  const sessionId = (await active.json()).session.session_id as string
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_sessions WHERE session_id = ? AND status = ? AND planned_minutes = ?',
      [sessionId, 'active', 10],
    ),
  ).toBe(1)

  const lessonResponse = await request.get(
    `${BACKEND_BASE_URL}/api/lessons/today/EN`,
  )
  expect(lessonResponse.ok()).toBeTruthy()
  const lesson = (await lessonResponse.json()).lesson
  const lessonId = lesson.metadata.lesson_id as string

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const started = await request.post(
      `${BACKEND_BASE_URL}/api/lessons/${encodeURIComponent(lessonId)}/start`,
      { data: { idempotency_key: 'full-stack-lesson-start' } },
    )
    expect(started.ok()).toBeTruthy()
  }
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_session_events WHERE session_id = ? AND event_type = ?',
      [sessionId, 'lesson_started'],
    ),
  ).toBe(1)

  const answers = [
    ...lesson.grammar.exercises.map(
      (exercise: { correct_answer: string }, index: number) => ({
        lesson_id: lessonId,
        exercise_type: 'grammar',
        question_index: index,
        user_answer: exercise.correct_answer,
        correct_answer: exercise.correct_answer,
        client_submission_id: 'full-stack-review-1',
      }),
    ),
    ...lesson.reading.questions.map(
      (question: { correct_answer: string }, index: number) => ({
        lesson_id: lessonId,
        exercise_type: 'reading',
        question_index: index,
        user_answer: question.correct_answer,
        correct_answer: question.correct_answer,
        client_submission_id: 'full-stack-review-1',
      }),
    ),
  ]
  const totalReviewAnswers = answers.length
  const beforeXp = scalarNumber(
    "SELECT json_extract(rpg_stats, '$.total_xp') AS xp FROM progress WHERE user_id = ?",
    ['default_user'],
  )
  const firstReview = await request.post(`${BACKEND_BASE_URL}/api/review`, {
    data: answers,
  })
  const retryReview = await request.post(`${BACKEND_BASE_URL}/api/review`, {
    data: answers,
  })
  expect(firstReview.ok()).toBeTruthy()
  expect(retryReview.ok()).toBeTruthy()
  expect((await retryReview.json()).gamification.xp_added).toBe(0)
  const afterRetryXp = scalarNumber(
    "SELECT json_extract(rpg_stats, '$.total_xp') AS xp FROM progress WHERE user_id = ?",
    ['default_user'],
  )
  expect(afterRetryXp).toBe(
    beforeXp + (await firstReview.json()).gamification.xp_added,
  )
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM review_submissions WHERE client_submission_id = ?',
      ['full-stack-review-1'],
    ),
  ).toBe(1)
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_session_events WHERE session_id = ? AND event_type = ?',
      [sessionId, 'lesson_completed'],
    ),
  ).toBe(1)
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_session_events WHERE session_id = ? AND event_type = ?',
      [sessionId, 'review_answered'],
    ),
  ).toBe(totalReviewAnswers)

  const secondAttempt = answers.map((answer) => ({
    ...answer,
    client_submission_id: 'full-stack-review-2',
  }))
  const newReview = await request.post(`${BACKEND_BASE_URL}/api/review`, {
    data: secondAttempt,
  })
  expect(newReview.ok()).toBeTruthy()
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM review_submissions WHERE lesson_id = ?',
      [lessonId],
    ),
  ).toBe(2)

  const dueItems = await request.get(
    `${BACKEND_BASE_URL}/api/srs/items/due?language=EN`,
  )
  expect(dueItems.ok()).toBeTruthy()
  const item = (await dueItems.json()).items[0]
  expect(item.item_id).toBeTruthy()
  const itemReview = await request.post(
    `${BACKEND_BASE_URL}/api/srs/items/review`,
    {
      data: {
        item_id: item.item_id,
        rating: 5,
        response_time_ms: 1200,
        source: 'srs_review',
      },
    },
  )
  expect(itemReview.ok()).toBeTruthy()

  queryDb(
    `
INSERT INTO srs_vocabulary (
  user_id, word, language, data, srs_level, ease_factor, interval, next_review, last_reviewed
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
`,
    [
      'default_user',
      'legacy-full-stack',
      'EN',
      '{"definition_zh":"legacy"}',
      0,
      2.5,
      0,
      '2000-01-01T00:00:00',
      null,
    ],
  )
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const legacySrs = await request.post(`${BACKEND_BASE_URL}/api/srs/review`, {
      data: {
        word: 'legacy-full-stack',
        language: 'EN',
        quality: 4,
        client_operation_id: 'legacy-full-stack-srs',
      },
    })
    expect(legacySrs.ok()).toBeTruthy()
  }
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_session_events WHERE session_id = ? AND event_type = ?',
      [sessionId, 'srs_reviewed'],
    ),
  ).toBe(2)

  await page.goto('/workspace?tab=chat')
  await page.getByTestId('chat-scenario-select').selectOption('travel')
  await page.getByTestId('chat-new-conversation').click()
  await page.getByTestId('chat-input').fill('Learning session chat turn')
  await page.getByTestId('chat-send').click()
  await expect(page.locator('[data-testid="chat-messages"]')).toContainText(
    '[Travel] I heard: Learning session chat turn',
  )
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_session_events WHERE session_id = ? AND event_type = ?',
      [sessionId, 'chat_turn_completed'],
    ),
  ).toBe(1)

  const note =
    'Long canonical note: '.padEnd(240, 'practice detail ') +
    'keep exactly one event after retry.'
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const noteResponse = await request.post(
      `${BACKEND_BASE_URL}/api/learning-sessions/${sessionId}/events`,
      {
        data: {
          event_type: 'session_note',
          metadata: { note },
          idempotency_key: 'session-note:full-stack-note',
        },
      },
    )
    expect(noteResponse.ok()).toBeTruthy()
  }
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_session_events WHERE session_id = ? AND event_type = ? AND idempotency_key = ?',
      [sessionId, 'session_note', 'session-note:full-stack-note'],
    ),
  ).toBe(1)

  await page.goto('/progress')
  await expect(page.getByTestId('learning-session-active')).toContainText('EN')
  await expect(
    page.getByTestId('learning-session-event-timeline'),
  ).toContainText('Long canonical note')
  await expect(page.getByTestId('learning-session-active')).toContainText('0')

  await page.getByTestId('learning-session-complete').click()
  await expect(
    page.getByTestId('learning-session-confirm-dialog'),
  ).toBeVisible()
  await page.getByTestId('learning-session-confirm-cancel').click()
  await expect(page.getByTestId('learning-session-active')).toBeVisible()
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_sessions WHERE session_id = ? AND status = ?',
      [sessionId, 'completed'],
    ),
  ).toBe(0)

  await page.getByTestId('learning-session-complete').click()
  await page.getByTestId('learning-session-confirm-accept').click()
  await expect(page.getByTestId('learning-session-confirm-dialog')).toBeHidden()
  await expect(page.getByTestId('learning-session-active')).toBeHidden()
  await expect(page.getByTestId('learning-session-summary')).toContainText(
    'Completed',
  )
  await expect(page.getByTestId('learning-session-history')).toContainText(
    'Completed',
  )
  const completedDuration = scalarNumber(
    'SELECT duration_seconds AS duration FROM learning_sessions WHERE session_id = ?',
    [sessionId],
  )
  expect(completedDuration).toBeGreaterThanOrEqual(0)

  await request.put(`${BACKEND_BASE_URL}/api/learning-goals?language=EN`, {
    data: {
      daily_minutes: 25,
      weekly_sessions: 5,
      weekly_minutes: 150,
    },
  })
  await page.reload()
  await expect(page.getByTestId('learning-session-history')).toContainText(
    'Completed',
  )
  await expect(page.getByTestId('learning-goal-daily-minutes')).toHaveValue(
    '25',
  )
  await expect(page.getByTestId('learning-goal-weekly-sessions')).toHaveValue(
    '5',
  )
  await expect(page.getByTestId('learning-goal-weekly-minutes')).toHaveValue(
    '150',
  )

  const weekly = await request.get(
    `${BACKEND_BASE_URL}/api/learning-insights/weekly?language=EN`,
  )
  expect(weekly.ok()).toBeTruthy()
  const insight = (await weekly.json()).insight
  expect(insight.completed_session_count).toBe(1)
  expect(insight.event_counts_by_type.lesson_started).toBe(1)
  expect(insight.event_counts_by_type.lesson_completed).toBe(1)
  expect(insight.event_counts_by_type.srs_reviewed).toBe(2)
  expect(insight.event_counts_by_type.chat_turn_completed).toBe(1)
  expect(insight.review_answer_count).toBe(totalReviewAnswers * 2)
  expect(insight.correct_review_answer_count).toBe(totalReviewAnswers * 2)
  expect(insight.review_correctness_rate).toBe(100)

  await page.getByTestId('learning-session-language').selectOption('JP')
  await expect(page.getByTestId('learning-session-start')).toBeVisible()
  const jpHistory = await request.get(
    `${BACKEND_BASE_URL}/api/learning-sessions?language=JP`,
  )
  expect((await jpHistory.json()).sessions).toHaveLength(0)
  const jpWeekly = await request.get(
    `${BACKEND_BASE_URL}/api/learning-insights/weekly?language=JP`,
  )
  expect((await jpWeekly.json()).insight.completed_session_count).toBe(0)

  await page.getByTestId('learning-session-planned-minutes').fill('10')
  await page.getByTestId('learning-session-start').click()
  await expect(page.getByTestId('learning-session-active')).toContainText('JP')
  const jpActive = await request.get(
    `${BACKEND_BASE_URL}/api/learning-sessions/active?language=JP`,
  )
  const jpSessionId = (await jpActive.json()).session.session_id as string

  await page.getByTestId('learning-session-abandon').click()
  await expect(
    page.getByTestId('learning-session-confirm-dialog'),
  ).toBeVisible()
  await page.getByTestId('learning-session-confirm-cancel').click()
  await expect(page.getByTestId('learning-session-active')).toBeVisible()
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_sessions WHERE session_id = ? AND status = ?',
      [jpSessionId, 'abandoned'],
    ),
  ).toBe(0)

  await page.getByTestId('learning-session-abandon').click()
  await page.getByTestId('learning-session-confirm-accept').click()
  await expect(page.getByTestId('learning-session-active')).toBeHidden()
  await expect(page.getByTestId('learning-session-summary')).toContainText(
    'Abandoned',
  )
  expect(
    scalarNumber(
      'SELECT COUNT(1) AS count FROM learning_sessions WHERE session_id = ? AND status = ?',
      [jpSessionId, 'abandoned'],
    ),
  ).toBe(1)

  await page.reload()
  await page.getByTestId('learning-session-language').selectOption('EN')
  await expect(page.getByTestId('learning-session-history')).toContainText(
    'Completed',
  )
  await expect(page.getByTestId('learning-goal-daily-minutes')).toHaveValue(
    '25',
  )
})
