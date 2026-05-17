/**
 * Phase 4.0 — OAuth consent catalog slice surfaced via ``GET /connectors/catalog``.
 */

export interface OAuthConsentProviderRow {
  provider_key: string
  label: string
  template_id: string
  vendor_family: string
  configured: boolean
  uses_pkce: boolean
}

export interface OAuthConsentCatalogSlice {
  redirect_uri: string
  providers: OAuthConsentProviderRow[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isProviderRow(value: unknown): value is OAuthConsentProviderRow {
  if (!isRecord(value)) {
    return false
  }
  return (
    typeof value.provider_key === 'string' &&
    typeof value.label === 'string' &&
    typeof value.template_id === 'string' &&
    typeof value.vendor_family === 'string' &&
    typeof value.configured === 'boolean' &&
    typeof value.uses_pkce === 'boolean'
  )
}

export function extractOAuthConsentCatalog(raw: Record<string, unknown>): OAuthConsentCatalogSlice | null {
  const oc = raw.oauth_consent
  if (!isRecord(oc)) {
    return null
  }
  const redirect_uri = oc.redirect_uri
  const providersRaw = oc.providers
  if (typeof redirect_uri !== 'string' || !Array.isArray(providersRaw)) {
    return null
  }
  const providers: OAuthConsentProviderRow[] = []
  for (const row of providersRaw) {
    if (isProviderRow(row)) {
      providers.push(row)
    }
  }
  return { redirect_uri: redirect_uri.trim(), providers }
}
