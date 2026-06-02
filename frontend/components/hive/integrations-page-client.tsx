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
  Rocket,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { HiveSubnavContent, HiveSubnavStack } from "@/components/hive/hive-subnav-stack";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import {
  INTEGRATIONS_HUB_SECTIONS,
  integrationsHubSectionHref,
  resolveIntegrationsHubSection,
  type IntegrationsHubSection,
} from "@/lib/integrations-hub-routes";
import { useSetHiveMobileHeaderTrailing } from "@/components/hive/hive-mobile-header-actions";
import { IntegrationsEcosystemLane } from "@/components/hive/integrations-ecosystem-lane";
import {
  ActiveIntegrationsPanel,
  type IntegrationCard,
  type IntegrationCardStatus,
} from "@/components/hive/active-integrations-panel";
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
} from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import type { DynamicConnectorPayload } from "@/lib/connectors-types";
import {
  integrationsScrollTargetFromHash,
  integrationsTabExplicitInLocation,
  integrationsTabHref,
  integrationsHubOAuthHref,
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

const ExecutionStudioPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-panel").then((mod) => mod.ExecutionStudioPanel),
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

interface IntegrationsPageClientProps {
  initial: IntegrationsInitialPayload;
  initialTab?: IntegrationsTab;
}

const TABS: { id: IntegrationsTab; label: string; icon: typeof CheckCircle2; featureKey?: string }[] = [
  { id: "active", label: "Active", icon: CheckCircle2, featureKey: "integrations" },
  { id: "studio", label: "Execution Studio", icon: Rocket, featureKey: "execution_studio" },
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
  const plugins = payload.plugins ?? [];
  const connectors = payload.connectors ?? [];
  const externalProjects = payload.externalProjects ?? [];
  const pluginIds = new Set(plugins.map((row) => row.id));
  const mergedPlugins = [
    ...plugins,
    ...SUPPLEMENTAL_PLUGINS.filter((row) => !pluginIds.has(row.id)),
  ];

  const pluginCards: IntegrationCard[] = mergedPlugins.map((plugin) => ({
    id: `plugin-${plugin.id}`,
    title: plugin.title ?? plugin.name ?? plugin.id,
    meta: formatPluginMeta(plugin),
    description: plugin.description ?? formatPluginMeta(plugin),
    status: pluginStatus(plugin),
    kind: "plugin",
    targetTab: "plugins",
    iconKey: iconKeyForPlugin(plugin.id),
    categoryKey: "plugins",
  }));

  const connectorCards: IntegrationCard[] = connectors.map((conn) => ({
    id: `connector-${conn.id}`,
    title: conn.display_name,
    meta: `${conn.slug} · ${conn.auth_type}`,
    description: conn.is_active
      ? `${conn.display_name} is active in the connector hub.`
      : `${conn.display_name} is provisioned but needs credentials or OAuth connect.`,
    status: conn.is_active ? "connected" : "error",
    kind: "connector",
    targetTab: "hub",
    slug: conn.slug,
    iconKey: "plug",
    categoryKey: "connectors_other",
  }));

  const externalCards: IntegrationCard[] = externalProjects.map((project) => ({
    id: `external-${project.id}`,
    title: project.display_name,
    meta: `${project.slug} · ${project.project_kind}`,
    description: project.is_active
      ? `${project.display_name} bridge is active for cross-repo orchestration.`
      : `${project.display_name} bridge is registered but inactive.`,
    status: project.is_active ? "connected" : "error",
    kind: "external",
    targetTab: "external",
    iconKey: "layers",
    categoryKey: "external",
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
}: IntegrationsPageClientProps) {
  const { features, hasFeature } = usePlatform();
  const searchParams = useSearchParams();
  const tabs = useMemo(() => visibleIntegrationTabs(features), [features]);
  const tabIds = useMemo(() => tabs.map((item) => item.id), [tabs]);
  const hasHubTab = tabIds.includes("hub");
  const hasMarketplaceTab = tabIds.includes("marketplace");

  const resolveTabFromLocation = useCallback(
    (queryTab: string | null, hash: string): IntegrationsTab =>
      resolveIntegrationsTab({
        queryTab,
        hash,
        visibleTabIds: tabIds,
        fallback: tabIds[0] ?? "active",
      }),
    [tabIds],
  );

  const [tab, setTab] = useState<IntegrationsTab>(() =>
    resolveIntegrationsTab({
      queryTab: initialTab,
      visibleTabIds: tabIds,
      fallback: tabIds[0] ?? "active",
    }),
  );
  const [hubSection, setHubSection] = useState<IntegrationsHubSection>(() =>
    resolveIntegrationsHubSection({
      querySection:
        typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("hubSection") : null,
      hash: typeof window !== "undefined" ? window.location.hash : "",
    }),
  );
  const pendingOAuthScrollRef = useRef(false);
  const [payload, setPayload] = useState(initial);
  const [refreshing, setRefreshing] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [pluginToggleBusy, setPluginToggleBusy] = useState<string | null>(null);

  const selectTab = useCallback((next: IntegrationsTab) => {
    setTab(next);
    if (next === "hub") {
      window.history.replaceState(null, "", integrationsHubSectionHref(hubSection));
      return;
    }
    window.history.replaceState(null, "", integrationsTabHref(next));
  }, [hubSection]);

  const selectHubSection = useCallback((next: IntegrationsHubSection) => {
    setHubSection(next);
    window.history.replaceState(null, "", integrationsHubSectionHref(next));
  }, []);

  const jumpToActiveIntegrations = useCallback(() => {
    if (tab !== "active") {
      selectTab("active");
    }
    window.requestAnimationFrame(() => {
      document.getElementById("active-integrations")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [selectTab, tab]);

  const scrollToElementId = useCallback((targetId: string, retries = 24): void => {
    const attempt = (left: number): void => {
      const el = document.getElementById(targetId);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      if (left > 0) {
        window.setTimeout(() => attempt(left - 1), 100);
      }
    };
    attempt(retries);
  }, []);

  const scrollToHashTarget = useCallback(() => {
    const targetId = integrationsScrollTargetFromHash(window.location.hash);
    if (!targetId) {
      return;
    }
    scrollToElementId(targetId);
  }, [scrollToElementId]);

  const jumpToHubOAuth = useCallback(() => {
    pendingOAuthScrollRef.current = true;
    setTab("hub");
    setHubSection("oauth");
    window.history.replaceState(null, "", integrationsHubOAuthHref());
    scrollToElementId("oauth-consent");
  }, [scrollToElementId]);

  useEffect(() => {
    const syncFromLocation = (): void => {
      const params = new URLSearchParams(window.location.search);
      const hash = window.location.hash;
      const next = resolveTabFromLocation(params.get("tab"), hash);
      setTab(next);
      if (next === "hub") {
        setHubSection(
          resolveIntegrationsHubSection({
            querySection: params.get("hubSection"),
            hash,
          }),
        );
      }
      if (!integrationsTabExplicitInLocation({ queryTab: params.get("tab"), hash })) {
        const hubNext =
          next === "hub"
            ? resolveIntegrationsHubSection({
                querySection: params.get("hubSection"),
                hash,
              })
            : null;
        window.history.replaceState(
          null,
          "",
          next === "hub" && hubNext ? integrationsHubSectionHref(hubNext) : integrationsTabHref(next),
        );
      }
      scrollToHashTarget();
    };
    syncFromLocation();
    window.addEventListener("hashchange", syncFromLocation);
    window.addEventListener("popstate", syncFromLocation);
    return () => {
      window.removeEventListener("hashchange", syncFromLocation);
      window.removeEventListener("popstate", syncFromLocation);
    };
  }, [resolveTabFromLocation, scrollToHashTarget]);

  useEffect(() => {
    const hash = typeof window !== "undefined" ? window.location.hash : "";
    const next = resolveTabFromLocation(searchParams.get("tab"), hash);
    setTab(next);
    if (next === "hub") {
      setHubSection(
        resolveIntegrationsHubSection({
          querySection: searchParams.get("hubSection"),
          hash,
        }),
      );
    }
  }, [searchParams, resolveTabFromLocation]);

  useEffect(() => {
    if (tab !== "hub") {
      return;
    }
    if (pendingOAuthScrollRef.current || window.location.hash === "#oauth-consent") {
      pendingOAuthScrollRef.current = false;
      setHubSection("oauth");
      scrollToElementId("oauth-consent");
    } else {
      scrollToHashTarget();
    }
  }, [tab, hubSection, scrollToElementId, scrollToHashTarget]);

  useEffect(() => {
    if (tab !== "studio") {
      return;
    }
    scrollToHashTarget();
  }, [tab, scrollToHashTarget]);

  useEffect(() => {
    if (tabs.some((item) => item.id === tab)) {
      return;
    }
    const next = resolveTabFromLocation(null, "");
    setTab(next);
    window.history.replaceState(null, "", integrationsTabHref(next));
  }, [tab, tabs, resolveTabFromLocation]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const oauth = params.get("oauth");
    if (!oauth) {
      return;
    }
    if (oauth === "success") {
      const pk = params.get("provider") ?? "integration";
      toast.success(`${pk} connected — OAuth token sealed.`);
    } else {
      const reason = params.get("reason");
      toast.error(reason ? `OAuth failed: ${reason}` : "OAuth flow failed.");
    }
    const url = new URL(window.location.href);
    url.searchParams.delete("oauth");
    url.searchParams.delete("provider");
    url.searchParams.delete("reason");
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
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
    () => <HiveRefreshButton busy={refreshing} onClick={() => void refreshPulse()} />,
    [refreshPulse, refreshing],
  );

  useSetHiveMobileHeaderTrailing(mobileRefreshAction);

  return (
    <HivePageShell
      title="Integrations"
      subtitle="Connectors · MCP hub · tools marketplace · external projects · plugin lattice."
      hintKey="integrations"
      status={
        <HiveRefreshButton
          className="hidden lg:inline-flex"
          busy={refreshing}
          onClick={() => void refreshPulse()}
        />
      }
      actions={
        hasHubTab ? (
          <Link href={integrationsHubSectionHref("roster")} className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
            <Plus className="h-4 w-4" aria-hidden />
            Add connector
          </Link>
        ) : null
      }
      subnav={
        <HiveSubnavStack>
          <HiveSubnavRow
            items={tabs.map((item) => ({ id: item.id, label: item.label, icon: item.icon }))}
            activeId={tab}
            onChange={(id) => selectTab(id as IntegrationsTab)}
            ariaLabel="Integration sections"
            menuKey="integrations-primary"
          />
          {tab === "hub" ? (
            <HiveSubnavRow
              items={INTEGRATIONS_HUB_SECTIONS.map(({ id, label, icon }) => ({ id, label, icon }))}
              activeId={hubSection}
              onChange={(id) => selectHubSection(id as IntegrationsHubSection)}
              ariaLabel="Connector hub sections"
              menuKey="integrations-hub"
            />
          ) : null}
        </HiveSubnavStack>
      }
    >

      {tab === "active" ? (
        <HiveSubnavContent className="space-y-6">
          <IntegrationsEcosystemLane onSelectTab={selectTab} />

          <V4Card id="marketplace-preview" className="scroll-mt-28">
            <ToolsMarketplacePanel onJumpToActive={jumpToActiveIntegrations} />
          </V4Card>

          <V4Card id="active-integrations" className="scroll-mt-28 hub-section-card hub-section-card--flush">
            <ActiveIntegrationsPanel
              cards={activeCards}
              healthyCount={healthyCount}
              refreshing={refreshing}
              retryingId={retryingId}
              hasHubTab={hasHubTab}
              hasMarketplaceTab={hasMarketplaceTab}
              onRefresh={refreshPulse}
              onRetry={retryCard}
              onOpen={selectTab}
              onOpenHub={() => selectTab("hub")}
              onOpenMarketplace={() => selectTab("marketplace")}
            />
          </V4Card>
        </HiveSubnavContent>
      ) : null}

      {tab === "studio" ? (
        <HiveSubnavContent>
          <V4Card id="execution-studio" className="scroll-mt-28">
            <ExecutionStudioPanel
              onOpenMarketplace={() => selectTab("marketplace")}
              onOpenHub={jumpToHubOAuth}
            />
          </V4Card>
        </HiveSubnavContent>
      ) : null}

      {tab === "hub" ? (
        <HiveSubnavContent className="space-y-4">
          <V4Card id="hub" className="scroll-mt-28">
            <V4CardHeader
              kicker="Phase 3 · MCP Hub"
              title="Dynamic connector hub"
              description="OAuth consent rail, connector provisioning, vault sync, and connection testing in one place."
              hint={sectionHintNode("integrationsHub")}
            />
          </V4Card>

          {hubSection === "tools" ? (
            <V4Card id="hub-tools" className="scroll-mt-28 hub-section-card hub-section-card--flush">
              <UnifiedToolHubPanel embedded />
            </V4Card>
          ) : hubSection === "templates" ? (
            <V4Card id="hub-templates" className="scroll-mt-28 hub-section-card hub-section-card--flush">
              <ConnectorsConsole embedded hubSection={hubSection} />
            </V4Card>
          ) : (
            <V4Card id={`hub-${hubSection}`} className="scroll-mt-28">
              <ConnectorsConsole embedded hubSection={hubSection} />
            </V4Card>
          )}
        </HiveSubnavContent>
      ) : null}

      {tab === "marketplace" ? (
        <HiveSubnavContent>
          <V4Card>
            <V4CardHeader
              kicker="Tools lattice"
              title="Tools marketplace"
              description="Install API tools one-click, then expose them to supervisor lanes dynamically."
              hint={sectionHintNode("integrationsMarketplace")}
            />
            <ToolsMarketplacePanel onJumpToActive={jumpToActiveIntegrations} />
          </V4Card>
        </HiveSubnavContent>
      ) : null}

      {tab === "skills" ? (
        <HiveSubnavContent>
          <V4Card>
            <V4CardHeader
              kicker={hasFeature("skills_export_factory") ? "Revenue factory" : "Skills marketplace"}
              title={hasFeature("skills_export_factory") ? "Skills export & publish" : "Premium skills"}
              description={
                hasFeature("skills_export_factory")
                  ? "Swarm → verify → export SKILL.md bundle → publish on your external sales channels."
                  : "Browse and unlock premium skills for your hive."
              }
              hint={sectionHintNode("integrationsSkills")}
            />
            <SkillsMarketplacePanel />
          </V4Card>
        </HiveSubnavContent>
      ) : null}

      {tab === "external" ? (
        <HiveSubnavContent>
          <V4Card>
            <V4CardHeader
              title="External projects"
              description="External project registry, API key issuance, and live success/latency metrics."
              hint={sectionHintNode("integrationsExternal")}
            />
            <ExternalProjectsConsole />
          </V4Card>
        </HiveSubnavContent>
      ) : null}

      {tab === "plugins" ? (
        <HiveSubnavContent>
          <V4Card>
          <V4CardHeader
            title="Plugin catalog"
            description="Built-in modules and operator uploads with quick status inspection."
            hint={sectionHintNode("integrationsPlugins")}
            actions={
              payload.reloadGeneration != null ? (
                <V4Badge tone="info">gen {payload.reloadGeneration}</V4Badge>
              ) : null
            }
          />
          {!(payload.plugins ?? []).length ? (
            <p className="v4-learning-panel p-3 text-sm text-(--qs-text-3)">
              No plugin rows present.
            </p>
          ) : (
            <div className="v4-plugin-grid mb-4">
              {payload.plugins.map((plug) => {
                const enabled = pluginIsEnabled(plug);
                const busy = pluginToggleBusy === plug.id;
                return (
                  <article key={plug.id} className="v4-int-card v4-int-card--plugin flex h-full min-w-0 flex-col">
                    <div className="v4-int-head v4-int-head--plugin min-w-0">
                      <div className="flex min-w-0 flex-1 items-start gap-3">
                        <div className="v4-int-logo shrink-0">
                          <Boxes className="h-[18px] w-[18px]" aria-hidden />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="v4-int-name">{plug.title ?? plug.name ?? plug.id}</p>
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
                    <p className="v4-int-meta mt-auto pt-1">{formatPluginMeta(plug)}</p>
                  </article>
                );
              })}
            </div>
          )}
          <PluginsUserUploader />
          </V4Card>
        </HiveSubnavContent>
      ) : null}
    </HivePageShell>
  );
}
