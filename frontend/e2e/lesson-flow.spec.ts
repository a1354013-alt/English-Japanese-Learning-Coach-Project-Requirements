import { expect, test, type Page, type Route } from '@playwright/test'
import type {
  AnalyticsPayload,
  Lesson,
  ReviewAnswer,
  ReviewResult,
  StreakResponse,
  UserProgress,
} from '../src/types'

test.skip(
  process.env.RUN_E2E === '0',
  'RUN_E2E=0 disables browser e2e in CI and local quick checks.',
)

const TIMESTAMP = '2026-05-06T08:00:00.000Z'

function buildLesson(topic: string): Lesson {
  return {
    metadata: {
      lesson_id: 'e2e-demo-lesson',
      language: 'EN',
      level: 'A1',
      topic,
      generated_at: TIMESTAMP,
      estimated_duration_minutes: 20,
      key_points: ['Standups', 'Status updates'],
    },
    vocabulary: [
      {
        word: 'blocker',
        phonetic: '/ˈblɒk.ər/',
        definition_zh: '阻礙問題',
        example_sentence: 'I still have one blocker in the deployment step.',
        example_translation: '我在部署步驟仍然有一個阻礙問題。',
      },
      {
        word: 'ship',
        phonetic: '/ʃɪp/',
        definition_zh: '發布',
        example_sentence: 'We can ship the update this afternoon.',
        example_translation: '我們今天下午可以發布這次更新。',
      },
    ],
    grammar: {
      title: 'Present simple for updates',
      explanation:
        'Use the present simple to report status and near-term plans in a standup.',
      examples: [
        {
          sentence: 'I review pull requests every morning.',
          translation: '我每天早上都會審查 pull request。',
        },
      ],
      exercises: [
        {
          question: 'Choose the best standup update sentence.',
          options: [
            'I finish the API docs today.',
            'I am finish the API docs today.',
            'I finished the API docs tomorrow.',
          ],
          correct_answer: 'I finish the API docs today.',
          explanation:
            'This demo uses the simple present as a concise standup status update.',
        },
      ],
    },
    reading: {
      title: 'Demo standup note',
      content:
        'Our team reviews the checklist, fixes one blocker, and ships the lesson flow before noon.',
      word_count: 14,
      questions: [
        {
          question: 'What does the team do before noon?',
          options: [
            'Ships the lesson flow',
            'Cancels the release',
            'Writes a novel',
          ],
          correct_answer: 'Ships the lesson flow',
          explanation:
            'The note says the team ships the lesson flow before noon.',
        },
      ],
    },
    dialogue: {
      scenario: 'Morning standup',
      context: 'A short work update between teammates.',
      dialogue: [
        {
          speaker: 'Aki',
          text: 'I fixed the blocker this morning.',
          translation: '我今天早上修好了阻礙問題。',
        },
        {
          speaker: 'Mina',
          text: 'Great, then we can ship after lunch.',
          translation: '太好了，那我們午餐後就能發布。',
        },
      ],
      alternatives: [],
    },
    evidence: [],
  }
}

function buildProgress(
  isOnboarded: boolean,
  completedLessons: number,
): UserProgress {
  return {
    user_id: 'default_user',
    english_progress: {
      language: 'EN',
      current_level: 'A1',
      target_level: 'A2',
      completed_lessons: completedLessons,
      total_exercises: completedLessons > 0 ? 2 : 0,
      correct_exercises: completedLessons > 0 ? 2 : 0,
      accuracy_rate: completedLessons > 0 ? 100 : 0,
      last_study_date: completedLessons > 0 ? TIMESTAMP : null,
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
      level: completedLessons > 0 ? 2 : 1,
      current_xp: completedLessons > 0 ? 40 : 0,
      next_level_xp: 100,
      total_xp: completedLessons > 0 ? 90 : 0,
      avatar_url: '',
      title: completedLessons > 0 ? 'Focused Learner' : 'Novice Explorer',
      unlocked_skills: completedLessons > 0 ? ['lesson_flow'] : [],
      achievements: [],
      word_cards:
        completedLessons > 0
          ? [
              {
                word: 'blocker',
                rarity: 'B',
                collected_at: TIMESTAMP,
                language: 'EN',
                phonetic: '/ˈblɒk.ər/',
                definition_zh: '阻礙問題',
                example_sentence:
                  'I still have one blocker in the deployment step.',
                example_translation: '我在部署步驟仍然有一個阻礙問題。',
              },
            ]
          : [],
      streak_days: completedLessons > 0 ? 1 : 0,
      difficulty_mode: 'normal',
      is_onboarded: isOnboarded,
      error_distribution: {},
    },
    updated_at: TIMESTAMP,
  }
}

