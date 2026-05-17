import { describe, expect, it } from 'vitest'

import { extractOAuthConsentCatalog } from '@/lib/connectors-oauth-catalog'

describe('extractOAuthConsentCatalog', () => {
  it('parses oauth_consent envelope from catalog payloads', () => {
    const parsed = extractOAuthConsentCatalog({
      oauth_consent: {
        redirect_uri: 'https://queenswarm.love/api/auth/callback/oauth',
        providers: [
          {
            provider_key: 'google_gmail',
            label: 'Gmail',
            template_id: 'gmail_google_workspace',
            vendor_family: 'google',
            configured: true,
            uses_pkce: true,
          },
        ],
      },
    })
    expect(parsed?.redirect_uri).toContain('/api/auth/callback/oauth')
    expect(parsed?.providers[0]?.provider_key).toBe('google_gmail')
  })

  it('returns null when oauth_consent missing', () => {
    expect(extractOAuthConsentCatalog({ phase3: {} })).toBeNull()
  })
})
