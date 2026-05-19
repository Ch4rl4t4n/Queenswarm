"use client";

import dynamic from "next/dynamic";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  FlaskConical,
  GitBranch,
  Globe,
  Layers,
  Plug,
  Plus,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { PluginsUserUploader } from "@/components/hive/plugins-user-uploader";
import {
  V4Badge,
  V4Card,
  V4CardHeader,
  V4IconBolt,
  V4IconCoin,
  V4IconCpu,
  V4PageCanvas,
  type V4BadgeTone,
} from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";
import { integrationsTabFromHash } from "@/lib/integrations-routes";
import { cn } from "@/lib/utils";

const ConnectorsConsole = dynamic(
  () => import("@/components/connectors/connectors-console").then((mod) => mod.ConnectorsConsole),
  { ssr: false },
);

const ExternalProjectsConsole = dynamic(
  () =>
    import("@/components/external-projects/external-projects-console").then(
      (mod) => mod.ExternalProjectsConsole,
    ),
  { ssr: false },
);

const ToolsMarketplacePanel = dynamic(
  () =>
    import("@/components/connectors/tools-marketplace-panel").then((mod) => mod.ToolsMarketplacePanel),
  { ssr: false },
);

const SkillsMarketplacePanel = dynamic(
  () =>
    import("@/components/connectors/skills-marketplace-panel").then((mod) => mod.SkillsMarketplacePanel),
  { ssr: false },
);

type IntegrationTab = "active" | "hub" | "marketplace" | "skills" | "external" | "plugins";

type IntegrationCardStatus = "connected" | "error" | "rate_limited";

type IntegrationCardKind = "plugin" | "connector" | "external" | "system";

export interface PluginInstalledRow {
  id: string;
  title?: string;
  name?: string;
  enabled?: boolean;
  description?: string;
  version?: string;
  status?: string;
  source?: string;
}

export interface ExternalProjectRow {
  id: string;
  slug: string;
  display_name: string;
  project_kind: string;
  is_active: boolean;
}

export interface IntegrationsInitialPayload {
  connectors: DynamicConnectorPayload[];
  externalProjects: ExternalProjectRow[];
  plugins: PluginInstalledRow[];
  reloadGeneration?: number;
}

interface IntegrationCard {
  id: string;
  title: string;
  meta: string;
  status: IntegrationCardStatus;
  kind: IntegrationCardKind;
  targetTab: IntegrationTab;
  slug?: string;
  iconKey: string;
}

interface IntegrationsPageClientProps {
  initial: IntegrationsInitialPayload;
  initialTab?: IntegrationTab;
  purchaseOutcome?: "success" | "cancel" | null;
  checkoutSessionId?: string | null;
}

function resolveInitialTab(raw: string | undefined): IntegrationTab {
  const allowed: IntegrationTab[] = ["active", "hub", "marketplace", "skills", "external", "plugins"];
  if (raw && allowed.includes(raw as IntegrationTab)) {
    return raw as IntegrationTab;
  }
  return "active";
}

const TABS: { id: IntegrationTab; label: string; icon: typeof CheckCircle2 }[] = [
  { id: "active", label: "Active", icon: CheckCircle2 },
  { id: "hub", label: "Connector hub", icon: Plug },
  { id: "marketplace", label: "Tools marketplace", icon: Globe },
  { id: "skills", label: "Skills export", icon: Sparkles },
  { id: "external", label: "External projects", icon: Layers },
  { id: "plugins", label: "Plugins", icon: FlaskConical },
];

const SUPPLEMENTAL_PLUGINS: PluginInstalledRow[] = [
  {
    id: "browser-operator",
    title: "Browser Operator",
    enabled: true,
    version: "bundled",
    status: "active",
    description: "Live browser sessions with approval guardrails in supervisor control-plane.",
    source: "builtin",
  },
];

function statusTone(status: IntegrationCardStatus): V4BadgeTone {
  if (status === "connected") return "ok";
  if (status === "rate_limited") return "warn";
  return "err";
}

function pluginStatus(plugin: PluginInstalledRow): IntegrationCardStatus {
  const normalized = String(plugin.status ?? "").toLowerCase();
  if (normalized.includes("rate")) return "rate_limited";
  if (normalized.includes("error") || normalized.includes("fail") || normalized.includes("inactive")) {
    return "error";
  }
  if (normalized === "active" || plugin.enabled) return "connected";
  return "error";
}

function formatPluginMeta(plugin: PluginInstalledRow): string {
  const version =
    plugin.version === "bundled" || !plugin.version ? "bundled" : `v${plugin.version}`;
  const status = plugin.status ?? (plugin.enabled ? "active" : "inactive");
  return `${version} · ${status}`;
}

function iconKeyForPlugin(id: string): string {
  if (id.includes("workflow-breaker")) return "bolt";
  if (id.includes("langgraph")) return "graph";
  if (id.includes("simulation")) return "cpu";
  if (id.includes("cost-governor")) return "coin";
  if (id.includes("browser")) return "globe";
  return "plug";
}

