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
import { useSetHiveMobileHeaderTrailing } from "@/components/hive/hive-mobile-header-actions";
import { IntegrationsEcosystemLane } from "@/components/hive/integrations-ecosystem-lane";
import { usePlatform } from "@/components/hive/platform-context";
import { PluginsUserUploader } from "@/components/hive/plugins-user-uploader";
import { HiveSwitch } from "@/components/ui/hive-switch";
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
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";
import {
  integrationsScrollTargetFromHash,
  integrationsTabHref,
  resolveIntegrationsTab,
  type IntegrationsTab,
} from "@/lib/integrations-routes";
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

const UnifiedToolHubPanel = dynamic(
  () =>
    import("@/components/connectors/unified-tool-hub-panel").then((mod) => mod.UnifiedToolHubPanel),
  { ssr: false },
);

const SkillsMarketplacePanel = dynamic(
  () =>
    import("@/components/connectors/skills-marketplace-panel").then((mod) => mod.SkillsMarketplacePanel),
  { ssr: false },
);

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
  targetTab: IntegrationsTab;
  slug?: string;
  iconKey: string;
}

interface IntegrationsPageClientProps {
  initial: IntegrationsInitialPayload;
  initialTab?: IntegrationsTab;
  purchaseOutcome?: "success" | "cancel" | null;
  checkoutSessionId?: string | null;
}

const TABS: { id: IntegrationsTab; label: string; icon: typeof CheckCircle2; featureKey?: string }[] = [
  { id: "active", label: "Active", icon: CheckCircle2, featureKey: "integrations" },
  { id: "hub", label: "Connector hub", icon: Plug, featureKey: "connectors" },
  { id: "marketplace", label: "Tools marketplace", icon: Globe, featureKey: "skills_marketplace" },
  { id: "skills", label: "Skills export", icon: Sparkles, featureKey: "skills_export_factory" },
  { id: "external", label: "External projects", icon: Layers, featureKey: "external_projects" },
  { id: "plugins", label: "Plugins", icon: FlaskConical, featureKey: "plugins" },
];

function visibleIntegrationTabs(features: Record<string, boolean>): typeof TABS {
  return TABS.filter((tab) => {
    if (tab.id === "skills") {
      return Boolean(features.skills_export_factory || features.skills_marketplace);
    }
    if (!tab.featureKey) {
      return true;
    }
    return Boolean(features[tab.featureKey]);
  });
}

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
  const status = pluginStatus(plugin) === "connected" ? "active" : "inactive";
  return `${version} · ${status}`;
}

