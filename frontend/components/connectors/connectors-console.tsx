'use client'

import Link from 'next/link'
import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2Icon,
  RefreshCw,
  Sparkles,
  Zap,
} from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { useCallback, useEffect, useState } from 'react'

import { ConnectorsOAuthConsentRail } from '@/components/connectors/connectors-oauth-consent-rail'
import { ConnectorsVaultPanel } from '@/components/connectors/connectors-vault-panel'
import { Phase3TemplateInspector } from '@/components/connectors/phase3-template-inspector'
import { InfoHint } from '@/components/hive/info-hint'
import { HiveApiError, hiveDelete, hiveGet, hivePatchJson, hivePostJson } from '@/lib/api'
import {
  parsePhase3IntegrationOverview,
  phase3OverviewCoverageScore,
  type Phase3IntegrationOverviewPayload,
} from '@/lib/connectors-phase3-overview'
import type { DynamicConnectorPayload } from '@/lib/connectors-types'
import {
  buildManifestJsonFromTemplate,
  extractPhase3FromCatalog,
  orderedPhase3Categories,
  phase3CategoryLabel,
  phase3ProvisionCoverage,
  type ObsidianVaultStatusPayload,
  type Phase3CatalogSlice,
  type Phase3TemplatePublic,
} from '@/lib/connectors-phase3'
import { extractOAuthConsentCatalog, type OAuthConsentCatalogSlice } from '@/lib/connectors-oauth-catalog'
import { cn } from '@/lib/utils'

interface ConnectorsEnvelope {
  items: DynamicConnectorPayload[]
  builtins: DynamicConnectorPayload[]
  customs: DynamicConnectorPayload[]
}

const AUTH_OPTIONS = ['none', 'api_key', 'bearer_token', 'oauth2'] as const

function Badge({ builtin, active }: { builtin: boolean; active: boolean }) {
  return (
    <div className="flex flex-wrap gap-2 font-[family-name:var(--font-poppins)] text-[11px] font-semibold">
      <span
        className={cn(
          'rounded-full border px-3 py-[3px] uppercase tracking-[0.18em]',
          builtin
            ? 'border-pollen text-pollen shadow-[0_0_10px_rgb(255_184_0/0.38)]'
            : 'border-cyan/35 text-cyan',
        )}
      >
        {builtin ? 'Built-in' : 'Custom'}
      </span>
      <span
        className={cn(
          'rounded-full border px-3 py-[3px]',
          active ? 'border-[#00FF88]/50 text-[#00FF88]' : 'border-magenta/50 text-[#FF00AA]',
        )}
      >
        {active ? 'Active' : 'Inactive'}
      </span>
    </div>
  )
}

async function reloadConnectors(): Promise<DynamicConnectorPayload[]> {
  const body = await hiveGet<ConnectorsEnvelope>('connectors/dynamic')
  return body.items
}