function buildActiveCards(payload: IntegrationsInitialPayload): IntegrationCard[] {
  const pluginIds = new Set(payload.plugins.map((row) => row.id));
  const mergedPlugins = [
    ...payload.plugins,
    ...SUPPLEMENTAL_PLUGINS.filter((row) => !pluginIds.has(row.id)),
  ];

  const pluginCards: IntegrationCard[] = mergedPlugins.map((plugin) => ({
    id: `plugin-${plugin.id}`,
    title: plugin.title ?? plugin.name ?? plugin.id,
    meta: formatPluginMeta(plugin),
    status: pluginStatus(plugin),
    kind: "plugin",
    targetTab: "plugins",
    iconKey: iconKeyForPlugin(plugin.id),
  }));

  const connectorCards: IntegrationCard[] = payload.connectors.map((conn) => ({
    id: `connector-${conn.id}`,
    title: conn.display_name,
    meta: `${conn.slug} · ${conn.auth_type}`,
    status: conn.is_active ? "connected" : "error",
    kind: "connector",
    targetTab: "hub",
    slug: conn.slug,
    iconKey: "plug",
  }));

  const externalCards: IntegrationCard[] = payload.externalProjects.map((project) => ({
    id: `external-${project.id}`,
    title: project.display_name,
    meta: `${project.slug} · ${project.project_kind}`,
    status: project.is_active ? "connected" : "error",
    kind: "external",
    targetTab: "external",
    iconKey: "layers",
  }));

  return [...pluginCards, ...connectorCards, ...externalCards];
}

function IntegrationIcon({ iconKey }: { iconKey: string }) {
  if (iconKey === "bolt") return <V4IconBolt size={18} aria-hidden />;
  if (iconKey === "graph") return <GitBranch className="h-[18px] w-[18px]" aria-hidden />;
  if (iconKey === "cpu") return <V4IconCpu size={18} aria-hidden />;
  if (iconKey === "coin") return <V4IconCoin size={18} aria-hidden />;
  if (iconKey === "globe") return <Globe className="h-[18px] w-[18px]" aria-hidden />;
  if (iconKey === "layers") return <Layers className="h-[18px] w-[18px]" aria-hidden />;
  if (iconKey === "alert") return <AlertTriangle className="h-[18px] w-[18px]" aria-hidden />;
  return <Plug className="h-[18px] w-[18px]" aria-hidden />;
}

