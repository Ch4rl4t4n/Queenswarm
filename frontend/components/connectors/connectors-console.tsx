'use client'

import Link from 'next/link'
import {
  ExternalLink,
  Loader2Icon,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import type { MouseEventHandler } from 'react'
import { useCallback, useEffect, useState } from 'react'

import { HiveRefreshButton } from '@/components/hive/hive-refresh-button'
import { QsSelect } from '@/components/ui/qs-select'
import { ConnectorsOAuthConsentRail } from '@/components/connectors/connectors-oauth-consent-rail'
import { ConnectorsVaultPanel } from '@/components/connectors/connectors-vault-panel'
import { Phase3TemplatesPanel } from '@/components/connectors/phase3-templates-panel'
import type { Phase3TemplateConfig } from '@/components/connectors/phase3-templates-grid'
import { InfoHint } from '@/components/hive/info-hint'
import { ListPaginator, ViewportBoundedPanel } from '@/components/ui/list-paginator'
import { V4Badge, V4Card, V4CardHeader } from '@/components/ui/v4'
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
  phase3ProvisionCoverage,
  type ObsidianVaultStatusPayload,
  type Phase3CatalogSlice,
  type Phase3TemplatePublic,
} from '@/lib/connectors-phase3'
import { extractOAuthConsentCatalog, type OAuthConsentCatalogSlice } from '@/lib/connectors-oauth-catalog'
import { useGridTwoRowPageSize } from '@/lib/use-grid-two-row-page-size'
import { usePaginatedSlice } from '@/lib/use-paginated-slice'
import type { IntegrationsHubSection } from '@/lib/integrations-hub-routes'
import { cn } from '@/lib/utils'

interface ConnectorsEnvelope {
  items: DynamicConnectorPayload[]
  builtins: DynamicConnectorPayload[]
  customs: DynamicConnectorPayload[]
}

const AUTH_OPTIONS = ['none', 'api_key', 'bearer_token', 'oauth2'] as const

function ConnectorBadges({ builtin, active }: { builtin: boolean; active: boolean }) {
  return (
    <div className="flex flex-wrap gap-2">
      <V4Badge tone={builtin ? 'gold' : 'info'}>{builtin ? 'Built-in' : 'Custom'}</V4Badge>
      <V4Badge tone={active ? 'ok' : 'err'}>{active ? 'Active' : 'Inactive'}</V4Badge>
    </div>
  )
}

async function reloadConnectors(): Promise<DynamicConnectorPayload[]> {
  const body = await hiveGet<ConnectorsEnvelope>('connectors/dynamic')
  return body.items
}

interface ConnectorsConsoleProps {
  embedded?: boolean
  /** When set (Integrations hub sub-nav), render only this block. */
  hubSection?: Exclude<IntegrationsHubSection, 'tools'>
}

function showHubBlock(active: Exclude<IntegrationsHubSection, 'tools'>, hubSection?: Exclude<IntegrationsHubSection, 'tools'>): boolean {
  return !hubSection || hubSection === active
}

