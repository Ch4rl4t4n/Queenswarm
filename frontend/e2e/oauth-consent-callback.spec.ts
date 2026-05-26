import { expect, test } from '@playwright/test'

import { seedDashboardSessionCookie } from './fixtures/dashboard-session'

test.describe('OAuth consent callback relay', () => {
  test.beforeEach(async ({ context, baseURL }) => {
    await seedDashboardSessionCookie(context, baseURL ?? 'http://localhost:4310')
  })

  test('rejects vendor callback when cookie state conflicts with query state', async ({ page }) => {
    await page.context().addCookies([
      {
        name: 'qs_oauth_state',
        value: 'cookie-state',
        domain: new URL(page.url() || 'http://localhost:4310').hostname,
        path: '/',
        httpOnly: true,
        sameSite: 'Lax',
      },
    ])
    const res = await page.goto('/api/auth/callback/oauth?code=fake&state=query-state', { waitUntil: 'commit' })
    expect(res?.ok()).toBeTruthy()
    await expect(page).toHaveURL(/\/integrations\?tab=hub&oauth=error/)
    await expect(page).toHaveURL(/reason=csrf_state_mismatch/)
  })
})