export function IntegrationsPageClient({
  initial,
  initialTab,
  purchaseOutcome = null,
  checkoutSessionId = null,
}: IntegrationsPageClientProps) {
  const [tab, setTab] = useState<IntegrationTab>(() => resolveInitialTab(initialTab));
  const [payload, setPayload] = useState(initial);
  const [refreshing, setRefreshing] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  useEffect(() => {
    const fromHash = integrationsTabFromHash(window.location.hash);
    if (fromHash) {
      setTab(fromHash);
    }
  }, []);

  const activeCards = useMemo(() => buildActiveCards(payload), [payload]);
  const healthyCount = activeCards.filter((card) => card.status === "connected").length;

  const refreshPulse = useCallback(async () => {
    setRefreshing(true);
    try {
      const [connectorsBody, externalRows, pluginsPack] = await Promise.all([
        hiveGet<{ items: DynamicConnectorPayload[] }>("/connectors/dynamic"),
        hiveGet<ExternalProjectRow[]>("/external/projects"),
        hiveGet<{ installed: PluginInstalledRow[]; reload_generation?: number }>("/plugins"),
      ]);
      setPayload({
        connectors: connectorsBody?.items ?? [],
        externalProjects: externalRows ?? [],
        plugins: pluginsPack?.installed ?? [],
        reloadGeneration: pluginsPack?.reload_generation,
      });
      toast.success("Integration pulse refreshed");
    } catch (error) {
      const message = error instanceof HiveApiError ? error.message : "Refresh failed";
      toast.error(message);
    } finally {
      setRefreshing(false);
    }
  }, []);

  const retryCard = useCallback(
    async (card: IntegrationCard) => {
      setRetryingId(card.id);
      try {
        if (card.kind === "plugin") {
          await hivePostJson("/operator/plugins/reload", {});
        } else if (card.kind === "connector" && card.slug) {
          await hivePostJson(`connectors/${encodeURIComponent(card.slug)}/ping`, {});
        } else {
          toast.message("Open the target tab to inspect and retry manually.");
          setTab(card.targetTab);
          return;
        }
        await refreshPulse();
        toast.success(`${card.title} retry dispatched`);
      } catch (error) {
        const message = error instanceof HiveApiError ? error.message : "Retry failed";
        toast.error(message);
      } finally {
        setRetryingId(null);
      }
    },
    [refreshPulse],
  );

  return (
    <V4PageCanvas>
      <HivePageHeader
        title="Integrations"
        subtitle="Connectors · MCP hub · tools marketplace · external projects · plugin lattice."
        actions={
          <>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
              disabled={refreshing}
              onClick={() => void refreshPulse()}
            >
              <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} aria-hidden />
              Refresh pulse
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm gap-2"
              onClick={() => setTab("hub")}
            >
              <Plus className="h-4 w-4" aria-hidden />
              Add connector
            </button>
          </>
        }
      />

      <div className="v4-subtab-row w-full max-w-full">
        {TABS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              className={cn("v4-subtab", tab === item.id && "v4-subtab--active")}
              onClick={() => setTab(item.id)}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden />
              {item.label}
            </button>
          );
        })}
      </div>

      {tab === "active" ? (
        <V4Card>
          <V4CardHeader
            title="Active integrations"
            description="Unified health snapshot across hub, bridges, and plugins."
            actions={
              <V4Badge tone="ok">
                {healthyCount} / {activeCards.length} healthy
              </V4Badge>
            }
          />
          {!activeCards.length ? (
            <p className="v4-learning-panel p-4 text-sm text-(--qs-text-3)">
              No integrations found yet. Provision a connector in the hub to start.
            </p>
          ) : (
            <div className="v4-cols-3">
              {activeCards.map((card) => (
                <article key={card.id} className="v4-int-card">
                  <div className="v4-int-head">
                    <div className="flex items-start gap-3">
                      <div className="v4-int-logo">
                        <IntegrationIcon iconKey={card.status === "error" ? "alert" : card.iconKey} />
                      </div>
                      <div className="min-w-0">
                        <p className="v4-int-name">{card.title}</p>
                        <p className="v4-int-meta">{card.meta}</p>
                      </div>
                    </div>
                    <V4Badge tone={statusTone(card.status)}>{card.status}</V4Badge>
                  </div>
                  <div className="v4-int-foot">
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      onClick={() => setTab(card.targetTab)}
                    >
                      Open
                    </button>
                    {card.status === "error" ? (
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
                        disabled={retryingId === card.id}
                        onClick={() => void retryCard(card)}
                      >
                        <RefreshCw
                          className={cn("h-3.5 w-3.5", retryingId === card.id && "animate-spin")}
                          aria-hidden
                        />
                        Retry
                      </button>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </V4Card>
      ) : null}

      {tab === "hub" ? (
        <V4Card>
          <V4CardHeader
            kicker="Phase 3 · MCP Hub"
            title="Dynamic connector hub"
            description="OAuth consent rail, connector provisioning, vault sync, and connection testing in one place."
          />
          <ConnectorsConsole embedded />
        </V4Card>
      ) : null}

      {tab === "marketplace" ? (
        <V4Card>
          <V4CardHeader
            kicker="Tools lattice"
            title="Tools marketplace"
            description="Install API tools one-click, then expose them to supervisor lanes dynamically."
          />
          <ToolsMarketplacePanel />
        </V4Card>
      ) : null}

      {tab === "skills" ? (
        <V4Card>
          <V4CardHeader
            kicker="Matt Pocock style"
            title="Skills export marketplace"
            description="Export verified recipes as SKILL.md + HIVE.md bundles for Cursor, Claude Code, and npx skills install flows."
          />
          <SkillsMarketplacePanel
            checkoutSessionId={checkoutSessionId}
            purchaseOutcome={purchaseOutcome}
          />
        </V4Card>
      ) : null}

      {tab === "external" ? (
        <V4Card>
          <V4CardHeader
            title="External projects"
            description="External project registry, API key issuance, and live success/latency metrics."
          />
          <ExternalProjectsConsole />
        </V4Card>
      ) : null}

      {tab === "plugins" ? (
        <V4Card>
          <V4CardHeader
            title="Plugin catalog"
            description="Built-in modules and operator uploads with quick status inspection."
            actions={
              payload.reloadGeneration != null ? (
                <V4Badge tone="info">gen {payload.reloadGeneration}</V4Badge>
              ) : null
            }
          />
          {!payload.plugins.length ? (
            <p className="v4-learning-panel p-3 text-sm text-(--qs-text-3)">
              No plugin rows present.
            </p>
          ) : (
            <div className="v4-cols-2 mb-4">
              {payload.plugins.map((plug) => (
                <article key={plug.id} className="v4-int-card">
                  <div className="v4-int-head">
                    <div className="flex items-start gap-3">
                      <div className="v4-int-logo">
                        <Boxes className="h-[18px] w-[18px]" aria-hidden />
                      </div>
                      <div className="min-w-0">
                        <p className="v4-int-name">{plug.title ?? plug.name ?? plug.id}</p>
                        <p className="v4-int-meta">{plug.description ?? "Awaiting operator notes."}</p>
                      </div>
                    </div>
                    <V4Badge tone={statusTone(pluginStatus(plug))}>
                      {plug.status ?? (plug.enabled ? "active" : "inactive")}
                    </V4Badge>
                  </div>
                  <p className="v4-int-meta">{formatPluginMeta(plug)}</p>
                </article>
              ))}
            </div>
          )}
          <PluginsUserUploader />
        </V4Card>
      ) : null}
    </V4PageCanvas>
  );
}
