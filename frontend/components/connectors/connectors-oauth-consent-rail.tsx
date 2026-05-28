'use client'

import { BookOpen, Calendar, Github, Instagram, Mail } from 'lucide-react'

function XGlyph() {
  return (
    <span className="font-mono text-sm font-bold text-(--qs-text)" aria-hidden>
      𝕏
    </span>
  )
}

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
    case 'instagram_graph':
      return <Instagram className="h-5 w-5 text-pollen" aria-hidden />
    case 'facebook_graph':
      return <Instagram className="h-5 w-5 text-(--qs-cyan)" aria-hidden />
    case 'twitter_api_v2':
      return <XGlyph />
    case 'tiktok_content':
      return <span className="font-mono text-xs font-bold text-pollen" aria-hidden>TT</span>
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
    <V4Card id="oauth-consent" glow className="scroll-mt-28">
      <V4CardHeader
        title="Connect Gmail, Outlook, Calendar, GitHub, Notion & social (Meta · X · TikTok)"
        description="One tap launches vendor consent in the browser. Queenswarm exchanges the authorization code server-side (PKCE for X/TikTok), seals tokens into the connector vault, and refreshes Dynamic Hub rows. Meta = Instagram/Facebook · X = tweet publish · TikTok = video publish."
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
