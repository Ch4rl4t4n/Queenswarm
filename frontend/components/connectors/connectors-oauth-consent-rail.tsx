'use client'

import { BookOpen, Calendar, CreditCard, Github, Mail } from 'lucide-react'

import { OAuthConnectButton } from '@/components/connectors/oauth-connect-button'
import type { OAuthConsentCatalogSlice } from '@/lib/connectors-oauth-catalog'
import { cn } from '@/lib/utils'

function VendorGlyph({ providerKey }: { providerKey: string }) {
  switch (providerKey) {
    case 'google_gmail':
      return <Mail className="h-5 w-5" aria-hidden />
    case 'google_calendar':
      return <Calendar className="h-5 w-5" aria-hidden />
    case 'microsoft_graph':
      return <Mail className="h-5 w-5 text-[#7CBDFF]" aria-hidden />
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
    <section
      className={cn(
        'rounded-[28px] border border-[#1b1f4a]/90 bg-black/58 p-6 shadow-[0_35px_90px_-50px_rgb(255_0_170/0.18)]',
      )}
    >
      <header className="mb-5 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="font-[family-name:var(--font-poppins)] text-[11px] font-semibold uppercase tracking-[0.32em] text-magenta">
            Phase 4.0 · Hosted OAuth consent
          </p>
          <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#EEEEFF]">
            Connect Gmail, Outlook, Calendar, GitHub, Notion &amp; Stripe
          </h2>
          <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
            One tap launches vendor consent in the browser. Queenswarm exchanges the authorization code server-side (PKCE where supported),
            seals tokens into the connector vault, and creates or refreshes the Dynamic Hub row automatically.
          </p>
        </div>
        <p className="font-mono text-xs text-zinc-500">
          Ready · {configuredCount}/{catalog.providers.length} vendors configured
        </p>
      </header>

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

      <p className="mt-4 break-all font-mono text-[10px] leading-relaxed text-zinc-600">
        Registered redirect URI · {catalog.redirect_uri}
      </p>
    </section>
  )
}