function buildAnalytics(completedLessons: number): AnalyticsPayload {
  return {
    total_xp: completedLessons > 0 ? 90 : 0,
    level: completedLessons > 0 ? 2 : 1,
    streak: completedLessons > 0 ? 1 : 0,
    longest_streak: completedLessons > 0 ? 1 : 0,
    lessons_completed: completedLessons,
    hardest_words:
      completedLessons > 0 ? [{ word: 'blocker', mistakes: 1 }] : [],
    weakest_category:
      completedLessons > 0 ? { category: 'grammar', active_items: 1 } : null,
    accuracy_trend:
      completedLessons > 0
        ? [
            {
              lesson_id: 'e2e-demo-lesson',
              latest_accuracy_rate: 100,
              best_accuracy_rate: 100,
              submitted_at: TIMESTAMP,
            },
          ]
        : [],
    today_completed: completedLessons > 0,
  }
}

function buildStreak(completedLessons: number): StreakResponse {
  return {
    success: true,
    current_streak: completedLessons > 0 ? 1 : 0,
    longest_streak: completedLessons > 0 ? 3 : 0,
    last_active_date: completedLessons > 0 ? '2026-05-11' : null,
    today_completed: completedLessons > 0,
  }
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function installMockApi(page: Page) {
  let currentLesson: Lesson | null = null
  let progress = buildProgress(false, 0)
  let streak = buildStreak(0)
  let analytics = buildAnalytics(0)

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()

    if (path === '/api/progress' && method === 'GET') {
      await fulfillJson(route, { success: true, progress, streak })
      return
    }

    if (path === '/api/onboard' && method === 'POST') {
      progress = buildProgress(
        true,
        progress.english_progress.completed_lessons,
      )
      await fulfillJson(route, { success: true })
      return
    }

    if (path === '/api/lessons/today/EN' && method === 'GET') {
      await fulfillJson(route, { success: true, lesson: currentLesson })
      return
    }

    if (path === '/api/streak' && method === 'GET') {
      await fulfillJson(route, streak)
      return
    }

    if (path === '/api/generate/lesson' && method === 'POST') {
      const body = request.postDataJSON() as { topic?: string } | null
      currentLesson = buildLesson(body?.topic || 'Daily standup update')
      await fulfillJson(route, { success: true, lesson: currentLesson })
      return
    }

    if (path === '/api/review' && method === 'POST') {
      const answers = (request.postDataJSON() as ReviewAnswer[]) || []
      progress = buildProgress(true, 1)
      streak = buildStreak(1)
      analytics = buildAnalytics(1)
      const result: ReviewResult = {
        success: true,
        total_questions: answers.length,
        correct_count: answers.length,
        accuracy_rate: 100,
        incorrect_items: [],
        gamification: {
          xp_added: 40,
          leveled_up: true,
        },
      }
      await fulfillJson(route, result)
      return
    }

    if (path === '/api/analytics' && method === 'GET') {
      await fulfillJson(route, { success: true, analytics })
      return
    }

    if (path.startsWith('/api/export/pdf/') && method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/pdf',
        body: '%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n',
      })
      return
    }

    if (path === '/api/demo/reset' && method === 'POST') {
      currentLesson = null
      progress = buildProgress(true, 0)
      streak = buildStreak(0)
      analytics = buildAnalytics(0)
      await fulfillJson(route, {
        success: true,
        message: 'Demo dataset reset',
        summary: {
          lessons: 0,
          imported_vocabulary: 0,
          wrong_answers: 0,
          today_lesson_id: '',
        },
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
}

test('lesson flow - generate, review, and see progress update', async ({
  page,
}) => {
  await installMockApi(page)

  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })
  page.on('dialog', async (dialog) => {
    throw new Error(`Unexpected native dialog: ${dialog.message()}`)
  })

  const progressResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/progress') &&
      response.request().method() === 'GET',
  )
  const todayLessonResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/lessons/today/EN') &&
      response.request().method() === 'GET',
  )
  const streakResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/streak') &&
      response.request().method() === 'GET',
  )

  await page.goto('/')
  await Promise.all([progressResponse, todayLessonResponse, streakResponse])

  await expect(page.getByTestId('app-title')).toBeVisible()

  const onboarding = page.getByTestId('onboarding-dialog')
  if (await onboarding.isVisible({ timeout: 3_000 }).catch(() => false)) {
    const onboardResponse = page.waitForResponse(
      (response) =>
        response.url().includes('/api/onboard') &&
        response.request().method() === 'POST',
    )
    await page.getByTestId('onboarding-start').click()
    await onboardResponse
    await expect(onboarding).toBeHidden()
  }

  await expect(page.getByTestId('today-lesson-title')).toBeVisible()
  await expect(
    page.getByText("Unable to load today's lesson. Please try again later."),
  ).toHaveCount(0)

  const generatePanel = page.getByTestId('generate-panel')
  await expect(generatePanel).toBeVisible()

  const generatedLessonResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/generate/lesson') &&
      response.request().method() === 'POST' &&
      response.status() === 200,
  )
  await page.getByTestId('generate-topic').fill('PW stable flow')
  await page.getByTestId('generate-button').click()
  await generatedLessonResponse

  await expect(page.getByTestId('lesson-vocabulary')).toBeVisible()
  await expect(page.getByTestId('lesson-grammar')).toBeVisible()
  await expect(page.getByTestId('lesson-reading')).toBeVisible()

  const g00 = page.getByTestId('grammar-option-0-0')
  if (await g00.isVisible().catch(() => false)) {
    await g00.check()
  } else {
    await page
      .getByTestId('grammar-input-0')
      .fill('I finish the API docs today.')
  }

  const r00 = page.getByTestId('reading-option-0-0')
  await expect(r00).toBeVisible()
  await r00.check()

  const reviewResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/review') &&
      response.request().method() === 'POST' &&
      response.status() === 200,
  )
  const reviewedStreakResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/streak') &&
      response.request().method() === 'GET' &&
      response.status() === 200,
  )
  await page.getByTestId('submit-review').click()
  await Promise.all([reviewResponse, reviewedStreakResponse])

  await expect(page.getByTestId('review-result')).toBeVisible()
  await expect(page.getByTestId('review-score')).toHaveText(
    /^\s*Score:\s+\d+\s+\/\s+\d+\s+\(\d+(\.\d+)?%\)\s*$/,
  )

  const progressPageResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/progress') &&
      response.request().method() === 'GET' &&
      response.status() === 200,
  )
  await page.getByTestId('nav-progress').click()
  await progressPageResponse
  await expect(page.getByText(/Completed lessons:\s*1/)).toBeVisible()
  await expect(page.getByTestId('progress-en-completed')).toHaveText(/[1-9]\d*/)

  const revisitProgressResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/progress') &&
      response.request().method() === 'GET' &&
      response.status() === 200,
  )
  const revisitTodayResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/lessons/today/EN') &&
      response.request().method() === 'GET' &&
      response.status() === 200,
  )
  const revisitStreakResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/streak') &&
      response.request().method() === 'GET' &&
      response.status() === 200,
  )
  await page.goto('/')
  await Promise.all([
    revisitProgressResponse,
    revisitTodayResponse,
    revisitStreakResponse,
  ])
  await expect(page.getByTestId('lesson-vocabulary')).toBeVisible()

  const pdfResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/export/pdf/') &&
      response.request().method() === 'GET' &&
      response.status() === 200,
  )
  await page.getByRole('button', { name: 'Export PDF' }).click()
  expect((await pdfResponse).headers()['content-type']).toContain(
    'application/pdf',
  )

  const analyticsResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/analytics') &&
      response.request().method() === 'GET' &&
      response.status() === 200,
  )
  await page.goto('/analytics')
  await analyticsResponse
  await expect(page.getByText('Learning Analytics')).toBeVisible()
  await expect(page.getByText('Total XP')).toBeVisible()
})
