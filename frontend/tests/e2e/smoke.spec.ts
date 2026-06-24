import { test, expect } from '@playwright/test'

test.describe('Cloud Crew AI — smoke tests', () => {
  test('app loads with the office section visible', async ({ page }) => {
    // Mock all API calls so we don't need a real backend
    await page.route('/api/health', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok' }),
      })
    )
    await page.route('/api/sessions', (route) =>
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ session_id: 'mock-session-id' }),
      })
    )

    await page.goto('/')

    // The office section must be present
    await expect(page.locator('[data-testid="office"]')).toBeVisible()
  })

  test('all 6 agents are visible in the office', async ({ page }) => {
    await page.route('/api/**', (route) => route.fulfill({ status: 200, body: '{}' }))
    await page.goto('/')

    // Each agent is rendered with its data-testid
    const agentIds = ['leslie', 'alan', 'edgar', 'hedy', 'grace', 'vint']
    for (const id of agentIds) {
      await expect(page.locator(`[data-testid="agent-${id}"]`)).toBeVisible()
    }
  })

  test('challenge input is visible and accepts text', async ({ page }) => {
    await page.route('/api/**', (route) => route.fulfill({ status: 200, body: '{}' }))
    await page.goto('/')

    const textarea = page.locator('[data-testid="challenge-input"]')
    await expect(textarea).toBeVisible()

    await textarea.fill('Design a cloud-native microservices architecture')
    await expect(textarea).toHaveValue('Design a cloud-native microservices architecture')
  })

  test('agent names are visible (pioneer names shown)', async ({ page }) => {
    await page.route('/api/**', (route) => route.fulfill({ status: 200, body: '{}' }))
    await page.goto('/')

    // Check for agent display names (short capitalized names)
    await expect(page.locator('text=Leslie')).toBeVisible()
    await expect(page.locator('text=Alan')).toBeVisible()
    await expect(page.locator('text=Edgar')).toBeVisible()
    await expect(page.locator('text=Hedy')).toBeVisible()
    await expect(page.locator('text=Grace')).toBeVisible()
    await expect(page.locator('text=Vint')).toBeVisible()
  })

  test('submit button is present in the challenge input area', async ({ page }) => {
    await page.route('/api/**', (route) => route.fulfill({ status: 200, body: '{}' }))
    await page.goto('/')

    await expect(page.locator('[data-testid="submit-challenge"]')).toBeVisible()
  })
})
