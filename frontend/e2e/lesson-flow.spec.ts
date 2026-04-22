import { test, expect } from '@playwright/test'

test('lesson flow - generate, review, and see progress update', async ({ page }) => {
  await page.goto('/')

  // App shell loads
  await expect(page.getByTestId('app-title')).toBeVisible()

  // Handle onboarding modal on fresh DBs.
  const onboarding = page.getByTestId('onboarding-dialog')
  if (await onboarding.isVisible().catch(() => false)) {
    await page.getByTestId('onboarding-start').click()
    await expect(onboarding).toBeHidden()
  }

  await expect(page.getByTestId('today-lesson-title')).toBeVisible()

  // Generate a lesson (must exist for review/progress flow).
  const generatePanel = page.getByTestId('generate-panel')
  if (await generatePanel.isVisible().catch(() => false)) {
    // Use a unique topic to avoid accidental dedup/idempotency collisions in local runs.
    await page.getByTestId('generate-topic').fill(`PW ${Date.now()}`)
    await page.getByTestId('generate-button').click()
  }

  // Lesson content appears.
  await expect(page.getByTestId('lesson-vocabulary')).toBeVisible({ timeout: 45_000 })
  await expect(page.getByTestId('lesson-grammar')).toBeVisible()
  await expect(page.getByTestId('lesson-reading')).toBeVisible()

  // Answer at least one grammar and one reading question (critical to review submission).
  const g00 = page.getByTestId('grammar-option-0-0')
  if (await g00.isVisible().catch(() => false)) {
    await g00.check()
  } else {
    await page.getByTestId('grammar-input-0').fill('A')
  }

  const r00 = page.getByTestId('reading-option-0-0')
  await expect(r00).toBeVisible()
  await r00.check()

  await page.getByTestId('submit-review').click()

  // Review result must be shown.
  await expect(page.getByTestId('review-result')).toBeVisible()
  await expect(page.getByTestId('review-score')).toHaveText(/^Score:\s+\d+\s+\/\s+\d+\s+\(\d+(\.\d+)?%\)$/)

  // Progress page reflects the completed lesson.
  await page.getByTestId('nav-progress').click()
  await expect(page.getByTestId('progress-en-completed')).toBeVisible()
  await expect(page.getByTestId('progress-en-completed')).toHaveText(/[1-9]\d*/)
})
