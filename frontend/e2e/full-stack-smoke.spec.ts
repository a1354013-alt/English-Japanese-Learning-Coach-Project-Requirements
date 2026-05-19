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

  await resetDemoSeed(request)
})