export function ConnectorsConsole() {
  const [rows, setRows] = useState<DynamicConnectorPayload[]>([])
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [phase3Slice, setPhase3Slice] = useState<Phase3CatalogSlice | null>(null)
  const [oauthCatalog, setOauthCatalog] = useState<OAuthConsentCatalogSlice | null>(null)
  const [oauthFlash, setOauthFlash] = useState<{ kind: 'success' | 'error'; message: string } | null>(null)
  const [phase3OpenCategory, setPhase3OpenCategory] = useState<string | null>('email')
  const [instantiatingId, setInstantiatingId] = useState<string | null>(null)
  const [obsidianStatus, setObsidianStatus] = useState<ObsidianVaultStatusPayload | null>(null)
  const [obsidianBusy, setObsidianBusy] = useState(false)
  const [obsidianErr, setObsidianErr] = useState<string | null>(null)

  const [slug, setSlug] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [authType, setAuthType] = useState<(typeof AUTH_OPTIONS)[number]>('none')
  const [secretBlob, setSecretBlob] = useState('')
  const [manifest, setManifest] = useState('')

  const [saving, setSaving] = useState(false)

  const [phase3Overview, setPhase3Overview] = useState<Phase3IntegrationOverviewPayload | null>(null)
  const [overviewErr, setOverviewErr] = useState<string | null>(null)
  const [overviewBusy, setOverviewBusy] = useState(false)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [testingConnectorId, setTestingConnectorId] = useState<string | null>(null)

  const refreshPhase3Overview = useCallback(async () => {
    setOverviewBusy(true)
    setOverviewErr(null)
    try {
      const raw = await hiveGet<unknown>('connectors/phase3/integration-overview')
      const parsed = parsePhase3IntegrationOverview(raw)
      setPhase3Overview(parsed)
      if (!parsed) {
        setOverviewErr('Overview payload malformed.')
      }
    } catch (err: unknown) {
      setOverviewErr(err instanceof HiveApiError ? err.message : 'Integration overview unavailable.')
    } finally {
      setOverviewBusy(false)
    }
  }, [])
  useEffect(() => {
    let cancelled = false
    reloadConnectors()
      .then((next) => {
        if (!cancelled) setRows(next)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setLoadErr(err instanceof HiveApiError ? err.message : 'Unable to fetch connectors.')
      })

    void hiveGet<Record<string, unknown>>('connectors/catalog')
      .then((raw) => {
        if (cancelled) return
        setPhase3Slice(extractPhase3FromCatalog(raw))
        setOauthCatalog(extractOAuthConsentCatalog(raw))
      })
      .catch(() => null)

    void hiveGet<ObsidianVaultStatusPayload>('connectors/phase3/obsidian/status')
      .then((snap) => {
        if (!cancelled) setObsidianStatus(snap)
      })
      .catch(() => null)

    void refreshPhase3Overview()

    return () => {
      cancelled = true
    }
  }, [refreshPhase3Overview])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const oauth = params.get('oauth')
    if (!oauth) return

    if (oauth === 'success') {
      const pk = params.get('provider')
      setOauthFlash({
        kind: 'success',
        message: `Connected ${pk ?? 'integration'}. Vault sealed and Dynamic Hub updated — run connector test to activate when ready.`,
      })
      void reloadConnectors()
        .then(setRows)
        .catch(() => null)
      void refreshPhase3Overview()
    } else {
      const reason = params.get('reason')
      setOauthFlash({
        kind: 'error',
        message: reason ? `OAuth error: ${reason}` : 'OAuth flow failed.',
      })
    }

    const url = new URL(window.location.href)
    url.searchParams.delete('oauth')
    url.searchParams.delete('provider')
    url.searchParams.delete('reason')
    window.history.replaceState({}, '', `${url.pathname}${url.search}`)
  }, [refreshPhase3Overview])

  const mutateRow = useCallback(async () => {
    setRows(await reloadConnectors())
  }, [])

  const handleCreate: MouseEventHandler<HTMLButtonElement> = async () => {
    setSaving(true)
    setLoadErr(null)
    try {
      let secretsParsed: Record<string, unknown> | undefined
      const trimmedSecrets = secretBlob.trim()
      if (trimmedSecrets) {
        secretsParsed = JSON.parse(trimmedSecrets) as Record<string, unknown>
      } else if (authType !== 'none') {
        throw new Error('Secrets JSON required whenever auth differs from none.')
      }

      let manifestPayload: Record<string, unknown>
      const trimmedManifest = manifest.trim()
      if (trimmedManifest) {
        manifestPayload = JSON.parse(trimmedManifest) as Record<string, unknown>
      } else {
        manifestPayload = {
          tools: [
            {
              name: 'invoke',
              path: '/',
              method: 'POST',
              description: 'Proxy JSON payloads to upstream root.',
            },
          ],
        }
      }

      await hivePostJson<DynamicConnectorPayload>('connectors/dynamic', {
        slug,
        display_name: displayName,
        base_url: baseUrl.trim() ? baseUrl : null,
        auth_type: authType,
        secrets: secretsParsed,
        mcp_manifest: manifestPayload,
        allowed_manager_slugs: [],
      })
      setSlug('')
      setDisplayName('')
      setBaseUrl('')
      setManifest('')
      setSecretBlob('')
      setRows(await reloadConnectors())
      await refreshPhase3Overview()
    } catch (err: unknown) {
      setLoadErr(err instanceof HiveApiError ? err.message : err instanceof Error ? err.message : 'Create connector failed.')
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(conn: DynamicConnectorPayload) {
    if (conn.is_builtin) return
    try {
      await hivePatchJson<DynamicConnectorPayload>(`connectors/dynamic/${encodeURIComponent(conn.id)}`, {
        is_active: !conn.is_active,
      })
      setRows(await reloadConnectors())
      await refreshPhase3Overview()
    } catch {
      setLoadErr('Unable to mutate connector.')
    }
  }

  async function handleTest(connId: string) {
    setTestingConnectorId(connId)
    try {
      await hivePostJson<Record<string, unknown>>(`connectors/dynamic/${encodeURIComponent(connId)}/test`, {})
      await mutateRow()
      setRows(await reloadConnectors())
      await refreshPhase3Overview()
    } finally {
      setTestingConnectorId(null)
    }
  }

  async function handleRemove(conn: DynamicConnectorPayload) {
    if (conn.is_builtin) return
    const accepted = typeof window !== 'undefined' ? window.confirm(`Delete connector ${conn.slug}?`) : false
    if (!accepted) return
    await hiveDelete(`connectors/dynamic/${encodeURIComponent(conn.id)}`)
    setRows(await reloadConnectors())
    await refreshPhase3Overview()
  }

  const managerChip = (mgrs: string[]) => (mgrs.length ? mgrs.join(', ') : 'All lanes')

  const refreshObsidianStatus = useCallback(async () => {
    try {
      const snap = await hiveGet<ObsidianVaultStatusPayload>('connectors/phase3/obsidian/status')
      setObsidianStatus(snap)
      setObsidianErr(null)
    } catch (err: unknown) {
      setObsidianErr(err instanceof HiveApiError ? err.message : 'Obsidian telemetry unavailable.')
    }
  }, [])

  function applyPhase3Template(tpl: Phase3TemplatePublic) {
    setSlug(tpl.suggested_slug)
    setDisplayName(tpl.title)
    setBaseUrl(tpl.base_url ?? '')
    setAuthType(tpl.auth_type as (typeof AUTH_OPTIONS)[number])
    setManifest(buildManifestJsonFromTemplate(tpl.tools))
    setSecretBlob('')
    setLoadErr(null)
  }

  async function provisionFromPhase3Template(tpl: Phase3TemplatePublic) {
    setInstantiatingId(tpl.template_id)
    setLoadErr(null)
    try {
      await hivePostJson<DynamicConnectorPayload>('connectors/phase3/instantiate', {
        template_id: tpl.template_id,
        slug: tpl.suggested_slug,
        display_name: tpl.title,
      })
      setRows(await reloadConnectors())
      await refreshPhase3Overview()
    } catch (err: unknown) {
      const msg =
        err instanceof HiveApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Instantiate failed — seal OAuth/API secrets when auth is not none.'
      setLoadErr(msg)
    } finally {
      setInstantiatingId(null)
    }
  }

  async function handleObsidianSyncNow() {
    setObsidianBusy(true)
    setObsidianErr(null)
    try {
      await hivePostJson<Record<string, unknown>>('connectors/phase3/obsidian/sync', {})
      await refreshObsidianStatus()
    } catch (err: unknown) {
      setObsidianErr(err instanceof HiveApiError ? err.message : 'Vault sync failed.')
    } finally {
      setObsidianBusy(false)
    }
  }

  const phase3Coverage = phase3Slice ? phase3ProvisionCoverage(phase3Slice.templates, rows.map((r) => r.slug)) : []

  const selectedPhase3Tpl =
    phase3Slice?.templates.find((t) => t.template_id === selectedTemplateId) ?? null
  const overviewMatchRow = phase3Overview?.templates.find((t) => t.template_id === selectedTemplateId)
  const inspectorHubRow =
    overviewMatchRow?.hub_row ??
    (selectedPhase3Tpl
      ? rows.find((r) => r.slug.trim().toLowerCase() === selectedPhase3Tpl.suggested_slug.trim().toLowerCase()) ?? null
      : null)

  const pulse = phase3Overview
    ? phase3OverviewCoverageScore(phase3Overview.templates)
    : {
        provisioned: phase3Coverage.filter((c) => c.provisioned).length,
        active: 0,
        total: phase3Coverage.length,
      }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 py-10 text-zinc-200">
      <header className="space-y-2">
        <p className="font-[family-name:var(--font-poppins)] text-xs uppercase tracking-[0.42em] text-cyan">
          Phase 3 · Communication &amp; Knowledge · MCP Hub
        </p>
        <div className="flex items-center gap-2">
          <h1 className="font-[family-name:var(--font-poppins)] text-3xl font-bold tracking-tight text-pollen md:text-[2.125rem]">
            Dynamic Connector Hub
          </h1>
          <InfoHint
            title="Dynamic Connector Hub"
            description="Connector operations hub for auth setup, marketplace wiring, and upstream integration testing."
            options={['Connector create/update', 'Vault + OAuth', 'Probe/test controls', 'Enable/disable connectors']}
          />
        </div>
        <p className="font-[family-name:var(--font-poppins)] text-base text-zinc-400">
          Persist manifests in Postgres, seal secrets via hive Fernet blobs, hydrate Redis manifests (TTL 300s), rate-limit outbound
          calls per slug, trip breakers automatically, then surface tools to Ballroom orchestration queues. Phase 3 adds curated Gmail,
          Outlook, Calendar, GitHub, GitLab, Slack, Telegram, Discord, Notion, and Stripe manifests — plus Obsidian vault embeddings into
          HiveMind when enabled.
        </p>
        <div className="flex flex-wrap gap-3 pt-2 font-[family-name:var(--font-poppins)] text-sm">
          <Link
            href="/external-projects"
            className="inline-flex items-center gap-2 rounded-full border border-cyan/35 px-4 py-2 text-cyan hover:bg-cyan/10"
          >
            <ExternalLink className="h-4 w-4" aria-hidden />
            External projects · MCP / REST / WS
          </Link>
          <Link href="/hive-mind" className="inline-flex items-center gap-2 rounded-full border border-pollen/35 px-4 py-2 text-pollen hover:bg-pollen/10">
            <Sparkles className="h-4 w-4" aria-hidden />
            HiveMind recall
          </Link>
        </div>
      </header>

      {loadErr ? (
        <div className="rounded-2xl border border-danger/35 bg-black/65 px-4 py-3 text-sm text-danger" role="status">
          {loadErr}{' '}
          <button
            type="button"
            className="ml-3 font-semibold underline"
            onClick={() =>
              reloadConnectors()
                .then(setRows)
                .then(() => refreshPhase3Overview())
                .catch(() => setLoadErr('Retry failed'))
            }
          >
            Retry
          </button>
        </div>
      ) : null}

      {oauthFlash ? (
        <div
          className={
            oauthFlash.kind === 'success'
              ? 'rounded-2xl border border-[#00FF88]/35 bg-black/65 px-4 py-3 text-sm text-[#00FF88]'
              : 'rounded-2xl border border-danger/35 bg-black/65 px-4 py-3 text-sm text-danger'
          }
          role="status"
        >
          {oauthFlash.message}{' '}
          <button type="button" className="ml-2 font-semibold underline" onClick={() => setOauthFlash(null)}>
            Dismiss
          </button>
        </div>
      ) : null}

      <ConnectorsVaultPanel />

      <ConnectorsOAuthConsentRail catalog={oauthCatalog} />

      {phase3Slice ? (
        <section className="space-y-5 rounded-[28px] border border-[#1b1f4a]/90 bg-black/58 p-6 shadow-[0_35px_90px_-50px_rgb(0_255_255/0.22)]">
          <header className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#EEEEFF]">
                Phase 3 templates · Communication &amp; Knowledge
              </h2>
              <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
                {phase3Slice.template_count} curated MCP manifests — use{' '}
                <span className="text-[#B7F6FF]">hosted OAuth connect</span> above for Gmail / Outlook / Calendar / GitHub / Notion / Stripe,
                prefill the forge below, or provision directly into the hub (manual secrets JSON still supported).
              </p>
            </div>
            <p className="font-mono text-xs text-zinc-500">
              Coverage · {phase3Coverage.filter((c) => c.provisioned).length}/{phase3Coverage.length} defaults detected
            </p>
          </header>

          {overviewErr ? (
            <p className="rounded-xl border border-magenta/35 bg-magenta/10 px-3 py-2 text-xs text-magenta" role="status">
              {overviewErr}
            </p>
          ) : null}

          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-cyan/25 bg-black/72 px-4 py-3 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.08)]">
              <p className="text-[11px] uppercase tracking-[0.24em] text-zinc-500">Templates rostered</p>
              <p className="font-[family-name:var(--font-poppins)] text-2xl font-bold text-cyan">
                {pulse.provisioned}/{pulse.total}
              </p>
            </div>
            <div className="rounded-2xl border border-[#00FF88]/25 bg-black/72 px-4 py-3 shadow-[inset_0_0_0_1px_rgb(0_255_136/0.08)]">
              <p className="text-[11px] uppercase tracking-[0.24em] text-zinc-500">Active slugs</p>
              <p className="font-[family-name:var(--font-poppins)] text-2xl font-bold text-[#00FF88]">{pulse.active}</p>
            </div>
            <button
              type="button"
              disabled={overviewBusy}
              onClick={() => void refreshPhase3Overview()}
              className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-2xl border border-pollen/35 px-4 py-3 font-[family-name:var(--font-poppins)] text-xs font-semibold text-pollen hover:bg-pollen/10 disabled:opacity-40 touch-manipulation"
            >
              {overviewBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : <RefreshCw className="h-4 w-4" aria-hidden />}
              Refresh integration pulse
            </button>
          </div>

          <div className="xl:grid xl:grid-cols-[minmax(0,1fr)_340px] xl:gap-8 xl:items-start">
          <div className="space-y-3">
            {orderedPhase3Categories(phase3Slice.grouped).map((category) => {
              const tpls = phase3Slice.grouped[category] ?? []
              if (!tpls.length) {
                return null
              }
              const open = phase3OpenCategory === category
              return (
                <div key={category} className="rounded-2xl border border-[#1e2348] bg-black/76">
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#EEEEFF] md:px-5"
                    onClick={() => setPhase3OpenCategory(open ? null : category)}
                    aria-expanded={open}
                  >
                    <span className="flex items-center gap-2">
                      {open ? <ChevronDown className="h-4 w-4 text-cyan" aria-hidden /> : <ChevronRight className="h-4 w-4 text-zinc-500" aria-hidden />}
                      {phase3CategoryLabel(category)}
                      <span className="rounded-full border border-zinc-700 px-2 py-[2px] text-[11px] font-normal uppercase tracking-[0.18em] text-zinc-500">
                        {tpls.length}
                      </span>
                    </span>
                  </button>
                  {open ? (
                    <div className="grid gap-3 border-t border-[#1e2348] p-4 md:grid-cols-2 md:p-5">
                      {tpls.map((tpl) => {
                        const covered = phase3Coverage.find((row) => row.template_id === tpl.template_id)?.provisioned
                        return (
                          <article
                            key={tpl.template_id}
                            className="flex flex-col gap-3 rounded-2xl border border-[#252a55] bg-black/80 p-4 shadow-[inset_0_0_0_1px_rgb(255_184_0/0.06)]"
                          >
                            <header className="space-y-1">
                              <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-cyan">{tpl.template_id}</p>
                              <h3 className="font-[family-name:var(--font-poppins)] text-base font-semibold text-pollen">{tpl.title}</h3>
                              <p className="font-[family-name:var(--font-poppins)] text-xs leading-relaxed text-zinc-400">{tpl.summary}</p>
                            </header>
                            <dl className="grid gap-2 text-xs font-[family-name:var(--font-poppins)] text-zinc-500 md:grid-cols-2">
                              <div>
                                <dt className="uppercase tracking-[0.32em]">Auth</dt>
                                <dd className="text-[#D7D9FF]">{tpl.auth_type}</dd>
                              </div>
                              <div>
                                <dt className="uppercase tracking-[0.32em]">Tools</dt>
                                <dd className="text-[#D7D9FF]">{tpl.tool_count}</dd>
                              </div>
                              <div className="md:col-span-2">
                                <dt className="uppercase tracking-[0.32em]">Status</dt>
                                <dd className={covered ? 'text-[#00FF88]' : 'text-magenta'}>{covered ? 'Slug detected in roster' : 'Not provisioned yet'}</dd>
                              </div>
                            </dl>
                            <div className="flex flex-wrap gap-2">
                              <button
                                type="button"
                                className="inline-flex min-h-[40px] w-full basis-full items-center justify-center rounded-xl border border-white/14 px-3 py-2 font-[family-name:var(--font-poppins)] text-xs font-semibold text-[#F4F4FF] hover:bg-white/6 touch-manipulation sm:w-auto sm:flex-1 sm:basis-auto"
                                onClick={() => setSelectedTemplateId(tpl.template_id)}
                              >
                                Power panel
                              </button>
                              <a
                                href={tpl.documentation_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-cyan/35 px-3 py-2 font-[family-name:var(--font-poppins)] text-xs font-semibold text-cyan hover:bg-cyan/10 min-[420px]:flex-none"
                              >
                                Docs
                                <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                              </a>
                              <button
                                type="button"
                                className="inline-flex flex-1 items-center justify-center rounded-xl border border-pollen/35 px-3 py-2 font-[family-name:var(--font-poppins)] text-xs font-semibold text-pollen hover:bg-pollen/10 min-[420px]:flex-none"
                                onClick={() => applyPhase3Template(tpl)}
                              >
                                Prefill forge
                              </button>
                              <button
                                type="button"
                                disabled={instantiatingId === tpl.template_id}
                                className="inline-flex flex-1 items-center justify-center rounded-xl border border-[#00FF88]/35 px-3 py-2 font-[family-name:var(--font-poppins)] text-xs font-semibold text-[#00FF88] hover:bg-[#00FF88]/10 disabled:opacity-40 min-[420px]:flex-none"
                                onClick={() => void provisionFromPhase3Template(tpl)}
                              >
                                {instantiatingId === tpl.template_id ? (
                                  <>
                                    <Loader2Icon className="mr-2 h-3.5 w-3.5 animate-spin" aria-hidden />
                                    Sealing…
                                  </>
                                ) : (
                                  'Provision hub row'
                                )}
                              </button>
                            </div>
                          </article>
                        )
                      })}
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>

          <div className="relative hidden xl:block">
            {selectedPhase3Tpl ? (
              <Phase3TemplateInspector
                layout="rail"
                tpl={selectedPhase3Tpl}
                hubRow={inspectorHubRow}
                onClose={() => setSelectedTemplateId(null)}
                onPrefill={applyPhase3Template}
                onProvision={(tplInst) => void provisionFromPhase3Template(tplInst)}
                onTestHub={(id) => void handleTest(id)}
                provisioning={instantiatingId === selectedPhase3Tpl.template_id}
                testingId={testingConnectorId}
              />
            ) : (
              <div className="sticky top-28 space-y-3 rounded-[26px] border border-[#252a55] bg-black/76 p-5 font-[family-name:var(--font-poppins)] text-sm text-zinc-400">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-pollen">Desktop · Power panel</p>
                <p>
                  Pick any Phase 3 vendor card and open <span className="text-[#EEEEFF]">Power panel</span> to browse MCP tools, sync forge
                  prefill, provision instantly, and run upstream probes — sidebar stays visible for operators jumping across HiveMind or External
                  Projects.
                </p>
                <p className="text-xs text-zinc-500">Phones &amp; tablets surface the same inspector as a bottom sheet aligned with thumb navigation.</p>
              </div>
            )}
          </div>
          </div>

          {selectedPhase3Tpl ? (
            <>
              <button
                type="button"
                className="fixed inset-0 z-[55] bg-black/65 xl:hidden"
                aria-label="Close template inspector"
                onClick={() => setSelectedTemplateId(null)}
              />
              <Phase3TemplateInspector
                layout="sheet"
                tpl={selectedPhase3Tpl}
                hubRow={inspectorHubRow}
                onClose={() => setSelectedTemplateId(null)}
                onPrefill={applyPhase3Template}
                onProvision={(tplInst) => void provisionFromPhase3Template(tplInst)}
                onTestHub={(id) => void handleTest(id)}
                provisioning={instantiatingId === selectedPhase3Tpl.template_id}
                testingId={testingConnectorId}
              />
            </>
          ) : null}
        </section>
      ) : null}

      <section className="rounded-[26px] border border-[#1c2045] bg-black/72 p-5 md:p-6">
        <header className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#EEEEFF]">Obsidian vault → HiveMind</h2>
            <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
              Markdown mirror under <span className="font-mono text-cyan">HIVE_MIND_VAULT_ROOT</span> (Compose:{' '}
              <span className="font-mono text-xs">/hive-mind/vault</span>) embeds into Chroma when watch mode is on — manual sync still
              respects HiveMind flags.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void refreshObsidianStatus()}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-cyan/40 px-4 py-2 font-[family-name:var(--font-poppins)] text-xs font-semibold text-cyan hover:bg-cyan/10"
          >
            <RefreshCw className="h-4 w-4" aria-hidden />
            Refresh telemetry
          </button>
        </header>

        {obsidianErr ? (
          <p className="mb-3 rounded-xl border border-danger/35 bg-black/65 px-3 py-2 text-xs text-danger" role="status">
            {obsidianErr}
          </p>
        ) : null}

        {obsidianStatus ? (
          <dl className="grid gap-4 font-[family-name:var(--font-poppins)] text-sm text-zinc-400 md:grid-cols-3">
            <div>
              <dt className="text-xs uppercase tracking-[0.32em] text-zinc-500">Watch mode</dt>
              <dd className="text-[#D7D9FF]">{obsidianStatus.enabled ? 'enabled' : 'disabled'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.32em] text-zinc-500">Poll cadence</dt>
              <dd className="text-[#D7D9FF]">{obsidianStatus.poll_interval_sec}s</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.32em] text-zinc-500">Max files / sweep</dt>
              <dd className="text-[#D7D9FF]">{obsidianStatus.max_files_per_sync}</dd>
            </div>
            <div className="md:col-span-3">
              <dt className="text-xs uppercase tracking-[0.32em] text-zinc-500">Last snapshot</dt>
              <dd className="break-all font-mono text-xs text-[#B7F6FF]">{JSON.stringify(obsidianStatus.snapshot)}</dd>
            </div>
          </dl>
        ) : (
          <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-500">Loading vault telemetry…</p>
        )}

        <div className="mt-5">
          <button
            type="button"
            disabled={obsidianBusy}
            onClick={() => void handleObsidianSyncNow()}
            className="inline-flex items-center gap-2 rounded-2xl border border-pollen/70 px-6 py-[10px] font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen hover:bg-pollen/10 disabled:opacity-40"
          >
            {obsidianBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : <RefreshCw className="h-4 w-4" aria-hidden />}
            Force vault embedding pass
          </button>
        </div>
      </section>

      <section className="rounded-[28px] border border-[#1b1f4a]/90 bg-black/58 p-6 shadow-[0_35px_90px_-50px_rgb(255_184_0/0.75)]">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-pollen/30 bg-black/68 text-pollen">
              <Zap className="h-5 w-5" aria-hidden />
            </div>
            <div>
          <div className="flex items-center gap-2">
            <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#EEEEFF]">Add New Connector</h2>
            <InfoHint
              title="Add New Connector"
              description="Form for creating a custom dynamic connector."
              options={['Slug', 'Base URL', 'Auth type', 'MCP manifest JSON', 'Encrypted secrets blob']}
            />
          </div>
              <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
                ciphertext never echoes in JSON — only MCP manifest metadata survives.
              </p>
            </div>
          </div>

          <Link href="/settings/security" className="font-[family-name:var(--font-poppins)] text-[13px] text-cyan underline decoration-cyan/40">
            Security reference
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-sm font-medium text-[#BEBED6]">
            <span className="inline-flex items-center gap-2">
              <span>Slug · DNS-safe</span>
              <InfoHint
                title="Connector slug"
                description="Stable connector identifier used by routing and internal lookups."
                options={['Unique value', 'Lowercase safe', 'No spaces']}
              />
            </span>
            <input
              type="text"
              value={slug}
              placeholder="stripe_pro"
              onChange={(evt) => setSlug(evt.target.value)}
              className="rounded-xl border border-[#1e2348] bg-black/76 px-3 py-3 font-mono text-sm text-[#EEEEFF]"
            />
          </label>
          <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-sm font-medium text-[#BEBED6]">
            Display name
            <input
              type="text"
              value={displayName}
              placeholder="Stripe Pro · Billing"
              onChange={(evt) => setDisplayName(evt.target.value)}
              className="rounded-xl border border-[#1e2348] bg-black/76 px-3 py-3 text-sm text-[#EEEEFF]"
            />
          </label>
          <label className="flex flex-col gap-2 md:col-span-2 font-[family-name:var(--font-poppins)] text-sm font-medium text-[#BEBED6]">
            Base URL · HTTPS upstream
            <input
              type="url"
              value={baseUrl}
              placeholder="https://integration.example/api"
              onChange={(evt) => setBaseUrl(evt.target.value)}
              className="rounded-xl border border-[#1e2348] bg-black/76 px-3 py-3 font-mono text-sm text-[#EEEEFF]"
            />
          </label>
          <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-sm font-medium text-[#BEBED6]">
            <span className="inline-flex items-center gap-2">
              <span>Auth type</span>
              <InfoHint
                title="Auth type"
                description="Defines how outbound connector requests are signed/authenticated."
                options={['none', 'api_key', 'bearer_token', 'oauth2']}
              />
            </span>
            <select
              value={authType}
              onChange={(evt) => setAuthType(evt.target.value as (typeof AUTH_OPTIONS)[number])}
              className="rounded-xl border border-[#1e2348] bg-black/76 px-3 py-3 text-sm text-[#EEEEFF]"
            >
              {AUTH_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt.replace('_', ' ')}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-2 md:col-span-2 font-[family-name:var(--font-poppins)] text-sm font-medium text-[#BEBED6]">
            MCP manifest · JSON ({`tools[]`})
            <textarea
              value={manifest}
              rows={9}
              onChange={(evt) => setManifest(evt.target.value)}
              placeholder={'{\n  "tools": [{ "name": "lookup", "path": "/", "method": "POST", "description": "Proxy" }]\n}'}
              className="rounded-xl border border-[#1e2348] bg-black/85 px-3 py-3 font-mono text-xs text-[#B7F6FF]"
            />
          </label>
          <label className="flex flex-col gap-2 md:col-span-2 font-[family-name:var(--font-poppins)] text-sm font-medium text-[#BEBED6]">
            Secrets blob · encrypted once (never returned)
            <textarea
              rows={5}
              value={secretBlob}
              onChange={(evt) => setSecretBlob(evt.target.value)}
              placeholder='Example: {"api_key":"..."}'
              className="rounded-xl border border-[#1e2348] bg-black/85 px-3 py-3 font-mono text-xs text-[#FFBFD6]"
            />
          </label>
        </div>

        <div className="mt-6">
          <button
            type="button"
            disabled={saving || !slug.trim() || !displayName.trim()}
            className={cn(
              'inline-flex items-center gap-2 rounded-2xl border px-8 py-[11px] font-[family-name:var(--font-poppins)] text-sm font-semibold transition shadow-[inset_0_0_0_1px_rgb(255_184_0/0.42)]',
              'border-pollen/70 bg-pollen text-black hover:brightness-105 disabled:opacity-40',
            )}
            onClick={handleCreate}
          >
            {saving ? (
              <>
                <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
                Sealing…
              </>
            ) : (
              '+ Add New Connector'
            )}
          </button>
        </div>
      </section>

      <section className="space-y-6">
        <div className="flex flex-wrap items-center gap-4">
          <h2 className="font-[family-name:var(--font-poppins)] text-xl font-semibold text-[#EEEEFF]">Combined roster</h2>
          <div className="h-px flex-1 min-w-[80px] rounded-full bg-gradient-to-r from-cyan via-pollen to-magenta opacity-60" aria-hidden />
        </div>

        {!loadErr && !rows.length ? (
          <div
            className="rounded-[26px] border border-dashed border-cyan/25 bg-black/55 px-5 py-8 text-center md:text-left"
            role="status"
          >
            <p className="font-[family-name:var(--font-poppins)] text-base font-semibold text-[#EEEEFF]">No dynamic hub rows yet</p>
            <p className="mt-2 font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
              Provision a Phase 3 template above or seal vault credentials first — the roster fills after manifests sync from the hive API.
            </p>
          </div>
        ) : null}

        <div className="grid gap-4">
          {rows.map((conn) => (
            <article key={conn.id} className="rounded-[26px] border border-[#1c2045] bg-black/72 p-5">
              <header className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.25em] text-cyan">{conn.slug}</p>
                  <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-pollen">{conn.display_name}</h3>
                  <p className="break-all font-mono text-xs text-zinc-500">{conn.base_url ?? '(unset base)'}</p>
                </div>
                <Badge builtin={conn.is_builtin} active={conn.is_active} />
              </header>

              <dl className="mt-5 grid gap-4 text-sm font-[family-name:var(--font-poppins)] text-zinc-400 md:grid-cols-3">
                <div>
                  <dt className="text-xs uppercase tracking-[0.32em] text-zinc-500">Managers</dt>
                  <dd className="text-[#D7D9FF]">{managerChip(conn.allowed_manager_slugs)}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.32em] text-zinc-500">Last test</dt>
                  <dd className="text-[#D7D9FF]">{conn.last_tested_at ?? 'never probed'}</dd>
                </div>
              </dl>

              <footer className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  className="rounded-xl border border-cyan/40 px-5 py-[9px] font-[family-name:var(--font-poppins)] text-sm font-semibold text-cyan hover:bg-cyan/10"
                  onClick={() => void handleTest(conn.id)}
                >
                  Test Connection · 2500 ms SLA
                </button>
                <button
                  type="button"
                  disabled={conn.is_builtin}
                  className={cn(
                    'rounded-xl border px-5 py-[9px] font-[family-name:var(--font-poppins)] text-sm font-semibold hover:bg-white/10',
                    conn.is_builtin ? 'opacity-35' : 'border-pollen text-pollen',
                  )}
                  onClick={() => void toggleActive(conn)}
                >
                  {conn.is_active ? 'Deactivate manually' : 'Activate manually'}
                </button>
                {!conn.is_builtin ? (
                  <button
                    type="button"
                    className="rounded-xl border border-danger/35 px-5 py-[9px] font-[family-name:var(--font-poppins)] text-sm font-semibold text-danger hover:bg-danger/15"
                    onClick={() => void handleRemove(conn)}
                  >
                    Remove
                  </button>
                ) : (
                  <p className="text-xs font-mono text-zinc-500">seeded via alembic 0014_dynamic_connectors</p>
                )}
              </footer>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}
