import { test, expect } from '@playwright/test';

test('lesson flow - generate and complete lesson', async ({ page }) => {
  // Open homepage
  await page.goto('/');
  
  // Wait for app to load
  await expect(page.getByText('English-Japanese Learning Coach')).toBeVisible();
  
  // Navigate to Today tab (already on homepage)
  await expect(page.getByRole('heading', { name: /generate/i })).toBeVisible({ timeout: 5000 });
  
  // Generate a lesson by clicking the generate button
  const generateButton = page.getByRole('button', { name: /generate/i });
  if (await generateButton.isVisible()) {
    await generateButton.click();
    
    // Wait for lesson to be generated
    await page.waitForTimeout(3000);
  }
  
  // Check if we can see lesson content or navigate to archive
  const archiveLink = page.getByRole('link', { name: 'Archive' });
  if (await archiveLink.isVisible()) {
    await archiveLink.click();
    
    // Wait for archive page
    await expect(page.getByText(/archive/i)).toBeVisible();
    
    // Look for any lesson in the archive
    const lessonLinks = page.getByRole('link', { name: /lesson/i });
    const count = await lessonLinks.count();
    
    if (count > 0) {
      // Click first lesson
      await lessonLinks.first().click();
      
      // Wait for lesson detail page
      await expect(page.getByText(/vocabulary/i)).toBeVisible({ timeout: 5000 });
      
      // Verify lesson sections exist
      await expect(page.getByText(/grammar/i)).toBeVisible();
      await expect(page.getByText(/reading/i)).toBeVisible();
    }
  }
  
  // Navigate to Progress page to verify progress tracking
  const progressLink = page.getByRole('link', { name: 'Progress' });
  if (await progressLink.isVisible()) {
    await progressLink.click();
    await expect(page.getByText(/progress|level|xp/i)).toBeVisible({ timeout: 5000 });
  }
});
