"use client";

import { ExternalLink, Plus } from "lucide-react";
import Link from "next/link";
import type { JSX } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { SuperToolRouterPanel } from "@/components/connectors/super-tool-router-panel";
import { InfoHint } from "@/components/hive/info-hint";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4CardHeader } from "@/components/ui/v4";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";
import { cn } from "@/lib/utils";
import { HiveApiError, hiveDelete, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { socialConnectorOperatorHint } from "@/lib/social-connector-operator-hints";

interface MarketplaceTemplateRow {
  source: string;
  id: string;
  slug: string;
  title: string;
  summary: string;
  category: string;
  auth_type: string;
  tool_count: number;
  installed: boolean;
  installed_connector_id?: string | null;
  documentation_url?: string;
  service_homepage?: string;
  agent_usage?: string;
  auth_header_name?: string | null;
  cost_tier?: "low" | "medium" | "high" | null;
  latency_tier?: "fast" | "balanced" | "slow" | null;
  featured?: boolean;
}

interface MarketplaceCatalogResponse {
  phase3_templates: MarketplaceTemplateRow[];
}

interface ConnectorsEnvelope {
  items: DynamicConnectorPayload[];
}

interface ConnectionEntry {
  key: string;
  slug: string;
  title: string;
  summary: string;
  agentUsage: string;
  auth_type: string;
  tool_count?: number;
  cost_tier: "low" | "medium" | "high";
  latency_tier: "fast" | "balanced" | "slow";
  featured?: boolean;
  documentationUrl?: string;
  serviceHomepage?: string;
  authHeaderName?: string | null;
  category?: string;
  fromTemplate: boolean;
  templateId?: string;
  templateSource?: string;
}

const AUTH_OPTIONS = ["none", "api_key", "bearer_token", "oauth2"] as const;
type AuthOption = (typeof AUTH_OPTIONS)[number];

type CategoryTab = "all" | "ai" | "knowledge" | "devtools" | "billing" | "calendar" | "chat" | "email" | "vault" | "social";

const CATEGORY_TABS: { id: CategoryTab; label: string }[] = [
  { id: "all", label: "All" },
  { id: "ai", label: "AI" },
  { id: "knowledge", label: "Knowledge" },
  { id: "devtools", label: "Devtools" },
  { id: "billing", label: "Billing" },
  { id: "calendar", label: "Calendar" },
  { id: "chat", label: "Chat" },
  { id: "email", label: "Email" },
  { id: "vault", label: "Vault" },
  { id: "social", label: "Social" },
];

const DEFAULT_MANIFEST = {
  tools: [
    {
      name: "invoke",
      path: "/",
      method: "POST",
      description: "Proxy JSON payloads to upstream root.",
    },
  ],
};

function categoryLabel(category: string): string {
  return category.replaceAll("_", " ");
}

function authFieldLabel(authType: string): string {
  if (authType === "api_key") return "API key";
  if (authType === "bearer_token") return "Bearer token";
  if (authType === "oauth2") return "OAuth access token";
  return "Credential";
}

function tierBadgeTone(tier: string, kind: "cost" | "latency"): "ok" | "warn" | "err" {
  if (kind === "cost") {
    if (tier === "low") return "ok";
    if (tier === "high") return "err";
    return "warn";
  }
  if (tier === "fast") return "ok";
  if (tier === "slow") return "err";
  return "warn";
}

function connectionStatus(entry: ConnectionEntry, connector: DynamicConnectorPayload | null): {
  label: string;
  tone: "ok" | "warn" | "err" | "info";
} {
  if (!connector) {
    return { label: entry.fromTemplate ? "not connected" : "missing", tone: "warn" };
  }
  if (connector.is_active) {
    return { label: "active", tone: "ok" };
  }
  if (connector.last_tested_at) {
    return { label: "tested · inactive", tone: "info" };
  }
  return { label: "needs credentials", tone: "err" };
}

function templateToEntry(row: MarketplaceTemplateRow): ConnectionEntry {
  return {
    key: row.id,
    slug: row.slug,
    title: row.title,
    summary: row.summary,
    agentUsage: row.agent_usage?.trim() || "Agents call manifest tools via mcp_invoke when this connector is active in their lane.",
    auth_type: row.auth_type,
    tool_count: row.tool_count,
    cost_tier: row.cost_tier ?? "medium",
    latency_tier: row.latency_tier ?? "balanced",
    featured: row.featured,
    documentationUrl: row.documentation_url,
    serviceHomepage: row.service_homepage ?? row.documentation_url,
    authHeaderName: row.auth_header_name,
    category: row.category,
    fromTemplate: true,
    templateId: row.id,
    templateSource: row.source || "phase3_template",
  };
}

function readCustomMeta(connector: DynamicConnectorPayload): { agentUsage?: string; documentationUrl?: string } {
  const manifest = connector.mcp_manifest;
  if (!manifest || typeof manifest !== "object") return {};
  const meta = (manifest as Record<string, unknown>).marketplace_meta;
  if (!meta || typeof meta !== "object") return {};
  const box = meta as Record<string, unknown>;
  return {
    agentUsage: typeof box.agent_usage === "string" ? box.agent_usage : undefined,
    documentationUrl: typeof box.documentation_url === "string" ? box.documentation_url : undefined,
  };
}

function customToEntry(connector: DynamicConnectorPayload): ConnectionEntry {
  const tools = connector.mcp_manifest?.tools;
  const toolCount = Array.isArray(tools) ? tools.length : 0;
  const meta = readCustomMeta(connector);
  return {
    key: `custom-${connector.id}`,
    slug: connector.slug,
    title: connector.display_name,
    summary: connector.base_url ? `Custom HTTP/MCP bridge · ${connector.base_url}` : "Custom HTTP/MCP bridge",
    agentUsage:
      meta.agentUsage?.trim() ||
      "Custom manifest tools exposed to agents through mcp_invoke when active and allowlisted.",
    auth_type: connector.auth_type,
    tool_count: toolCount,
    cost_tier: "medium",
    latency_tier: "balanced",
    documentationUrl: meta.documentationUrl,
    serviceHomepage: meta.documentationUrl,
    category: "devtools",
    fromTemplate: false,
  };
}

type MarketplaceView = "catalog" | "super-routers";

interface ToolsMarketplacePanelProps {
  onJumpToActive?: () => void;
}

export function ToolsMarketplacePanel({ onJumpToActive }: ToolsMarketplacePanelProps): JSX.Element {
  const [rows, setRows] = useState<MarketplaceTemplateRow[]>([]);
  const [connectorsBySlug, setConnectorsBySlug] = useState<Record<string, DynamicConnectorPayload>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [configuringSlug, setConfiguringSlug] = useState<string | null>(null);
  const [credentialDraft, setCredentialDraft] = useState("");
  const [activeTab, setActiveTab] = useState<CategoryTab>("all");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createSlug, setCreateSlug] = useState("");
  const [createDisplayName, setCreateDisplayName] = useState("");
  const [createBaseUrl, setCreateBaseUrl] = useState("");
  const [createAuthType, setCreateAuthType] = useState<AuthOption>("api_key");
  const [createCredential, setCreateCredential] = useState("");
  const [createDocUrl, setCreateDocUrl] = useState("");
  const [createAgentUsage, setCreateAgentUsage] = useState("");
  const [creating, setCreating] = useState(false);
  const [marketplaceView, setMarketplaceView] = useState<MarketplaceView>("catalog");

  const load = useCallback(async (): Promise<void> => {
    setError(null);
    try {
      const [catalog, connectors] = await Promise.all([
        hiveGet<MarketplaceCatalogResponse>("tools/marketplace/catalog"),
        hiveGet<ConnectorsEnvelope>("connectors/dynamic"),
      ]);
      setRows(catalog.phase3_templates ?? []);
      const bySlug: Record<string, DynamicConnectorPayload> = {};
      for (const item of connectors.items ?? []) {
        bySlug[item.slug.trim().toLowerCase()] = item;
      }
      setConnectorsBySlug(bySlug);
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Marketplace unavailable.";
      setError(detail);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const templateSlugs = useMemo(() => new Set(rows.map((row) => row.slug.trim().toLowerCase())), [rows]);

  const customEntries = useMemo(
    () =>
      Object.values(connectorsBySlug)
        .filter((connector) => !connector.is_builtin && !templateSlugs.has(connector.slug.trim().toLowerCase()))
        .map(customToEntry)
        .sort((a, b) => a.title.localeCompare(b.title)),
    [connectorsBySlug, templateSlugs],
  );

  const templateEntries = useMemo(() => rows.map(templateToEntry), [rows]);

  const tabCounts = useMemo(() => {
    const counts: Record<string, number> = { all: templateEntries.length };
    for (const entry of templateEntries) {
      const cat = entry.category || "other";
      counts[cat] = (counts[cat] ?? 0) + 1;
    }
    return counts;
  }, [templateEntries]);

  const visibleTemplateEntries = useMemo(() => {
    if (activeTab === "all") return templateEntries;
    return templateEntries.filter((entry) => entry.category === activeTab);
  }, [activeTab, templateEntries]);

  const templatePageSize = useGridTwoRowPageSize({ columns: 2 });
  const templatePagination = usePaginatedSlice(
    visibleTemplateEntries,
    templatePageSize,
    `${activeTab}|${templatePageSize}`,
  );

  async function connect(entry: ConnectionEntry): Promise<void> {
    if (!entry.fromTemplate || !entry.templateId) return;
    setBusyId(entry.key);
    setError(null);
    setSuccess(null);
    try {
      await hivePostJson("tools/marketplace/install", {
        source: entry.templateSource || "phase3_template",
        entry_id: entry.templateId,
      });
      setSuccess(`${entry.title} connected — add credentials and run test.`);
      setConfiguringSlug(entry.slug);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Connect failed.";
      setError(detail);
    } finally {
      setBusyId(null);
    }
  }

  async function createCustomConnection(): Promise<void> {
    const slug = createSlug.trim().toLowerCase();
    const displayName = createDisplayName.trim();
    if (!slug || !displayName) {
      setError("Slug and display name are required.");
      return;
    }

    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      let secrets: Record<string, string> | undefined;
      const trimmedCredential = createCredential.trim();
      if (trimmedCredential) {
        secrets =
          createAuthType === "api_key"
            ? { api_key: trimmedCredential, api_key_header_name: "X-API-KEY" }
            : createAuthType === "oauth2"
              ? { oauth2_access_token: trimmedCredential }
              : createAuthType === "bearer_token"
                ? { bearer_token: trimmedCredential }
                : undefined;
      }

      const manifest: Record<string, unknown> = {
        ...DEFAULT_MANIFEST,
        marketplace_meta: {
          documentation_url: createDocUrl.trim() || null,
          agent_usage: createAgentUsage.trim() || null,
        },
      };

      await hivePostJson<DynamicConnectorPayload>("connectors/dynamic", {
        slug,
        display_name: displayName,
        base_url: createBaseUrl.trim() || null,
        auth_type: createAuthType,
        secrets,
        mcp_manifest: manifest,
        allowed_manager_slugs: [],
      });

      setCreateSlug("");
      setCreateDisplayName("");
      setCreateBaseUrl("");
      setCreateAuthType("api_key");
      setCreateCredential("");
      setCreateDocUrl("");
      setCreateAgentUsage("");
      setShowCreateForm(false);
      setConfiguringSlug(slug);
      setSuccess(`${displayName} created — run test after saving credentials.`);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Create connection failed.";
      setError(detail);
    } finally {
      setCreating(false);
    }
  }

  async function saveCredentials(entry: ConnectionEntry, connector: DynamicConnectorPayload): Promise<void> {
    const trimmed = credentialDraft.trim();
    if (!trimmed) {
      setError("Enter a credential before saving.");
      return;
    }
    setBusyId(entry.key);
    setError(null);
    setSuccess(null);
    try {
      const secrets =
        entry.auth_type === "api_key"
          ? {
              api_key: trimmed,
              api_key_header_name: entry.authHeaderName?.trim() || "X-API-KEY",
            }
          : entry.auth_type === "oauth2"
            ? { oauth2_access_token: trimmed }
            : { bearer_token: trimmed };
      await hivePatchJson<DynamicConnectorPayload>(`connectors/dynamic/${encodeURIComponent(connector.id)}`, {
        secrets,
      });
      setCredentialDraft("");
      setConfiguringSlug(null);
      setSuccess(`${entry.title} credentials saved. Run test to activate.`);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Save credentials failed.";
      setError(detail);
    } finally {
      setBusyId(null);
    }
  }

  async function testConnection(entry: ConnectionEntry, connector: DynamicConnectorPayload): Promise<void> {
    setBusyId(`${entry.key}:test`);
    setError(null);
    setSuccess(null);
    try {
      const outcome = await hivePostJson<{ ok?: boolean; reason?: string }>(
        `connectors/dynamic/${encodeURIComponent(connector.id)}/test`,
        {},
      );
      if (outcome.ok) {
        setSuccess(`${entry.title} test passed — connection active.`);
      } else {
        setError(`${entry.title} test failed${outcome.reason ? `: ${outcome.reason}` : "."}`);
      }
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Test connection failed.";
      setError(detail);
    } finally {
      setBusyId(null);
    }
  }

  async function toggleActive(entry: ConnectionEntry, connector: DynamicConnectorPayload): Promise<void> {
    setBusyId(`${entry.key}:toggle`);
    setError(null);
    setSuccess(null);
    try {
      await hivePatchJson<DynamicConnectorPayload>(`connectors/dynamic/${encodeURIComponent(connector.id)}`, {
        is_active: !connector.is_active,
      });
      setSuccess(`${entry.title} ${connector.is_active ? "paused" : "activated"}.`);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Unable to change connection state.";
      setError(detail);
    } finally {
      setBusyId(null);
    }
  }

  async function deleteConnection(entry: ConnectionEntry, connector: DynamicConnectorPayload): Promise<void> {
    const accepted =
      typeof window !== "undefined"
        ? window.confirm(`Delete connection "${entry.title}"? This removes credentials and tools from the hive.`)
        : false;
    if (!accepted) return;

    setBusyId(`${entry.key}:delete`);
    setError(null);
    setSuccess(null);
    try {
      await hiveDelete(`connectors/dynamic/${encodeURIComponent(connector.id)}`);
      if (configuringSlug === entry.slug) {
        setConfiguringSlug(null);
        setCredentialDraft("");
      }
      setSuccess(`${entry.title} removed.`);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Delete failed.";
      setError(detail);
    } finally {
      setBusyId(null);
    }
  }

  function renderTierBadges(entry: ConnectionEntry): JSX.Element {
    return (
      <div className="flex flex-wrap gap-2">
        <V4Badge tone={tierBadgeTone(entry.cost_tier, "cost")}>{entry.cost_tier} cost</V4Badge>
        <V4Badge tone={tierBadgeTone(entry.latency_tier, "latency")}>{entry.latency_tier}</V4Badge>
        {entry.featured ? <V4Badge tone="gold">featured</V4Badge> : null}
      </div>
    );
  }

  function renderConnectionCard(entry: ConnectionEntry): JSX.Element {
    const connector = connectorsBySlug[entry.slug.trim().toLowerCase()] ?? null;
    const status = connectionStatus(entry, connector);
    const isConfiguring = configuringSlug === entry.slug;
    const rowBusy = busyId === entry.key;
    const testBusy = busyId === `${entry.key}:test`;
    const toggleBusy = busyId === `${entry.key}:toggle`;
    const deleteBusy = busyId === `${entry.key}:delete`;
    const showConnect = entry.fromTemplate && !connector;
    const docUrl = entry.serviceHomepage || entry.documentationUrl;
    const operatorHint = socialConnectorOperatorHint(entry.templateId);

    return (
      <article key={entry.key} className="v4-dream-cycle-card flex h-full flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 space-y-1">
            <p className="inline-flex items-center gap-2 text-sm font-semibold text-(--qs-text)">
              {entry.title}
              {operatorHint ? (
                <InfoHint
                  title={operatorHint.title}
                  description={operatorHint.description}
                  options={operatorHint.options}
                />
              ) : null}
            </p>
            {entry.category ? (
              <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
                {categoryLabel(entry.category)}
              </p>
            ) : null}
          </div>
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            {!entry.fromTemplate ? <V4Badge tone="info">custom</V4Badge> : null}
            <V4Badge tone={status.tone}>{status.label}</V4Badge>
          </div>
        </div>

        <p className="text-xs leading-relaxed text-(--qs-text-3)">{entry.summary}</p>

        <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
          <p className="v4-field-label text-[10px] text-cyan-300/90">How agents use this</p>
          <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">{entry.agentUsage}</p>
        </div>

        <p className="font-mono text-[11px] text-(--qs-text-3)">
          {entry.slug} · {entry.auth_type}
          {typeof entry.tool_count === "number" ? ` · ${entry.tool_count} tools` : ""}
        </p>

        {renderTierBadges(entry)}

        {docUrl ? (
          <a
            href={docUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-pollen hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden />
            Provider docs &amp; pricing
          </a>
        ) : null}

        {showConnect ? (
          <div className="v4-dream-cycle-card-actions">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={rowBusy}
              onClick={() => void connect(entry)}
            >
              {rowBusy ? "Connecting…" : "Connect"}
            </button>
          </div>
        ) : connector ? (
          <>
            {connector.last_tested_at ? (
              <p className="text-[11px] text-(--qs-text-3)">
                Last test: {new Date(connector.last_tested_at).toLocaleString()}
              </p>
            ) : null}

            {isConfiguring && entry.auth_type !== "oauth2" ? (
              <div className="space-y-2 rounded-xl border border-(--qs-border) bg-black/25 p-3">
                <label className="v4-field-label" htmlFor={`cred-${entry.key}`}>
                  {authFieldLabel(entry.auth_type)}
                </label>
                <input
                  id={`cred-${entry.key}`}
                  type="password"
                  autoComplete="off"
                  className="qs-input w-full font-mono text-xs"
                  placeholder={`Paste ${authFieldLabel(entry.auth_type).toLowerCase()}…`}
                  value={credentialDraft}
                  onChange={(event) => setCredentialDraft(event.target.value)}
                />
                <div className="v4-dream-cycle-card-actions">
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => {
                      setConfiguringSlug(null);
                      setCredentialDraft("");
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm"
                    disabled={rowBusy}
                    onClick={() => void saveCredentials(entry, connector)}
                  >
                    {rowBusy ? "Saving…" : "Save credentials"}
                  </button>
                </div>
              </div>
            ) : null}

            {isConfiguring && entry.auth_type === "oauth2" ? (
              <div className="rounded-xl border border-(--qs-border) bg-black/25 p-3 text-xs text-(--qs-text-3)">
                OAuth connectors need consent flow in the connector hub.
                <Link href="/integrations?tab=hub#oauth-consent" className="ml-1 text-pollen underline">
                  Open hub → OAuth
                </Link>
              </div>
            ) : null}

            <div className="v4-dream-cycle-card-actions">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                disabled={testBusy}
                onClick={() => void testConnection(entry, connector)}
              >
                {testBusy ? "Testing…" : "Test"}
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                disabled={toggleBusy}
                onClick={() => void toggleActive(entry, connector)}
              >
                {toggleBusy ? "…" : connector.is_active ? "Pause" : "Activate"}
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm text-(--qs-red)"
                disabled={deleteBusy}
                onClick={() => void deleteConnection(entry, connector)}
              >
                {deleteBusy ? "Deleting…" : "Delete"}
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm"
                disabled={rowBusy || entry.auth_type === "oauth2"}
                onClick={() => {
                  setConfiguringSlug(entry.slug);
                  setCredentialDraft("");
                }}
              >
                Configure
              </button>
            </div>
          </>
        ) : null}
      </article>
    );
  }

  return (
    <div className={cn("v4-marketplace-shell", marketplaceView === "catalog" && "v4-marketplace-shell--paginated")}>
      <V4CardHeader
        as="h3"
        title="API Marketplace Foundation"
        description="Curated routers and app bridges — tab by category, connect on demand, pause when idle."
        actions={
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm gap-2"
            onClick={() => setShowCreateForm((open) => !open)}
          >
            <Plus className="h-4 w-4" aria-hidden />
            {showCreateForm ? "Close form" : "Custom connection"}
          </button>
        }
      />

      {error ? (
        <p className="shrink-0 rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-3 py-2 text-xs text-(--qs-red)">{error}</p>
      ) : null}
      {success ? (
        <p className="shrink-0 rounded-xl border border-(--qs-green)/35 bg-(--qs-green)/10 px-3 py-2 text-xs text-(--qs-green)">
          {success}
        </p>
      ) : null}

      <div className="v4-subtab-row w-full max-w-full shrink-0">
        <button
          type="button"
          className={cn("v4-subtab shrink-0 gap-2", marketplaceView === "catalog" && "v4-subtab--active")}
          onClick={() => setMarketplaceView("catalog")}
        >
          Marketplace
        </button>
        <button
          type="button"
          className={cn("v4-subtab shrink-0 gap-2", marketplaceView === "super-routers" && "v4-subtab--active")}
          onClick={() => setMarketplaceView("super-routers")}
        >
          Super Routers
        </button>
        {onJumpToActive ? (
          <button type="button" className="v4-subtab shrink-0 gap-2 ml-auto text-pollen" onClick={onJumpToActive}>
            Active integrations ↓
          </button>
        ) : null}
      </div>

      {marketplaceView === "super-routers" ? (
        <div className="v4-marketplace-body-scroll hive-scrollbar min-h-0 flex-1">
          <SuperToolRouterPanel />
        </div>
      ) : null}

      {marketplaceView === "catalog" ? (
        <div className="flex flex-col gap-3">
      {showCreateForm ? (
        <div className="shrink-0 space-y-4 rounded-2xl border border-(--qs-border) bg-black/25 p-4">
          <div>
            <p className="text-sm font-semibold text-(--qs-text)">Create custom connection</p>
            <p className="mt-1 text-xs text-(--qs-text-3)">
              Define your own upstream API or MCP endpoint. Add agent guidance and a docs link so bees know when to call it.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
              Slug
              <input
                type="text"
                value={createSlug}
                placeholder="my_internal_api"
                onChange={(event) => setCreateSlug(event.target.value)}
                className="qs-input font-mono text-sm"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
              Display name
              <input
                type="text"
                value={createDisplayName}
                placeholder="My Internal API"
                onChange={(event) => setCreateDisplayName(event.target.value)}
                className="qs-input text-sm"
              />
            </label>
            <label className="flex flex-col gap-2 md:col-span-2 text-sm font-medium text-(--qs-text-2)">
              Base URL
              <input
                type="url"
                value={createBaseUrl}
                placeholder="https://api.example.com/v1"
                onChange={(event) => setCreateBaseUrl(event.target.value)}
                className="qs-input font-mono text-sm"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
              Auth type
              <QsSelect
                value={createAuthType}
                onValueChange={(next) => setCreateAuthType(next as AuthOption)}
                options={AUTH_OPTIONS.map((opt) => ({
                  value: opt,
                  label: opt.replaceAll("_", " "),
                }))}
              />
            </label>
            {createAuthType !== "none" ? (
              <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
                {authFieldLabel(createAuthType)} (optional now)
                <input
                  type="password"
                  autoComplete="off"
                  value={createCredential}
                  placeholder="Can add later via Configure"
                  onChange={(event) => setCreateCredential(event.target.value)}
                  className="qs-input font-mono text-sm"
                />
              </label>
            ) : null}
            <label className="flex flex-col gap-2 md:col-span-2 text-sm font-medium text-(--qs-text-2)">
              Provider documentation URL
              <input
                type="url"
                value={createDocUrl}
                placeholder="https://docs.example.com/api"
                onChange={(event) => setCreateDocUrl(event.target.value)}
                className="qs-input font-mono text-sm"
              />
            </label>
            <label className="flex flex-col gap-2 md:col-span-2 text-sm font-medium text-(--qs-text-2)">
              How agents should use this
              <textarea
                rows={3}
                value={createAgentUsage}
                placeholder="e.g. Research bees call invoke for verified enrichment when Serper results are thin."
                onChange={(event) => setCreateAgentUsage(event.target.value)}
                className="v4-textarea text-sm"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm gap-2"
              disabled={creating || !createSlug.trim() || !createDisplayName.trim()}
              onClick={() => void createCustomConnection()}
            >
              <Plus className="h-4 w-4" aria-hidden />
              {creating ? "Creating…" : "Create connection"}
            </button>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setShowCreateForm(false)}>
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      <div className="v4-subtab-row w-full max-w-full shrink-0">
        {CATEGORY_TABS.map((tab) => {
          const count = tab.id === "all" ? tabCounts.all : tabCounts[tab.id] ?? 0;
          if (tab.id !== "all" && count === 0) return null;
          return (
            <button
              key={tab.id}
              type="button"
              className={cn("v4-subtab shrink-0 gap-2", activeTab === tab.id && "v4-subtab--active")}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
              <span className="rounded-full bg-white/10 px-1.5 py-0.5 font-mono text-[10px] text-(--qs-text-3)">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-2">
        <p className="v4-field-label">
          {activeTab === "all" ? "All templates" : categoryLabel(activeTab)} ({visibleTemplateEntries.length})
        </p>
      </div>

      {customEntries.length ? (
        <div className="space-y-3">
          <p className="v4-field-label">Your connections ({customEntries.length})</p>
          <div className="grid gap-3 md:grid-cols-2">{customEntries.map((entry) => renderConnectionCard(entry))}</div>
        </div>
      ) : null}

      {visibleTemplateEntries.length ? (
        <ViewportBoundedPanel
          className="v4-recipe-catalog-panel"
          footer={
            <ListPaginator
              page={templatePagination.page}
              totalPages={templatePagination.totalPages}
              totalItems={templatePagination.totalItems}
              pageSize={templatePageSize}
              onPageChange={templatePagination.setPage}
            />
          }
        >
          <div className="grid gap-3 md:grid-cols-2">
            {templatePagination.slice.map((entry) => renderConnectionCard(entry))}
          </div>
        </ViewportBoundedPanel>
      ) : !rows.length && error ? null : (
        <p className="text-sm text-(--qs-text-3)">
          {rows.length ? "No templates in this category." : "Loading marketplace catalog…"}
        </p>
      )}
        </div>
      ) : null}
    </div>
  );
}
