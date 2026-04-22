import { test, expect } from '@playwright/test'

test('lesson flow - generate, review, and see progress update', async ({ page }) => {
  await page.goto('/')

  // App shell loads
  await expect(page.getByText('English-Japanese Learning Coach')).toBeVisible()

  // Handle onboarding modal on fresh DBs.
  const welcome = page.getByRole('heading', { name: 'Welcome' })
  if (await welcome.isVisible().catch(() => false)) {
    await page.getByRole('button', { name: 'Start' }).click()
    await expect(welcome).toBeHidden()
  }

  await expect(page.getByRole('heading', { name: "Today's Lesson" })).toBeVisible()

  // Generate a lesson (must exist for review/progress flow).
  const generatePanel = page.getByRole('heading', { name: 'Generate lesson' })
  if (await generatePanel.isVisible().catch(() => false)) {
    await page.getByRole('button', { name: /^Generate$/ }).click()
    // Generation may fall back if no AI provider is available; wait for the generate panel to disappear.
    await expect(page.getByRole('button', { name: 'Generating...' })).toBeHidden({ timeout: 30_000 })
  }

  // Lesson content appears.
  await expect(page.getByRole('heading', { name: 'Vocabulary' })).toBeVisible({ timeout: 30_000 })
  await expect(page.getByRole('heading', { name: 'Grammar Exercises' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Reading' })).toBeVisible()

  // Answer at least one grammar and one reading question (critical to review submission).
  const g0 = page.locator('input[name="g-0"]')
  await expect(g0.first()).toBeVisible()
  await g0.first().check()

  const r0 = page.locator('input[name="r-0"]')
  await expect(r0.first()).toBeVisible()
  await r0.first().check()

  await page.getByRole('button', { name: 'Submit Review' }).click()

  // Review result must be shown.
  await expect(page.getByRole('heading', { name: 'Review Result' })).toBeVisible()
  await expect(page.getByText(/^Score:/)).toBeVisible()

  // Progress page reflects the completed lesson.
  await page.getByRole('link', { name: 'Progress' }).click()
  await expect(page.getByRole('heading', { name: 'English' })).toBeVisible()
  await expect(page.getByText(/Completed lessons: [1-9]\d*/)).toBeVisible()
})
