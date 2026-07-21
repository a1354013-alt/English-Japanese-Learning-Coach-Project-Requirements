import { expect, test, type APIRequestContext } from '@playwright/test'

const BACKEND_BASE_URL = 'http://127.0.0.1:8000'

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
