import { test, expect } from '@playwright/test';

test.describe('LEVI-AI v14.0 Sovereign Smoke Test', () => {
  test.beforeEach(async ({ page }) => {
    // 1. Auth Handshake
    await page.goto('/login');
    await page.fill('input[type="email"]', 'core@levi.ai');
    await page.fill('input[type="password"]', 'sovereign_pass');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/');
  });

  test('full mission lifecycle: submit -> dag -> hitl -> memory', async ({ page }) => {
    // 2. Submit Task
    const prompt = 'Autonomous Graduation v14.0';
    await page.fill('.task-input', prompt);
    await page.click('.submit-button');

    // 3. Confirm DAG Renders
    const dagContainer = page.locator('.graph-wrapper');
    await expect(dagContainer).toBeVisible();
    await expect(page.locator('.sovereign-node')).toHaveCount(4);

    // 4. Intercept HITL Gate (Mocking pulse if needed, or waiting for real event)
    const hitlModal = page.locator('.hitl-modal');
    await expect(hitlModal).toBeVisible({ timeout: 15000 });
    await page.click('.btn-approve');
    await expect(hitlModal).not.toBeVisible();

    // 5. Verify Memory Persistence
    await page.click('a[href="/memory"]');
    await page.fill('.search-bar input', prompt);
    await page.keyboard.press('Enter');
    await expect(page.locator('.memory-card')).toContainText(prompt);

    // 6. Check Telemetry & Metrics
    await page.click('a[href="/metrics"]');
    await expect(page.locator('.metric-card')).toContainText('DAG GENERATION');
  });
});
