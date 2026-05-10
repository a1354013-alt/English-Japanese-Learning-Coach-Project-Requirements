import { expect, test } from '@playwright/test'

test('full-stack demo flow updates progress and serves pdf export', async ({ page, request }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })

  const reset = await request.post('http://127.0.0.1:8000/api/demo/reset')
  expect(reset.ok()).toBeTruthy()

  await page.goto('/')
  await expect(page.getByTestId('today-lesson-title')).toBeVisible()
  await expect(page.getByText('Daily Standup Conversations').first()).toBeVisible()

  const grammarWrongOption = page.getByTestId('grammar-option-0-1')
  await expect(grammarWrongOption).toBeVisible()
  await grammarWrongOption.check()

  const readingCorrectOption = page.getByTestId('reading-option-0-0')
  await expect(readingCorrectOption).toBeVisible()
  await readingCorrectOption.check()

  const reviewResponse = page.waitForResponse(
    (response) => response.url().includes('/api/review') && response.request().method() === 'POST' && response.status() === 200,
  )
  await page.getByTestId('submit-review').click()
  await reviewResponse

  await expect(page.getByTestId('review-result')).toBeVisible()

  await page.goto('/progress')
  await expect(page.getByTestId('progress-en-completed')).toHaveText('2')

  await page.goto('/progress?tab=mistakes')
  await expect(page.getByText('Choose the best standup update sentence.').first()).toBeVisible()

  const pdfResponse = await request.get('http://127.0.0.1:8000/api/export/pdf/demo-en-today')
  expect(pdfResponse.ok()).toBeTruthy()
  expect(pdfResponse.headers()['content-type']).toContain('application/pdf')
  const pdfBytes = await pdfResponse.body()
  expect(pdfBytes.subarray(0, 4).toString()).toBe('%PDF')

  const ragMaterials = await request.get('http://127.0.0.1:8000/api/rag/materials?language=EN')
  expect(ragMaterials.ok()).toBeTruthy()
  await page.goto('/workspace?tab=materials')
  await expect(page.getByText('No materials yet.')).toBeVisible()
})
