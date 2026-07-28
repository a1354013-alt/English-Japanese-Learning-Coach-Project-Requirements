import { expect, test, type APIRequestContext } from '@playwright/test'

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'

async function resetDemoSeed(request: APIRequestContext) {
  const response = await request.post(`${BACKEND_BASE_URL}/api/demo/reset`)
  expect(response.ok()).toBeTruthy()
  const payload = await response.json()
  expect(payload.summary.today_lesson_id).toBe('demo-en-today')
  return payload
}

test('full-stack smoke boots both apps and completes seeded review flow', async ({
  page,
  request,
}) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })

  const healthResponse = await request.get(`${BACKEND_BASE_URL}/api/health`)
  expect(healthResponse.ok()).toBeTruthy()

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

  await page.goto('/progress?tab=review')
  await expect(page).toHaveURL(/\/progress\?tab=review$/)
  await expect(page.getByTestId('srs-review-row').first()).toBeVisible()
  await expect(page.getByText('Vocabulary').first()).toBeVisible()
  await expect(page.getByText('Weak').first()).toBeVisible()
  await expect(page.getByText('grammar').first()).toBeVisible()

  await resetDemoSeed(request)
})

test('full-stack smoke persists a learning session completion flow', async ({
  page,
  request,
}) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })

  await resetDemoSeed(request)

  await page.goto('/progress')

  const panel = page.getByTestId('learning-session-panel')
  const activeSession = page.getByTestId('learning-session-active')
  const summary = page.getByTestId('learning-session-summary')
  const history = page.getByTestId('learning-session-history')
  const weeklyReview = page.getByTestId('learning-session-weekly-review')
  const timeline = page.getByTestId('learning-session-event-timeline')
  const confirmDialog = page.getByTestId('learning-session-confirm-dialog')

  await expect(panel).toBeVisible()

  await page.getByTestId('learning-session-start').click()
  await expect(activeSession).toBeVisible()
  await expect(activeSession).toContainText('Active')

  await page
    .getByTestId('learning-session-note-input')
    .fill('Smoke session note')
  await page.getByTestId('learning-session-add-note').click()
  await expect(timeline).toContainText('Smoke session note')

  await page.getByTestId('learning-session-complete').click()
  await expect(confirmDialog).toBeVisible()
  await page.getByTestId('learning-session-confirm-accept').click()

  await expect(confirmDialog).toBeHidden()
  await expect(activeSession).toBeHidden()
  await expect(summary).toContainText('Completed')
  await expect(timeline).toContainText('Smoke session note')
  await expect(history).toContainText('Completed')
  await expect(weeklyReview).toContainText('Completed')

  await page.reload()
  await expect(history).toContainText('Completed')
  await history.locator('.history-item').first().click()
  await expect(summary).toContainText('Completed')
  await expect(timeline).toContainText('Smoke session note')
})
