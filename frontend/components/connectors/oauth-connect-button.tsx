'use client'

import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export interface OAuthConnectButtonProps {
  /** Registry key (``google_gmail``, ``github_rest``, …). */
  providerKey: string
  /** Human label beside logo. */
  label: string
  /** False when vendor OAuth client env is not configured server-side. */
  configured: boolean
  /** Vendor glyph (Lucide or inline SVG). */
  logo: ReactNode
}

/**
 * Mobile-first POST to Next.js connect route — triggers PKCE + HttpOnly ``qs_oauth_state`` cookie + vendor redirect.
 */
export function OAuthConnectButton({ providerKey, label, configured, logo }: OAuthConnectButtonProps) {
  return (
    <form method="POST" action={`/api/auth/connect/${providerKey}`} className="block w-full">
      <button
        type="submit"
        disabled={!configured}
        className={cn(
          'flex min-h-[52px] w-full touch-manipulation items-center gap-3 rounded-2xl border px-4 py-3 text-left transition',
          'shadow-[inset_0_0_0_1px_rgb(255_184_0/0.08)]',
          configured
            ? 'border-pollen/35 bg-black/72 text-[#F4F4FF] hover:border-pollen/60 hover:bg-pollen/10'
            : 'cursor-not-allowed border-zinc-800 bg-black/40 text-zinc-600',
        )}
      >
        <span
          className={cn(
            'flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border bg-black/78',
            configured ? 'border-cyan/35 text-cyan' : 'border-zinc-800 text-zinc-600',
          )}
          aria-hidden
        >
          {logo}
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="truncate font-[family-name:var(--font-poppins)] text-sm font-semibold">{label}</span>
          <span className="font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500">
            {configured ? 'Hosted OAuth · Authorization Code + PKCE' : 'Configure OAuth client credentials in hive env'}
          </span>
        </span>
      </button>
    </form>
  )
}