function pluginIsEnabled(plugin: PluginInstalledRow): boolean {
  if (typeof plugin.enabled === "boolean") {
    return plugin.enabled;
  }
  return String(plugin.status ?? "").toLowerCase() === "active";
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
  const { features, hasFeature } = usePlatform();
  const tabs = useMemo(() => visibleIntegrationTabs(features), [features]);
  const [tab, setTab] = useState<IntegrationsTab>(() =>
    resolveIntegrationsTab({ queryTab: initialTab, fallback: "active" }),
  );
  const [payload, setPayload] = useState(initial);
  const [refreshing, setRefreshing] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [pluginToggleBusy, setPluginToggleBusy] = useState<string | null>(null);

  const selectTab = useCallback((next: IntegrationsTab) => {
    setTab(next);
    window.history.replaceState(null, "", integrationsTabHref(next));
  }, []);

  const scrollToHashTarget = useCallback(() => {
    const targetId = integrationsScrollTargetFromHash(window.location.hash);
    if (!targetId) {
      return;
    }
    document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  useEffect(() => {
    const syncFromLocation = (): void => {
      const params = new URLSearchParams(window.location.search);
      const next = resolveIntegrationsTab({
        queryTab: params.get("tab"),
        hash: window.location.hash,
      });
      setTab(next);
      scrollToHashTarget();
    };
    syncFromLocation();
    window.addEventListener("hashchange", syncFromLocation);
    window.addEventListener("popstate", syncFromLocation);
    return () => {
      window.removeEventListener("hashchange", syncFromLocation);
      window.removeEventListener("popstate", syncFromLocation);
    };
  }, [scrollToHashTarget]);

  useEffect(() => {
    scrollToHashTarget();
  }, [tab, scrollToHashTarget]);

  useEffect(() => {
    if (tabs.some((item) => item.id === tab)) {
      return;
    }
    setTab(tabs[0]?.id ?? "active");
  }, [tab, tabs]);

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
          selectTab(card.targetTab);
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
    [refreshPulse, selectTab],
  );

  const togglePlugin = useCallback(
    async (plug: PluginInstalledRow, nextEnabled: boolean) => {
      setPluginToggleBusy(plug.id);
      try {
        if (plug.source === "user") {
          if (nextEnabled) {
            await hivePostJson(`plugins/${encodeURIComponent(plug.id)}/enable`, {});
          } else {
            await hivePostJson(`plugins/${encodeURIComponent(plug.id)}/disable`, {});
          }
        } else {
          await hivePatchJson(`plugins/${encodeURIComponent(plug.id)}`, { enabled: nextEnabled });
        }
        setPayload((prev) => ({
          ...prev,
          plugins: prev.plugins.map((row) =>
            row.id === plug.id
              ? {
                  ...row,
                  enabled: nextEnabled,
                  status: nextEnabled ? "active" : "inactive",
                }
              : row,
          ),
        }));
        toast.success(nextEnabled ? `${plug.title ?? plug.id} enabled` : `${plug.title ?? plug.id} disabled`);
        await refreshPulse();
      } catch (error) {
        const message = error instanceof HiveApiError ? error.message : "Plugin toggle failed";
        toast.error(message);
      } finally {
        setPluginToggleBusy(null);
      }
    },
    [refreshPulse],
  );

  const mobileRefreshAction = useMemo(
    () => (
      <button
        type="button"
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-(--qs-border) bg-black/55 text-zinc-300 hover:border-(--qs-border-2) hover:text-pollen disabled:opacity-50 touch-manipulation"
        aria-label="Refresh integration pulse"
        disabled={refreshing}
        onClick={() => void refreshPulse()}
      >
        <RefreshCw className={cn("h-[20px] w-[20px]", refreshing && "animate-spin")} aria-hidden />
      </button>
    ),
    [refreshPulse, refreshing],
  );

  useSetHiveMobileHeaderTrailing(mobileRefreshAction);

  return (
    <V4PageCanvas>
      <HivePageHeader
        title="Integrations"
        subtitle="Connectors · MCP hub · tools marketplace · external projects · plugin lattice."
        status={
          <button
            type="button"
            className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-(--qs-border) bg-black/55 text-zinc-300 hover:border-(--qs-border-2) hover:text-pollen disabled:opacity-50 lg:flex"
            aria-label="Refresh integration pulse"
            disabled={refreshing}
            onClick={() => void refreshPulse()}
          >
            <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} aria-hidden />
          </button>
        }
        actions={
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm gap-2"
            onClick={() => selectTab("hub")}
          >
            <Plus className="h-4 w-4" aria-hidden />
            Add connector
          </button>
        }
      />

      <div className="v4-subtab-row w-full max-w-full">
        {tabs.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              className={cn("v4-subtab", tab === item.id && "v4-subtab--active")}
              onClick={() => selectTab(item.id)}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden />
              {item.label}
            </button>
          );
        })}
      </div>

      {tab === "active" ? (
        <div className="space-y-6">
          <IntegrationsEcosystemLane onSelectTab={selectTab} />

          <V4Card id="marketplace-preview" className="scroll-mt-28">
            <ToolsMarketplacePanel />
          </V4Card>

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
              <div className="v4-learning-panel flex flex-col items-center gap-3 p-6 text-center">
                <p className="text-sm text-(--qs-text-3)">
                  No integrations connected yet. Install a marketplace template or provision a connector in the hub.
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" onClick={() => selectTab("hub")}>
                    Open connector hub
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => selectTab("marketplace")}
                  >
                    Browse marketplace
                  </button>
                </div>
              </div>
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
                        onClick={() => selectTab(card.targetTab)}
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
        </div>
      ) : null}

      {tab === "hub" ? (
        <V4Card id="hub" className="scroll-mt-28">
          <V4CardHeader
            kicker="Phase 3 · MCP Hub"
            title="Dynamic connector hub"
            description="OAuth consent rail, connector provisioning, vault sync, and connection testing in one place."
          />
          <UnifiedToolHubPanel />
          <div className="my-8 border-t border-(--qs-border)/40" />
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
            kicker={hasFeature("skills_export_factory") ? "Revenue factory" : "Skills marketplace"}
            title={hasFeature("skills_export_factory") ? "Skills export & publish" : "Premium skills"}
            description={
              hasFeature("skills_export_factory")
                ? "Swarm → verify → export SKILL.md bundle → sell on GitHub, Gumroad, or optional Stripe unlock."
                : "Browse and unlock premium skills for your hive."
            }
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
            <div className="v4-cols-2 v4-cols-2--stack-mobile mb-4">
              {payload.plugins.map((plug) => {
                const enabled = pluginIsEnabled(plug);
                const busy = pluginToggleBusy === plug.id;
                return (
                  <article key={plug.id} className="v4-int-card v4-int-card--plugin min-w-0">
                    <div className="v4-int-head v4-int-head--plugin">
                      <div className="flex min-w-0 flex-1 items-start gap-3">
                        <div className="v4-int-logo shrink-0">
                          <Boxes className="h-[18px] w-[18px]" aria-hidden />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="v4-int-name truncate">{plug.title ?? plug.name ?? plug.id}</p>
                          <p className="v4-int-meta line-clamp-2">{plug.description ?? "Awaiting operator notes."}</p>
                        </div>
                      </div>
                      <HiveSwitch
                        checked={enabled}
                        disabled={busy}
                        aria-label={`${enabled ? "Disable" : "Enable"} ${plug.title ?? plug.name ?? plug.id}`}
                        className="shrink-0"
                        onCheckedChange={(next) => void togglePlugin(plug, next)}
                      />
                    </div>
                    <p className="v4-int-meta">{formatPluginMeta(plug)}</p>
                  </article>
                );
              })}
            </div>
          )}
          <PluginsUserUploader />
        </V4Card>
      ) : null}
    </V4PageCanvas>
  );
}
