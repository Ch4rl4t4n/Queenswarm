'use client'

import { BookOpen, Calendar, CreditCard, Github, Mail } from 'lucide-react'

import { OAuthConnectButton } from '@/components/connectors/oauth-connect-button'
import { V4Badge, V4Card, V4CardHeader } from '@/components/ui/v4'
import type { OAuthConsentCatalogSlice } from '@/lib/connectors-oauth-catalog'

function VendorGlyph({ providerKey }: { providerKey: string }) {
  switch (providerKey) {
    case 'google_gmail':
      return <Mail className="h-5 w-5" aria-hidden />
    case 'google_calendar':
      return <Calendar className="h-5 w-5" aria-hidden />
    case 'microsoft_graph':
      return <Mail className="h-5 w-5 text-(--qs-cyan)" aria-hidden />
    case 'github_rest':
      return <Github className="h-5 w-5" aria-hidden />
    case 'notion_workspace':
      return <BookOpen className="h-5 w-5" aria-hidden />
    case 'stripe_billing':
      return <CreditCard className="h-5 w-5" aria-hidden />
    default:
      return <Mail className="h-5 w-5 opacity-60" aria-hidden />
  }
}

export interface ConnectorsOAuthConsentRailProps {
  catalog: OAuthConsentCatalogSlice | null
}

/**
 * Phase 4.0 hosted consent entrypoints — pairs Phase 3 MCP templates with vendor OAuth apps.
 */
export function ConnectorsOAuthConsentRail({ catalog }: ConnectorsOAuthConsentRailProps) {
  if (!catalog || !catalog.providers.length) {
    return null
  }

  const configuredCount = catalog.providers.filter((p) => p.configured).length

  return (
    <V4Card glow>
      <V4CardHeader
        title="Connect Gmail, Outlook, Calendar, GitHub, Notion & Stripe"
        description="One tap launches vendor consent in the browser. Queenswarm exchanges the authorization code server-side (PKCE where supported), seals tokens into the connector vault, and creates or refreshes the Dynamic Hub row automatically."
        actions={
          <V4Badge tone="info">
            Ready · {configuredCount}/{catalog.providers.length} vendors
          </V4Badge>
        }
      />
      <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.32em] text-(--qs-magenta)">
        Phase 4.0 · Hosted OAuth consent
      </p>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {catalog.providers.map((p) => (
          <OAuthConnectButton
            key={p.provider_key}
            providerKey={p.provider_key}
            label={p.label}
            configured={p.configured}
            logo={<VendorGlyph providerKey={p.provider_key} />}
          />
        ))}
      </div>

      <p className="mt-4 break-all font-mono text-[10px] leading-relaxed text-(--qs-text-3)">
        Registered redirect URI · {catalog.redirect_uri}
      </p>
    </V4Card>
  )
}