export function ConnectorsConsole({ embedded = false, hubSection }: ConnectorsConsoleProps) {
  const [rows, setRows] = useState<DynamicConnectorPayload[]>([])
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [phase3Slice, setPhase3Slice] = useState<Phase3CatalogSlice | null>(null)
  const [oauthCatalog, setOauthCatalog] = useState<OAuthConsentCatalogSlice | null>(null)
  const [oauthFlash, setOauthFlash] = useState<{ kind: 'success' | 'error'; message: string } | null>(null)
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

  const rosterPageSize = useGridTwoRowPageSize({ columns: 2 })
  const rosterPagination = usePaginatedSlice(rows, rosterPageSize, `${rows.length}|${rosterPageSize}`)

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
        message: `Connected ${pk ?? 'integration'}. Vault sealed — connector active and super routers sync when ready.`,
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
    try {
      await hivePostJson<Record<string, unknown>>(`connectors/dynamic/${encodeURIComponent(connId)}/test`, {})
      await mutateRow()
      setRows(await reloadConnectors())
      await refreshPhase3Overview()
    } catch {
      setLoadErr('Connector test failed.')
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

  function applyPhase3Template(tpl: Phase3TemplatePublic, config?: Phase3TemplateConfig) {
    const slugValue = config?.slug.trim() || tpl.suggested_slug
    const displayValue = config?.displayName.trim() || tpl.title
    const baseValue = config?.baseUrl.trim() || tpl.base_url || ''
    setSlug(slugValue)
    setDisplayName(displayValue)
    setBaseUrl(baseValue)
    setAuthType(tpl.auth_type as (typeof AUTH_OPTIONS)[number])
    setManifest(buildManifestJsonFromTemplate(tpl.tools))
    setSecretBlob('')
    setLoadErr(null)
  }

  async function provisionFromPhase3Template(tpl: Phase3TemplatePublic, config?: Phase3TemplateConfig) {
    const slugValue = config?.slug.trim() || tpl.suggested_slug
    const displayValue = config?.displayName.trim() || tpl.title
    const baseValue = config?.baseUrl.trim() || tpl.base_url || ''
    setInstantiatingId(tpl.template_id)
    setLoadErr(null)
    try {
      const created = await hivePostJson<DynamicConnectorPayload>('connectors/phase3/instantiate', {
        template_id: tpl.template_id,
        slug: slugValue,
        display_name: displayValue,
      })
      if (baseValue && baseValue !== (tpl.base_url ?? '')) {
        await hivePatchJson<DynamicConnectorPayload>(`connectors/dynamic/${created.id}`, {
          base_url: baseValue,
        })
      }
      setRows(await reloadConnectors())
      await refreshPhase3Overview()
      applyPhase3Template(tpl, config)
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

  const pulse = phase3Overview
    ? phase3OverviewCoverageScore(phase3Overview.templates)
    : {
        provisioned: phase3Coverage.filter((c) => c.provisioned).length,
        active: 0,
        total: phase3Coverage.length,
      }

  const shell = (
    <>
      {loadErr && showHubBlock('roster', hubSection) ? (
        <div className="rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-4 py-3 text-sm text-danger" role="status">
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

      {oauthFlash && showHubBlock('oauth', hubSection) ? (
        <div
          className={
            oauthFlash.kind === 'success'
              ? 'rounded-xl border border-(--qs-green)/35 bg-(--qs-green)/10 px-4 py-3 text-sm text-(--qs-green)'
              : 'rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-4 py-3 text-sm text-danger'
          }
          role="status"
        >
          {oauthFlash.message}{' '}
          <button type="button" className="ml-2 font-semibold underline" onClick={() => setOauthFlash(null)}>
            Dismiss
          </button>
        </div>
      ) : null}

      {showHubBlock('vault', hubSection) ? <ConnectorsVaultPanel /> : null}

      {showHubBlock('oauth', hubSection) ? <ConnectorsOAuthConsentRail catalog={oauthCatalog} /> : null}

      {showHubBlock('templates', hubSection) && phase3Slice ? (
        <Phase3TemplatesPanel
          embedded
          phase3Slice={phase3Slice}
          connectorRows={rows}
          instantiatingId={instantiatingId}
          overviewBusy={overviewBusy}
          overviewErr={overviewErr}
          pulse={pulse}
          onRefresh={() => void refreshPhase3Overview()}
          onPrefill={applyPhase3Template}
          onProvision={(tpl, config) => void provisionFromPhase3Template(tpl, config)}
        />
      ) : null}

      {showHubBlock('templates', hubSection) && !phase3Slice ? (
        <p className="text-sm text-(--qs-text-3)">Loading Phase 3 template catalog…</p>
      ) : null}

      {showHubBlock('obsidian', hubSection) ? (
      <V4Card>
        <V4CardHeader
          title="Obsidian vault → HiveMind"
          description={
            <>
              Markdown mirror under <span className="font-mono text-pollen">HIVE_MIND_VAULT_ROOT</span> (Compose:{' '}
              <span className="font-mono text-xs">/hive-mind/vault</span>) embeds into Chroma when watch mode is on.
            </>
          }
          actions={
            <HiveRefreshButton label="Refresh telemetry" onClick={() => void refreshObsidianStatus()} />
          }
        />

        {obsidianErr ? (
          <p className="mb-3 rounded-xl border border-danger/35 bg-black/65 px-3 py-2 text-xs text-danger" role="status">
            {obsidianErr}
          </p>
        ) : null}

        {obsidianStatus ? (
          <dl className="grid gap-4 text-sm text-(--qs-text-2) md:grid-cols-3">
            <div>
              <dt className="v4-field-label">Watch mode</dt>
              <dd className="text-(--qs-text)">{obsidianStatus.enabled ? 'enabled' : 'disabled'}</dd>
            </div>
            <div>
              <dt className="v4-field-label">Poll cadence</dt>
              <dd className="text-(--qs-text)">{obsidianStatus.poll_interval_sec}s</dd>
            </div>
            <div>
              <dt className="v4-field-label">Max files / sweep</dt>
              <dd className="text-(--qs-text)">{obsidianStatus.max_files_per_sync}</dd>
            </div>
            <div className="md:col-span-3">
              <dt className="v4-field-label">Last snapshot</dt>
              <dd className="break-all font-mono text-xs text-(--qs-text-3)">{JSON.stringify(obsidianStatus.snapshot)}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-(--qs-text-3)">Loading vault telemetry…</p>
        )}

        <div className="mt-5">
          <button
            type="button"
            disabled={obsidianBusy}
            onClick={() => void handleObsidianSyncNow()}
            className="qs-btn qs-btn--primary qs-btn--sm gap-2 disabled:opacity-40"
          >
            {obsidianBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : <RefreshCw className="h-4 w-4" aria-hidden />}
            Force vault embedding pass
          </button>
        </div>
      </V4Card>
      ) : null}

      {showHubBlock('roster', hubSection) ? (
      <>
      <V4Card glow>
        <V4CardHeader
          title="Add new connector"
          description="Ciphertext never echoes in JSON — only MCP manifest metadata survives."
          actions={
            <Link href="/settings/security" className="qs-btn qs-btn--ghost qs-btn--sm">
              Security reference
            </Link>
          }
        />

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
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
              placeholder="billing_provider"
              onChange={(evt) => setSlug(evt.target.value)}
              className="qs-input font-mono"
            />
          </label>
          <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
            Display name
            <input
              type="text"
              value={displayName}
              placeholder="Billing provider"
              onChange={(evt) => setDisplayName(evt.target.value)}
              className="qs-input"
            />
          </label>
          <label className="flex flex-col gap-2 md:col-span-2 text-sm font-medium text-(--qs-text-2)">
            Base URL · HTTPS upstream
            <input
              type="url"
              value={baseUrl}
              placeholder="https://integration.example/api"
              onChange={(evt) => setBaseUrl(evt.target.value)}
              className="qs-input font-mono"
            />
          </label>
          <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
            <span className="inline-flex items-center gap-2">
              <span>Auth type</span>
              <InfoHint
                title="Auth type"
                description="Defines how outbound connector requests are signed/authenticated."
                options={['none', 'api_key', 'bearer_token', 'oauth2']}
              />
            </span>
            <QsSelect
              value={authType}
              onValueChange={(next) => setAuthType(next as (typeof AUTH_OPTIONS)[number])}
              options={AUTH_OPTIONS.map((opt) => ({
                value: opt,
                label: opt.replace("_", " "),
              }))}
            />
          </label>
          <label className="flex flex-col gap-2 md:col-span-2 text-sm font-medium text-(--qs-text-2)">
            MCP manifest · JSON ({`tools[]`})
            <textarea
              value={manifest}
              rows={9}
              onChange={(evt) => setManifest(evt.target.value)}
              placeholder={'{\n  "tools": [{ "name": "lookup", "path": "/", "method": "POST", "description": "Proxy" }]\n}'}
              className="v4-textarea font-mono text-xs"
            />
          </label>
          <label className="flex flex-col gap-2 md:col-span-2 text-sm font-medium text-(--qs-text-2)">
            Secrets blob · encrypted once (never returned)
            <textarea
              rows={5}
              value={secretBlob}
              onChange={(evt) => setSecretBlob(evt.target.value)}
              placeholder='Example: {"api_key":"..."}'
              className="v4-textarea font-mono text-xs"
            />
          </label>
        </div>

        <div className="mt-6">
          <button
            type="button"
            disabled={saving || !slug.trim() || !displayName.trim()}
            className="qs-btn qs-btn--primary gap-2 disabled:opacity-40"
            onClick={handleCreate}
          >
            {saving ? (
              <>
                <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
                Sealing…
              </>
            ) : (
              '+ Add new connector'
            )}
          </button>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader title="Combined roster" description="Dynamic hub rows synced from the hive API." />

        {!loadErr && !rows.length ? (
          <div className="v4-dream-empty text-center md:text-left" role="status">
            <p className="text-base font-semibold text-(--qs-text)">No dynamic hub rows yet</p>
            <p className="mt-2 text-sm text-(--qs-text-3)">
              Provision a Phase 3 template above or seal vault credentials first — the roster fills after manifests sync from the hive API.
            </p>
          </div>
        ) : null}

        {rows.length ? (
        <ViewportBoundedPanel
          className="v4-recipe-catalog-panel"
          footer={
            <ListPaginator
              page={rosterPagination.page}
              totalPages={rosterPagination.totalPages}
              totalItems={rosterPagination.totalItems}
              pageSize={rosterPageSize}
              onPageChange={rosterPagination.setPage}
            />
          }
        >
          <div className="combined-roster-grid">
          {rosterPagination.slice.map((conn) => (
            <article key={conn.id} className="v4-dream-cycle-card combined-roster-card flex flex-col gap-2">
              <header className="flex w-full flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-(--qs-text-3)">{conn.slug}</p>
                  <h3 className="text-base font-semibold leading-tight text-pollen">{conn.display_name}</h3>
                  <p className="truncate font-mono text-[10px] text-(--qs-text-3)" title={conn.base_url ?? undefined}>
                    {conn.base_url ?? '(unset base)'}
                  </p>
                </div>
                <ConnectorBadges builtin={conn.is_builtin} active={conn.is_active} />
              </header>

              <dl className="grid w-full gap-2 text-xs text-(--qs-text-2) sm:grid-cols-2">
                <div className="min-w-0">
                  <dt className="v4-field-label text-[10px]">Managers</dt>
                  <dd className="line-clamp-2 text-(--qs-text)">{managerChip(conn.allowed_manager_slugs)}</dd>
                </div>
                <div>
                  <dt className="v4-field-label text-[10px]">Last test</dt>
                  <dd className="text-(--qs-text)">{conn.last_tested_at ?? 'never probed'}</dd>
                </div>
              </dl>

              <footer className="v4-dream-cycle-card-actions pt-1">
                <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm text-[11px]" onClick={() => void handleTest(conn.id)}>
                  Test · 2500ms
                </button>
                <button
                  type="button"
                  disabled={conn.is_builtin}
                  className={cn('qs-btn qs-btn--ghost qs-btn--sm text-[11px]', conn.is_builtin && 'opacity-35')}
                  onClick={() => void toggleActive(conn)}
                >
                  {conn.is_active ? 'Deactivate' : 'Activate'}
                </button>
                {!conn.is_builtin ? (
                  <button type="button" className="qs-btn qs-btn--danger qs-btn--sm text-[11px]" onClick={() => void handleRemove(conn)}>
                    Remove
                  </button>
                ) : (
                  <p className="text-[10px] font-mono text-(--qs-text-3)">seeded · alembic</p>
                )}
              </footer>
            </article>
          ))}
          </div>
        </ViewportBoundedPanel>
        ) : null}
      </V4Card>
      </>
      ) : null}

    </>
  )

  if (embedded) {
    return <div className="flex flex-col gap-6">{shell}</div>
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 py-10 text-(--qs-text)">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.42em] text-(--qs-cyan)">
          Phase 3 · Communication &amp; Knowledge · MCP Hub
        </p>
        <div className="flex items-center gap-2">
          <h1 className="text-3xl font-bold tracking-tight text-(--qs-gold) md:text-[2.125rem]">
            Dynamic Connector Hub
          </h1>
          <InfoHint
            title="Dynamic Connector Hub"
            description="Connector operations hub for auth setup, marketplace wiring, and upstream integration testing."
            options={['Connector create/update', 'Vault + OAuth', 'Probe/test controls', 'Enable/disable connectors']}
          />
        </div>
        <p className="text-base text-(--qs-text-3)">
          Persist manifests in Postgres, seal secrets via hive Fernet blobs, hydrate Redis manifests (TTL 300s), rate-limit outbound
          calls per slug, trip breakers automatically, then surface tools to Ballroom orchestration queues. Phase 3 adds curated Gmail,
          Outlook, Calendar, GitHub, GitLab, Slack, Telegram, Discord, and Notion manifests — plus Obsidian vault embeddings into
          HiveMind when enabled.
        </p>
        <div className="flex flex-wrap gap-3 pt-2 text-sm">
          <Link
            href="/external-projects"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
          >
            <ExternalLink className="h-4 w-4" aria-hidden />
            External projects · MCP / REST / WS
          </Link>
          <Link href="/hive-mind" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
            <Sparkles className="h-4 w-4" aria-hidden />
            HiveMind recall
          </Link>
        </div>
      </header>
      {shell}
    </main>
  )
}