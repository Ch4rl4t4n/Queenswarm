import { expect, test } from '@playwright/test'

import { seedDashboardSessionCookie } from './fixtures/dashboard-session'

test.describe('OAuth consent callback relay', () => {
  test.beforeEach(async ({ context, baseURL }) => {
    await seedDashboardSessionCookie(context, baseURL ?? 'http://localhost:4310')
  })

  test('rejects vendor callback without matching HttpOnly state cookie', async ({ page }) => {
    const res = await page.goto('/api/auth/callback/oauth?code=fake&state=fake-state', { waitUntil: 'commit' })
    expect(res?.ok()).toBeTruthy()
    await expect(page).toHaveURL(/(\/connectors\?oauth=error|\/login\?oauth=error)/)
    await expect(page).toHaveURL(/reason=csrf_state_mismatch/)
  })
})
