"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import {
  formatRelativeMinutes,
  MCP_LIFECYCLE_RECOMMENDATION_COOLDOWN_MINUTES,
  minutesSinceIso,
  MCP_SNAPSHOT_RETRY_SPIKE_24H_THRESHOLD,
} from "@/lib/mcp-ops-observability";
import { useUiLanguage } from "@/components/hive/ui-language-provider";
import { HiveModalShell, hiveModalBottomSheetPanelClass } from "@/components/hive/hive-modal-shell";
import { AppsToolsModuleGrid } from "@/components/apps-tools/apps-tools-module-grid";
import { resolveAppsToolsAnalyticsCopy } from "@/lib/apps-tools-analytics-copy";
import {
  APPS_TOOLS_MODULES,
  APPS_TOOLS_MODULES_CORE,
  APPS_TOOLS_MODULES_FROZEN,
} from "@/lib/apps-tools-modules";
import { contentFactoryAgencyHref, contentFactoryMicroSaasHref } from "@/lib/factory-content-factory-routes";

type PolicyRiskTier = "read" | "write" | "publish" | "financial";

interface ModulePolicyPack {
  module_key: (typeof APPS_TOOLS_MODULES)[number]["moduleKey"];
  label: string;
  enabled: boolean;
  risk_tier: PolicyRiskTier;
  requires_approval: boolean;
  cooldown_sec: number | null;
  spend_cap_usd_24h: number | null;
  time_limit_sec: number | null;
  rate_limit_window_sec: number | null;
  rate_limit_max_global: number | null;
  notes: string[];
}

interface CapabilityWorkspace {
  module_key: string;
  label: string;
  summary: string;
  status: "live" | "beta" | "planned";
  enabled: boolean;
  capability_keys: string[];
}

interface CapabilityContract {
  capability_key: string;
  label: string;
  owner_module: string;
  summary: string;
  status: "live" | "beta" | "planned";
  risk_tier: PolicyRiskTier;
  requires_approval: boolean;
  sla_hint_sec: number | null;
  dependency_keys: string[];
}

interface AppsToolsIndexSnapshot {
  workspaces: CapabilityWorkspace[];
  capabilities: CapabilityContract[];
  policies: ModulePolicyPack[];
}

interface AppsToolsModuleFunnel {
  module_key: string;
  card_open: number;
  details_open: number;
  section_quick_link: number;
  dependency_jump: number;
}

interface AppsToolsAnalyticsEvent {
  at: string | null;
  event: AppsToolsFunnelEvent;
  module_key: string;
  target_module_key: string | null;
  href: string | null;
  source: string | null;
}

interface AppsToolsAnalyticsSnapshot {
  window: "24h" | "7d" | "all";
  compact_mode?: boolean;
  last_event_at: string | null;
  total_events: number;
  counters: Record<string, number>;
  module_funnel: AppsToolsModuleFunnel[];
  top_movers: Array<{
    module_key: string;
    module_label?: string | null;
    current_score: number;
    previous_score: number;
    delta_score: number;
  }>;
  recommendation: {
    module_key: string;
    module_label?: string | null;
    action: "review_details" | "open_sections" | "check_dependencies";
    reason: string;
  } | null;
  recent_events: AppsToolsAnalyticsEvent[];
}

type AppsToolsFunnelEvent =
  | "module_card_open"
  | "module_details_open"
  | "module_section_quick_link"
  | "module_dependency_jump"
  | "module_availability_hint_open"
  | "module_beta_hint_open"
  | "mcp_ops_snapshot_retry"
  | "mcp_ops_retry_anomaly_ack"
  | "mcp_ops_retry_anomaly_resurfaced"
  | "mcp_ops_retry_anomaly_ack_reset"
  | "mcp_ops_lifecycle_recommendation_open"
  | "mcp_ops_lifecycle_recommendation_cooldown_block"
  | "mcp_ops_lifecycle_recommendation_cooldown_override";

type RetryAnomalyAckScope = "window" | "global";
type RetryLifecycleState = "active" | "suppressed" | "resurfaced";

function riskTone(riskTier: PolicyRiskTier): string {
  if (riskTier === "financial") return "border-red-400/45 bg-red-400/10 text-red-100";
  if (riskTier === "publish") return "border-amber-400/45 bg-amber-400/10 text-amber-100";
  if (riskTier === "write") return "border-cyan-400/45 bg-cyan-400/10 text-cyan-100";
  return "border-emerald-400/45 bg-emerald-400/10 text-emerald-100";
}

function formatRateWindow(seconds: number): string {
  if (seconds < 3600) {
    return `${Math.max(1, Math.round(seconds / 60))}m`;
  }
  return `${Math.max(1, Math.round(seconds / 3600))}h`;
}

function formatEventLabel(event: AppsToolsFunnelEvent): string {
  if (event === "module_card_open") return "card open";
  if (event === "module_details_open") return "details open";
  if (event === "module_section_quick_link") return "section click";
  if (event === "module_dependency_jump") return "dependency jump";
  if (event === "module_availability_hint_open") return "availability hint";
  if (event === "mcp_ops_snapshot_retry") return "snapshot retry";
  if (event === "mcp_ops_retry_anomaly_ack") return "anomaly ack";
  if (event === "mcp_ops_retry_anomaly_resurfaced") return "anomaly resurfaced";
  if (event === "mcp_ops_retry_anomaly_ack_reset") return "anomaly ack reset";
  if (event === "mcp_ops_lifecycle_recommendation_open") return "lifecycle recommendation open";
  if (event === "mcp_ops_lifecycle_recommendation_cooldown_block") return "lifecycle cooldown blocked";
  if (event === "mcp_ops_lifecycle_recommendation_cooldown_override") return "lifecycle cooldown override";
  return "beta hint";
}

function safeLocalTime(input: string | null): string {
  if (!input) return "n/a";
  const dt = new Date(input);
  if (Number.isNaN(dt.getTime())) return "n/a";
  return dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function hintInteractionCounts(counters: Record<string, number> | null | undefined): {
  availability: number;
  beta: number;
} {
  let availability = 0;
  let beta = 0;
  if (!counters || typeof counters !== "object") {
    return { availability, beta };
  }
  for (const [key, rawValue] of Object.entries(counters)) {
    const value = Number.isFinite(rawValue) ? Math.max(0, Number(rawValue)) : 0;
    if (key.startsWith("module_availability_hint_open:")) {
      availability += value;
    } else if (key.startsWith("module_beta_hint_open:")) {
      beta += value;
    }
  }
  return { availability, beta };
}

function mcpSnapshotRetryCount(counters: Record<string, number> | null | undefined): number {
  if (!counters || typeof counters !== "object") {
    return 0;
  }
  let count = 0;
  for (const [key, rawValue] of Object.entries(counters)) {
    if (!key.startsWith("mcp_ops_snapshot_retry:")) {
      continue;
    }
    const value = Number.isFinite(rawValue) ? Math.max(0, Number(rawValue)) : 0;
    count += value;
  }
  return count;
}

function mcpRetryAckCount(counters: Record<string, number> | null | undefined): number {
  if (!counters || typeof counters !== "object") {
    return 0;
  }
  let count = 0;
  for (const [key, rawValue] of Object.entries(counters)) {
    if (!key.startsWith("mcp_ops_retry_anomaly_ack:")) {
      continue;
    }
    const value = Number.isFinite(rawValue) ? Math.max(0, Number(rawValue)) : 0;
    count += value;
  }
  return count;
}

function mcpRetryResurfacedCount(counters: Record<string, number> | null | undefined): number {
  if (!counters || typeof counters !== "object") {
    return 0;
  }
  let count = 0;
  for (const [key, rawValue] of Object.entries(counters)) {
    if (!key.startsWith("mcp_ops_retry_anomaly_resurfaced:")) {
      continue;
    }
    const value = Number.isFinite(rawValue) ? Math.max(0, Number(rawValue)) : 0;
    count += value;
  }
  return count;
}

function mcpLifecycleRecommendationOpenCount(counters: Record<string, number> | null | undefined): number {
  if (!counters || typeof counters !== "object") {
    return 0;
  }
  let count = 0;
  for (const [key, rawValue] of Object.entries(counters)) {
    if (!key.startsWith("mcp_ops_lifecycle_recommendation_open:")) {
      continue;
    }
    const value = Number.isFinite(rawValue) ? Math.max(0, Number(rawValue)) : 0;
    count += value;
  }
  return count;
}

function mcpLifecycleRecommendationOverrideCount(counters: Record<string, number> | null | undefined): number {
  if (!counters || typeof counters !== "object") {
    return 0;
  }
  let count = 0;
  for (const [key, rawValue] of Object.entries(counters)) {
    if (!key.startsWith("mcp_ops_lifecycle_recommendation_cooldown_override:")) {
      continue;
    }
    const value = Number.isFinite(rawValue) ? Math.max(0, Number(rawValue)) : 0;
    count += value;
  }
  return count;
}

function mcpSnapshotRetryTrend(countersByWindow: Record<"24h" | "7d" | "all", Record<string, number> | null>): Record<
  "24h" | "7d" | "all",
  number
> {
  return {
    "24h": mcpSnapshotRetryCount(countersByWindow["24h"]),
    "7d": mcpSnapshotRetryCount(countersByWindow["7d"]),
    all: mcpSnapshotRetryCount(countersByWindow.all),
  };
}

function retryTrendBarWidth(value: number, max: number): string {
  if (max <= 0) {
    return "8%";
  }
  return `${Math.max(8, Math.round((value / max) * 100))}%`;
}

function mcpSnapshotLastRetryAt(events: AppsToolsAnalyticsEvent[] | null | undefined): string | null {
  if (!Array.isArray(events)) {
    return null;
  }
  for (const row of events) {
    if (row.event === "mcp_ops_snapshot_retry" && row.at) {
      return row.at;
    }
  }
  return null;
}

function mcpRetryLastAckAt(events: AppsToolsAnalyticsEvent[] | null | undefined): string | null {
  if (!Array.isArray(events)) {
    return null;
  }
  for (const row of events) {
    if (row.event === "mcp_ops_retry_anomaly_ack" && row.at) {
      return row.at;
    }
  }
  return null;
}

function mcpLifecycleRecommendationLastAt(events: AppsToolsAnalyticsEvent[] | null | undefined): string | null {
  if (!Array.isArray(events)) {
    return null;
  }
  for (const row of events) {
    if (row.event === "mcp_ops_lifecycle_recommendation_open" && row.at) {
      return row.at;
    }
  }
  return null;
}

function resolveHintTrendTone(
  totalHints: number,
  window: "24h" | "7d" | "all",
): "quiet" | "watch" | "hot" {
  if (totalHints <= 0) {
    return "quiet";
  }
  if (window === "24h") {
    if (totalHints >= 4) return "hot";
    if (totalHints >= 2) return "watch";
    return "quiet";
  }
  if (window === "7d") {
    if (totalHints >= 8) return "hot";
    if (totalHints >= 3) return "watch";
    return "quiet";
  }
  if (totalHints >= 15) return "hot";
  if (totalHints >= 6) return "watch";
  return "quiet";
}

function normalizeAnalyticsSnapshot(raw: AppsToolsAnalyticsSnapshot | null): AppsToolsAnalyticsSnapshot {
  const windowRaw = raw?.window;
  return {
    window: windowRaw === "24h" || windowRaw === "7d" || windowRaw === "all" ? windowRaw : "24h",
    compact_mode: Boolean(raw?.compact_mode),
    last_event_at: typeof raw?.last_event_at === "string" ? raw.last_event_at : null,
    total_events: Number.isFinite(raw?.total_events) ? Number(raw?.total_events) : 0,
    counters: raw?.counters && typeof raw.counters === "object" ? raw.counters : {},
    module_funnel: Array.isArray(raw?.module_funnel) ? raw.module_funnel : [],
    top_movers: Array.isArray(raw?.top_movers) ? raw.top_movers : [],
    recommendation:
      raw?.recommendation && typeof raw.recommendation === "object" ? raw.recommendation : null,
    recent_events: Array.isArray(raw?.recent_events) ? raw.recent_events : [],
  };
}

const MODULE_SECTION_DEEP_LINKS: Record<
  (typeof APPS_TOOLS_MODULES)[number]["moduleKey"],
  Array<{ label: string; href: string }>
> = {
  marketing_automation: [
    { label: "Publish queue", href: "/apps-tools/marketing-automation?section=queue#publish-queue" },
    { label: "Social publish", href: "/apps-tools/marketing-automation?section=publish#social-publish" },
    { label: "Performance", href: "/apps-tools/marketing-automation?section=performance#publish-performance" },
  ],
  ecommerce_workspace: [
    { label: "Order events", href: "/apps-tools/ecommerce-automation?section=orders" },
    { label: "Webhook setup", href: "/apps-tools/ecommerce-automation?section=setup" },
    { label: "Connectors", href: "/integrations?tab=connectors" },
  ],
  mcp_ops_studio: [
    { label: "Catalog", href: "/apps-tools/mcp-ops-studio?section=catalog#mcp-catalog" },
    { label: "Install queue", href: "/apps-tools/mcp-ops-studio?section=install#mcp-install" },
    { label: "Health checks", href: "/apps-tools/mcp-ops-studio?section=health#mcp-health" },
  ],
  trading_automation: [
    { label: "Trading cockpit", href: "/apps-tools/trading-automation?section=cockpit#trading-cockpit" },
    { label: "Hybrid loop", href: "/apps-tools/trading-automation?section=hybrid#trading-content-hybrid" },
    { label: "Live lane prep", href: "/apps-tools/trading-automation?section=live-lane#live-lane" },
  ],
  browser_automation: [
    { label: "Live approvals", href: "/apps-tools/browser-automation?section=approvals#studio-pending-live" },
    { label: "Lane readiness", href: "/apps-tools/browser-automation?section=live-lane#live-lane" },
    { label: "Innovation", href: "/apps-tools/browser-automation?section=innovation#innovation-lab" },
  ],
  content_factory: [
    { label: "Media agency", href: contentFactoryAgencyHref() },
    { label: "Micro-SaaS factory", href: contentFactoryMicroSaasHref() },
  ],
  research_workspace: [
    { label: "Research bee", href: "/apps-tools/research-workspace?section=briefing#research-bee" },
    { label: "HiveMind recall", href: "/apps-tools/research-workspace?section=hivemind#hivemind-links" },
    { label: "Automation handoff", href: "/apps-tools/research-workspace?section=automation#research-automation" },
  ],
  skill_factory: [
    { label: "Research", href: "/apps-tools/skill-factory" },
    { label: "Sessions", href: "/agents#sessions" },
    { label: "Knowledge", href: "/knowledge" },
  ],
};

const MCP_RETRY_ANOMALY_ACK_STORAGE_KEY = "apps-tools:mcp-retry-anomaly-ack-score:v1";
const MCP_RETRY_ANOMALY_ACK_AT_STORAGE_KEY = "apps-tools:mcp-retry-anomaly-ack-at:v1";
const MCP_RETRY_ANOMALY_ACK_SCOPE_STORAGE_KEY = "apps-tools:mcp-retry-anomaly-ack-scope:v1";
const MCP_RETRY_ANOMALY_ACK_WINDOW_STORAGE_KEY = "apps-tools:mcp-retry-anomaly-ack-window:v1";
const MCP_RETRY_LIFECYCLE_RECOMMENDATION_AT_STORAGE_KEY = "apps-tools:mcp-lifecycle-recommendation-at:v1";

export function AppsToolsIndexClient() {
  const { language } = useUiLanguage();
  const copy = resolveAppsToolsAnalyticsCopy(language);
  const [policyByModule, setPolicyByModule] = useState<Record<string, ModulePolicyPack>>({});
  const [workspaceByModule, setWorkspaceByModule] = useState<Record<string, CapabilityWorkspace>>({});
  const [capabilitiesByModule, setCapabilitiesByModule] = useState<Record<string, CapabilityContract[]>>({});
  const [analyticsSnapshot, setAnalyticsSnapshot] = useState<AppsToolsAnalyticsSnapshot | null>(null);
  const [retryAnomalyAckScore, setRetryAnomalyAckScore] = useState<number | null>(null);
  const [retryAnomalyAckAt, setRetryAnomalyAckAt] = useState<string | null>(null);
  const [lifecycleRecommendationOpenedAt, setLifecycleRecommendationOpenedAt] = useState<string | null>(null);
  const [lifecycleOverrideConfirmArmed, setLifecycleOverrideConfirmArmed] = useState(false);
  const [retryAnomalyAckScope, setRetryAnomalyAckScope] = useState<RetryAnomalyAckScope>("window");
  const [retryAnomalyAckWindow, setRetryAnomalyAckWindow] = useState<"24h" | "7d" | "all">("24h");
  const [retryCountersByWindow, setRetryCountersByWindow] = useState<
    Record<"24h" | "7d" | "all", Record<string, number> | null>
  >({ "24h": null, "7d": null, all: null });
  const [analyticsWindow, setAnalyticsWindow] = useState<"24h" | "7d" | "all">("24h");
  const [analyticsWindowHydrated, setAnalyticsWindowHydrated] = useState(false);
  const [analyticsCompactMode, setAnalyticsCompactMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeModuleKey, setActiveModuleKey] = useState<string | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const lastResurfacedSignatureRef = useRef<string | null>(null);

  useEffect(() => {
    let alive = true;
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const snapshot = await hiveGet<AppsToolsIndexSnapshot>("operator/apps-tools-index");
        if (!alive) return;

        const nextPolicies: Record<string, ModulePolicyPack> = {};
        for (const row of snapshot.policies ?? []) {
          nextPolicies[row.module_key] = row;
        }
        setPolicyByModule(nextPolicies);

        const nextWorkspaces: Record<string, CapabilityWorkspace> = {};
        for (const row of snapshot.workspaces ?? []) {
          nextWorkspaces[row.module_key] = row;
        }
        setWorkspaceByModule(nextWorkspaces);

        const nextCapabilities: Record<string, CapabilityContract[]> = {};
        for (const row of snapshot.capabilities ?? []) {
          if (!nextCapabilities[row.owner_module]) {
            nextCapabilities[row.owner_module] = [];
          }
          nextCapabilities[row.owner_module]!.push(row);
        }
        setCapabilitiesByModule(nextCapabilities);
      } catch (exc) {
        if (exc instanceof HiveApiError && exc.status === 404) {
          return;
        }
      } finally {
        if (alive) {
          setLoading(false);
        }
      }
    };
    void load();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    const loadAnalytics = async (): Promise<void> => {
      try {
        const query = analyticsWindowHydrated
          ? `operator/apps-tools-index/analytics?limit=16&window=${analyticsWindow}`
          : "operator/apps-tools-index/analytics?limit=16";
        const analytics = await hiveGet<AppsToolsAnalyticsSnapshot>(
          query,
        );
        if (alive) {
          const normalized = normalizeAnalyticsSnapshot(analytics);
          setAnalyticsSnapshot(normalized);
          if (!analyticsWindowHydrated) {
            setAnalyticsWindow(normalized.window);
            setAnalyticsWindowHydrated(true);
          }
          setAnalyticsCompactMode(Boolean(normalized.compact_mode));
        }
      } catch {
        if (alive) {
          setAnalyticsSnapshot(null);
        }
      }
    };
    void loadAnalytics();
    return () => {
      alive = false;
    };
  }, [analyticsWindow, analyticsWindowHydrated]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const raw = window.localStorage.getItem(MCP_RETRY_ANOMALY_ACK_STORAGE_KEY);
    if (raw) {
      const parsed = Number.parseInt(raw, 10);
      if (Number.isFinite(parsed) && parsed >= 0) {
        setRetryAnomalyAckScore(parsed);
      }
    }
    const ackAtRaw = window.localStorage.getItem(MCP_RETRY_ANOMALY_ACK_AT_STORAGE_KEY);
    if (ackAtRaw) {
      setRetryAnomalyAckAt(ackAtRaw);
    }
    const scopeRaw = window.localStorage.getItem(MCP_RETRY_ANOMALY_ACK_SCOPE_STORAGE_KEY);
    if (scopeRaw === "window" || scopeRaw === "global") {
      setRetryAnomalyAckScope(scopeRaw);
    }
    const ackWindowRaw = window.localStorage.getItem(MCP_RETRY_ANOMALY_ACK_WINDOW_STORAGE_KEY);
    if (ackWindowRaw === "24h" || ackWindowRaw === "7d" || ackWindowRaw === "all") {
      setRetryAnomalyAckWindow(ackWindowRaw);
    }
    const lifecycleOpenedAt = window.localStorage.getItem(MCP_RETRY_LIFECYCLE_RECOMMENDATION_AT_STORAGE_KEY);
    if (lifecycleOpenedAt) {
      setLifecycleRecommendationOpenedAt(lifecycleOpenedAt);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    const loadRetryTrend = async (): Promise<void> => {
      try {
        const [d24, d7, dall] = await Promise.all([
          hiveGet<AppsToolsAnalyticsSnapshot>("operator/apps-tools-index/analytics?limit=1&window=24h"),
          hiveGet<AppsToolsAnalyticsSnapshot>("operator/apps-tools-index/analytics?limit=1&window=7d"),
          hiveGet<AppsToolsAnalyticsSnapshot>("operator/apps-tools-index/analytics?limit=1&window=all"),
        ]);
        if (!alive) return;
        setRetryCountersByWindow({
          "24h": d24?.counters && typeof d24.counters === "object" ? d24.counters : null,
          "7d": d7?.counters && typeof d7.counters === "object" ? d7.counters : null,
          all: dall?.counters && typeof dall.counters === "object" ? dall.counters : null,
        });
      } catch {
        if (!alive) return;
        setRetryCountersByWindow({ "24h": null, "7d": null, all: null });
      }
    };
    void loadRetryTrend();
    return () => {
      alive = false;
    };
  }, [analyticsWindow]);

  const persistAnalyticsPreferences = (next: {
    window?: "24h" | "7d" | "all";
    compactMode?: boolean;
  }): void => {
    void hivePostJson("operator/apps-tools-index/analytics/preferences", {
      window: next.window,
      compact_mode: next.compactMode,
    }).catch(() => {
      // Preference persistence is non-critical and must not block rendering.
    });
  };

  const activePolicy = useMemo(
    () => (activeModuleKey ? policyByModule[activeModuleKey] ?? null : null),
    [activeModuleKey, policyByModule],
  );

  const activeModuleDef = useMemo(
    () => APPS_TOOLS_MODULES.find((row) => row.moduleKey === activeModuleKey) ?? null,
    [activeModuleKey],
  );
  const activeWorkspace = useMemo(
    () => (activeModuleKey ? workspaceByModule[activeModuleKey] ?? null : null),
    [activeModuleKey, workspaceByModule],
  );
  const activeCapabilities = useMemo(
    () => (activeModuleKey ? capabilitiesByModule[activeModuleKey] ?? [] : []),
    [activeModuleKey, capabilitiesByModule],
  );
  const capabilityOwnerByKey = useMemo(() => {
    const index: Record<string, string> = {};
    for (const moduleCapabilities of Object.values(capabilitiesByModule)) {
      for (const capability of moduleCapabilities) {
        index[capability.capability_key] = capability.owner_module;
      }
    }
    return index;
  }, [capabilitiesByModule]);
  const moduleByKey = useMemo(() => {
    const index: Record<string, (typeof APPS_TOOLS_MODULES)[number]> = {};
    for (const moduleDef of APPS_TOOLS_MODULES) {
      index[moduleDef.moduleKey] = moduleDef;
    }
    return index;
  }, []);
  const activeDependencyEdges = useMemo(() => {
    if (!activeModuleKey) return [] as Array<{ dependencyKey: string; ownerModuleKey: string }>;
    const edges: Array<{ dependencyKey: string; ownerModuleKey: string }> = [];
    const seen = new Set<string>();
    for (const capability of activeCapabilities) {
      for (const dependencyKey of capability.dependency_keys) {
        const ownerModuleKey = capabilityOwnerByKey[dependencyKey];
        if (!ownerModuleKey || ownerModuleKey === activeModuleKey) continue;
        const dedupeKey = `${dependencyKey}:${ownerModuleKey}`;
        if (seen.has(dedupeKey)) continue;
        seen.add(dedupeKey);
        edges.push({ dependencyKey, ownerModuleKey });
      }
    }
    return edges;
  }, [activeCapabilities, activeModuleKey, capabilityOwnerByKey]);
  const hintCounts = useMemo(
    () => hintInteractionCounts(analyticsSnapshot?.counters),
    [analyticsSnapshot?.counters],
  );
  const hintTrendTone = useMemo(
    () => resolveHintTrendTone(hintCounts.availability + hintCounts.beta, analyticsWindow),
    [analyticsWindow, hintCounts.availability, hintCounts.beta],
  );
  const snapshotRetryCount = useMemo(
    () => mcpSnapshotRetryCount(analyticsSnapshot?.counters),
    [analyticsSnapshot?.counters],
  );
  const snapshotLastRetry = useMemo(
    () => mcpSnapshotLastRetryAt(analyticsSnapshot?.recent_events),
    [analyticsSnapshot?.recent_events],
  );
  const snapshotLastRetryRelative = useMemo(
    () => formatRelativeMinutes(minutesSinceIso(snapshotLastRetry)),
    [snapshotLastRetry],
  );
  const hasRetrySpikeIn24h = analyticsWindow === "24h" && snapshotRetryCount >= MCP_SNAPSHOT_RETRY_SPIKE_24H_THRESHOLD;
  const retryTrend = useMemo(() => mcpSnapshotRetryTrend(retryCountersByWindow), [retryCountersByWindow]);
  const retryAckSplitByWindow = useMemo(
    () => ({
      "24h": mcpRetryAckCount(retryCountersByWindow["24h"]),
      "7d": mcpRetryAckCount(retryCountersByWindow["7d"]),
      all: mcpRetryAckCount(retryCountersByWindow.all),
    }),
    [retryCountersByWindow],
  );
  const recommendationOpenSplitByWindow = useMemo(
    () => ({
      "24h": mcpLifecycleRecommendationOpenCount(retryCountersByWindow["24h"]),
      "7d": mcpLifecycleRecommendationOpenCount(retryCountersByWindow["7d"]),
      all: mcpLifecycleRecommendationOpenCount(retryCountersByWindow.all),
    }),
    [retryCountersByWindow],
  );
  const recommendationOverrideSplitByWindow = useMemo(
    () => ({
      "24h": mcpLifecycleRecommendationOverrideCount(retryCountersByWindow["24h"]),
      "7d": mcpLifecycleRecommendationOverrideCount(retryCountersByWindow["7d"]),
      all: mcpLifecycleRecommendationOverrideCount(retryCountersByWindow.all),
    }),
    [retryCountersByWindow],
  );
  const retryResurfacedSplitByWindow = useMemo(
    () => ({
      "24h": mcpRetryResurfacedCount(retryCountersByWindow["24h"]),
      "7d": mcpRetryResurfacedCount(retryCountersByWindow["7d"]),
      all: mcpRetryResurfacedCount(retryCountersByWindow.all),
    }),
    [retryCountersByWindow],
  );
  const hasSustainedRetryAnomaly =
    retryTrend["24h"] >= MCP_SNAPSHOT_RETRY_SPIKE_24H_THRESHOLD &&
    retryTrend["7d"] >= MCP_SNAPSHOT_RETRY_SPIKE_24H_THRESHOLD;
  const retryAnomalyScore = retryTrend["24h"] + retryTrend["7d"];
  const selectedWindowRetryScore = retryTrend[analyticsWindow];
  const isRetryAnomalyAcknowledged =
    retryAnomalyAckScore !== null &&
    (retryAnomalyAckScope === "global"
      ? retryAnomalyScore <= retryAnomalyAckScore
      : analyticsWindow === retryAnomalyAckWindow && selectedWindowRetryScore <= retryAnomalyAckScore);
  const showRetryAnomaly = hasSustainedRetryAnomaly && !isRetryAnomalyAcknowledged;
  const isRetryAnomalySuppressed = hasSustainedRetryAnomaly && isRetryAnomalyAcknowledged;
  const isRetryAnomalyResurfaced =
    hasSustainedRetryAnomaly &&
    retryAnomalyAckScore !== null &&
    (retryAnomalyAckScope === "global"
      ? retryAnomalyScore > retryAnomalyAckScore
      : analyticsWindow === retryAnomalyAckWindow && selectedWindowRetryScore > retryAnomalyAckScore);
  const retryLifecycleState: RetryLifecycleState | null = isRetryAnomalyResurfaced
    ? "resurfaced"
    : isRetryAnomalySuppressed
      ? "suppressed"
      : showRetryAnomaly
        ? "active"
        : null;
  const retryTrendMax = Math.max(1, retryTrend["24h"], retryTrend["7d"], retryTrend.all);
  const anomalyAckCount = useMemo(
    () => mcpRetryAckCount(analyticsSnapshot?.counters),
    [analyticsSnapshot?.counters],
  );
  const anomalyLastAckAt = useMemo(
    () => retryAnomalyAckAt ?? mcpRetryLastAckAt(analyticsSnapshot?.recent_events),
    [retryAnomalyAckAt, analyticsSnapshot?.recent_events],
  );
  const anomalyLastAckRelative = useMemo(
    () => formatRelativeMinutes(minutesSinceIso(anomalyLastAckAt)),
    [anomalyLastAckAt],
  );
  const hasAnomalySignalSplit = useMemo(
    () =>
      retryAckSplitByWindow["24h"] > 0 ||
      retryAckSplitByWindow["7d"] > 0 ||
      retryAckSplitByWindow.all > 0 ||
      retryResurfacedSplitByWindow["24h"] > 0 ||
      retryResurfacedSplitByWindow["7d"] > 0 ||
      retryResurfacedSplitByWindow.all > 0,
    [retryAckSplitByWindow, retryResurfacedSplitByWindow],
  );
  const hasRecommendationOpenSignal = useMemo(
    () =>
      recommendationOpenSplitByWindow["24h"] > 0 ||
      recommendationOpenSplitByWindow["7d"] > 0 ||
      recommendationOpenSplitByWindow.all > 0 ||
      recommendationOverrideSplitByWindow["24h"] > 0 ||
      recommendationOverrideSplitByWindow["7d"] > 0 ||
      recommendationOverrideSplitByWindow.all > 0,
    [recommendationOpenSplitByWindow, recommendationOverrideSplitByWindow],
  );
  const retryLifecycleLabel = useMemo(() => {
    if (retryLifecycleState === "resurfaced") {
      return copy.mcpRetryLifecycleResurfacedLabel;
    }
    if (retryLifecycleState === "suppressed") {
      return copy.mcpRetryLifecycleSuppressedLabel;
    }
    if (retryLifecycleState === "active") {
      return copy.mcpRetryLifecycleActiveLabel;
    }
    return null;
  }, [
    copy.mcpRetryLifecycleActiveLabel,
    copy.mcpRetryLifecycleResurfacedLabel,
    copy.mcpRetryLifecycleSuppressedLabel,
    retryLifecycleState,
  ]);
  const retryLifecycleRecommendationCtaLabel = useMemo(
    () =>
      retryLifecycleState === "suppressed"
        ? copy.mcpRetryLifecycleRecommendationMonitorCta
        : copy.mcpRetryLifecycleRecommendationOpenCta,
    [
      copy.mcpRetryLifecycleRecommendationMonitorCta,
      copy.mcpRetryLifecycleRecommendationOpenCta,
      retryLifecycleState,
    ],
  );
  const lifecycleRecommendationLastAt = useMemo(
    () => lifecycleRecommendationOpenedAt ?? mcpLifecycleRecommendationLastAt(analyticsSnapshot?.recent_events),
    [lifecycleRecommendationOpenedAt, analyticsSnapshot?.recent_events],
  );
  const lifecycleRecommendationLastOpenedMinutes = useMemo(
    () => minutesSinceIso(lifecycleRecommendationLastAt),
    [lifecycleRecommendationLastAt],
  );
  const recommendationCooldownRemainingMinutes = useMemo(() => {
    if (lifecycleRecommendationLastOpenedMinutes === null) {
      return null;
    }
    return Math.max(
      0,
      MCP_LIFECYCLE_RECOMMENDATION_COOLDOWN_MINUTES - lifecycleRecommendationLastOpenedMinutes,
    );
  }, [lifecycleRecommendationLastOpenedMinutes]);
  const isLifecycleRecommendationCooldownActive =
    recommendationCooldownRemainingMinutes !== null && recommendationCooldownRemainingMinutes > 0;
  const lifecycleRecommendationLastRelative = useMemo(
    () => formatRelativeMinutes(minutesSinceIso(lifecycleRecommendationLastAt)),
    [lifecycleRecommendationLastAt],
  );

  useEffect(() => {
    if (!hasSustainedRetryAnomaly || retryAnomalyAckScore === null) {
      return;
    }
    const resurfaced =
      retryAnomalyAckScope === "global"
        ? retryAnomalyScore > retryAnomalyAckScore
        : analyticsWindow === retryAnomalyAckWindow && selectedWindowRetryScore > retryAnomalyAckScore;
    if (!resurfaced) {
      return;
    }
    const signature = `${retryAnomalyAckScope}:${retryAnomalyAckWindow}:${retryAnomalyAckScore}:${retryAnomalyScore}:${selectedWindowRetryScore}:${analyticsWindow}`;
    if (lastResurfacedSignatureRef.current === signature) {
      return;
    }
    lastResurfacedSignatureRef.current = signature;
    trackEvent("mcp_ops_retry_anomaly_resurfaced", {
      moduleKey: "mcp_ops_studio",
      source: "analytics_retry_strip",
    });
  }, [
    analyticsWindow,
    hasSustainedRetryAnomaly,
    retryAnomalyAckScope,
    retryAnomalyAckScore,
    retryAnomalyAckWindow,
    retryAnomalyScore,
    selectedWindowRetryScore,
  ]);

  const clearRetryAnomalyAcknowledgment = (source?: string): void => {
    if (source) {
      trackEvent("mcp_ops_retry_anomaly_ack_reset", {
        moduleKey: "mcp_ops_studio",
        source,
      });
    }
    setRetryAnomalyAckScore(null);
    setRetryAnomalyAckAt(null);
    setRetryAnomalyAckWindow("24h");
    lastResurfacedSignatureRef.current = null;
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(MCP_RETRY_ANOMALY_ACK_STORAGE_KEY);
      window.localStorage.removeItem(MCP_RETRY_ANOMALY_ACK_AT_STORAGE_KEY);
      window.localStorage.removeItem(MCP_RETRY_ANOMALY_ACK_SCOPE_STORAGE_KEY);
      window.localStorage.removeItem(MCP_RETRY_ANOMALY_ACK_WINDOW_STORAGE_KEY);
    }
  };

  const trackEvent = (
    event: AppsToolsFunnelEvent,
    params: {
      moduleKey: string;
      targetModuleKey?: string;
      href?: string;
      source?: string;
    },
  ): void => {
    void hivePostJson("operator/apps-tools-index/events", {
      event,
      module_key: params.moduleKey,
      target_module_key: params.targetModuleKey,
      href: params.href,
      source: params.source ?? "apps_tools_index",
    }).catch(() => {
      // Analytics is best-effort only and must never block UX.
    });
  };

  const runLifecycleRecommendationOpenAction = (source: string): void => {
    const openedAt = new Date().toISOString();
    setLifecycleRecommendationOpenedAt(openedAt);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(MCP_RETRY_LIFECYCLE_RECOMMENDATION_AT_STORAGE_KEY, openedAt);
    }
    trackEvent("mcp_ops_lifecycle_recommendation_open", {
      moduleKey: "mcp_ops_studio",
      href: "/apps-tools/mcp-ops-studio?section=health",
      source,
    });
  };

  useEffect(() => {
    if (!isLifecycleRecommendationCooldownActive && lifecycleOverrideConfirmArmed) {
      setLifecycleOverrideConfirmArmed(false);
    }
  }, [isLifecycleRecommendationCooldownActive, lifecycleOverrideConfirmArmed]);

  const mcpModuleHeaderExtras = useMemo(() => {
    const badges: ReactNode[] = [];
    if (retryLifecycleLabel) {
      badges.push(
        <span
          key="lifecycle"
          className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
            retryLifecycleState === "resurfaced"
              ? "border-red-300/45 bg-red-300/10 text-red-100"
              : retryLifecycleState === "suppressed"
                ? "border-cyan-300/45 bg-cyan-300/10 text-cyan-100"
                : "border-magenta-300/45 bg-magenta-300/10 text-magenta-100"
          }`}
        >
          {copy.mcpRetryLifecycleBadgePrefix} {retryLifecycleLabel}
        </span>,
      );
    }
    if (showRetryAnomaly) {
      badges.push(
        <span
          key="anomaly"
          className="rounded-full border border-magenta-300/45 bg-magenta-300/10 px-2 py-0.5 text-[11px] font-medium text-magenta-100"
        >
          {copy.mcpRetryAnomalyBadge}
        </span>,
      );
    }
    if (badges.length === 0) return undefined;
    return <>{badges}</>;
  }, [copy.mcpRetryAnomalyBadge, copy.mcpRetryLifecycleBadgePrefix, retryLifecycleLabel, retryLifecycleState, showRetryAnomaly]);

  return (
    <>
      <section className="mt-4 rounded-2xl border border-pollen/30 bg-pollen/5 p-4">
        <h3 className="text-sm font-semibold text-(--qs-text)">Verified Niche Harness — first revenue</h3>
        <p className="mt-1 text-xs text-(--qs-text-3)">
          Harness beats model. Produce eval-backed packs (SKILL + HARNESS + EVAL + TOOLS), sell on Gumroad — not in-app
          marketplace.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link href="/apps-tools/skill-factory#launch" className="qs-btn qs-btn--primary qs-btn--sm">
            Skill Factory → Launch
          </Link>
          <Link href="/apps-tools/content-factory#research" className="qs-btn qs-btn--ghost qs-btn--sm">
            Content Pack Factory
          </Link>
          <Link href="/integrations?tab=hub" className="qs-btn qs-btn--ghost qs-btn--sm">
            MCP Integrations
          </Link>
          <Link href="/manual#skill-factory" className="qs-btn qs-btn--ghost qs-btn--sm">
            Operator manual
          </Link>
        </div>
      </section>

      {!loading && analyticsSnapshot ? (
        <details className="mt-4 rounded-2xl border border-white/12 bg-white/[0.03] p-4">
          <summary className="cursor-pointer text-sm font-semibold text-white/95">Advanced operator metrics (MCP)</summary>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-white/95">{copy.usagePulseTitle}</h3>
              <p className="mt-1 text-xs text-white/70">
                {copy.lastPrefix} {safeLocalTime(analyticsSnapshot.last_event_at)} · {analyticsSnapshot.total_events}{" "}
                {copy.eventsSuffix}
              </p>
            </div>
            <span className="rounded-full border border-cyan-400/40 bg-cyan-400/10 px-2 py-0.5 text-[11px] text-cyan-100">
              {copy.soloAnalyticsTag}
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(["24h", "7d", "all"] as const).map((windowKey) => (
              <button
                key={windowKey}
                type="button"
                aria-pressed={analyticsWindow === windowKey}
                className={`rounded-full border px-2 py-0.5 text-[11px] ${
                  analyticsWindow === windowKey
                    ? "border-cyan-400/45 bg-cyan-400/10 text-cyan-100"
                    : "border-white/20 bg-white/5 text-white/70"
                }`}
                onClick={() => {
                  setAnalyticsWindow(windowKey);
                  persistAnalyticsPreferences({ window: windowKey });
                }}
              >
                {windowKey}
              </button>
            ))}
            <button
              type="button"
              aria-pressed={analyticsCompactMode}
              className={`rounded-full border px-2 py-0.5 text-[11px] ${
                analyticsCompactMode
                  ? "border-cyan-400/45 bg-cyan-400/10 text-cyan-100"
                  : "border-white/20 bg-white/5 text-white/70"
              }`}
              onClick={() => {
                const next = !analyticsCompactMode;
                setAnalyticsCompactMode(next);
                persistAnalyticsPreferences({ compactMode: next });
              }}
            >
              {copy.compactLabel}
            </button>
          </div>
          {(hintCounts.availability > 0 || hintCounts.beta > 0) && !analyticsCompactMode ? (
            <div className="mt-3 rounded-xl border border-white/10 bg-black/20 px-3 py-2">
              <p className="text-[11px] font-medium text-white/85">{copy.hintInteractionsTitle}</p>
              <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-white/75">
                <span className="rounded-full border border-amber-300/45 bg-amber-300/10 px-2 py-0.5 text-amber-100">
                  {copy.hintAvailabilityLabel} {hintCounts.availability}
                </span>
                <span className="rounded-full border border-cyan-300/45 bg-cyan-300/10 px-2 py-0.5 text-cyan-100">
                  {copy.hintBetaLabel} {hintCounts.beta}
                </span>
                <span
                  className={`rounded-full border px-2 py-0.5 ${
                    hintTrendTone === "hot"
                      ? "border-red-300/45 bg-red-300/10 text-red-100"
                      : hintTrendTone === "watch"
                        ? "border-amber-300/45 bg-amber-300/10 text-amber-100"
                        : "border-emerald-300/45 bg-emerald-300/10 text-emerald-100"
                  }`}
                >
                  {copy.hintTrendPrefix}{" "}
                  {hintTrendTone === "hot"
                    ? copy.hintTrendHot
                    : hintTrendTone === "watch"
                      ? copy.hintTrendWatch
                      : copy.hintTrendQuiet}{" "}
                  ({analyticsWindow})
                </span>
              </div>
            </div>
          ) : null}
          {snapshotRetryCount > 0 ? (
            <div className="mt-3 rounded-xl border border-magenta-400/35 bg-magenta-400/10 px-3 py-2">
              <p className="text-[11px] font-medium text-magenta-100">
                {copy.mcpSnapshotRetriesLabel} {snapshotRetryCount}
              </p>
              <p className="mt-1 text-[11px] text-magenta-100/85">
                {copy.mcpSnapshotLastRetryLabel} {snapshotLastRetryRelative}
              </p>
              {hasRetrySpikeIn24h ? (
                <p className="mt-1 text-[11px] text-amber-100/90">{copy.mcpSnapshotRetrySpikeRecommendation}</p>
              ) : null}
              {showRetryAnomaly ? (
                <div className="mt-2">
                  <div className="mb-2 flex flex-wrap gap-2">
                    <button
                      type="button"
                      className={`rounded-full border px-2 py-0.5 text-[11px] ${
                        retryAnomalyAckScope === "window"
                          ? "border-magenta-300/50 bg-magenta-300/20 text-magenta-100"
                          : "border-white/20 bg-white/5 text-magenta-100/80"
                      }`}
                      onClick={() => setRetryAnomalyAckScope("window")}
                    >
                      {copy.mcpRetryAnomalyScopeWindowLabel}
                    </button>
                    <button
                      type="button"
                      className={`rounded-full border px-2 py-0.5 text-[11px] ${
                        retryAnomalyAckScope === "global"
                          ? "border-magenta-300/50 bg-magenta-300/20 text-magenta-100"
                          : "border-white/20 bg-white/5 text-magenta-100/80"
                      }`}
                      onClick={() => setRetryAnomalyAckScope("global")}
                    >
                      {copy.mcpRetryAnomalyScopeGlobalLabel}
                    </button>
                  </div>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => {
                      const ackAt = new Date().toISOString();
                      const baseline =
                        retryAnomalyAckScope === "global" ? retryAnomalyScore : selectedWindowRetryScore;
                      setRetryAnomalyAckScore(baseline);
                      setRetryAnomalyAckAt(ackAt);
                      setRetryAnomalyAckWindow(analyticsWindow);
                      lastResurfacedSignatureRef.current = null;
                      if (typeof window !== "undefined") {
                        window.localStorage.setItem(MCP_RETRY_ANOMALY_ACK_STORAGE_KEY, String(baseline));
                        window.localStorage.setItem(MCP_RETRY_ANOMALY_ACK_AT_STORAGE_KEY, ackAt);
                        window.localStorage.setItem(MCP_RETRY_ANOMALY_ACK_SCOPE_STORAGE_KEY, retryAnomalyAckScope);
                        window.localStorage.setItem(MCP_RETRY_ANOMALY_ACK_WINDOW_STORAGE_KEY, analyticsWindow);
                      }
                      trackEvent("mcp_ops_retry_anomaly_ack", {
                        moduleKey: "mcp_ops_studio",
                        source: "analytics_retry_strip",
                      });
                    }}
                  >
                    {copy.mcpRetryAnomalyAcknowledgeCta}
                  </button>
                </div>
              ) : isRetryAnomalyAcknowledged ? (
                <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-magenta-100/85">
                  <p>{copy.mcpRetryAnomalyAcknowledgedLabel}</p>
                  <span className="rounded-full border border-magenta-300/35 bg-magenta-300/10 px-2 py-0.5 text-magenta-100">
                    {copy.mcpRetryAnomalyScopeChipLabel}{" "}
                    {retryAnomalyAckScope === "global"
                      ? copy.mcpRetryAnomalyScopeGlobalLabel
                      : copy.mcpRetryAnomalyScopeWindowLabel}
                  </span>
                </div>
              ) : null}
              {isRetryAnomalyAcknowledged ? (
                <p className="mt-1 text-[11px] text-magenta-100/85">
                  {copy.mcpRetryAnomalyAckedAgoLabel} {anomalyLastAckRelative}
                </p>
              ) : null}
              {isRetryAnomalySuppressed ? (
                <div className="mt-2">
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => clearRetryAnomalyAcknowledgment()}
                  >
                    {copy.mcpRetryAnomalyClearCta}
                  </button>
                </div>
              ) : null}
              {anomalyAckCount > 0 ? (
                <p className="mt-1 text-[11px] text-magenta-100/85">
                  {copy.mcpRetryAnomalyAckCountLabel} {anomalyAckCount}
                </p>
              ) : null}
              {hasAnomalySignalSplit ? (
                <div className="mt-2 rounded-lg border border-magenta-300/30 bg-black/20 px-2 py-1.5">
                  <p className="text-[11px] font-medium text-magenta-100">{copy.mcpRetryAnomalyRateSplitLabel}</p>
                  <div className="mt-1 flex flex-wrap gap-1.5 text-[11px] text-magenta-100/85">
                    <span className="rounded-full border border-magenta-300/35 bg-magenta-300/10 px-2 py-0.5">
                      24h {retryAckSplitByWindow["24h"]}/{retryResurfacedSplitByWindow["24h"]}
                    </span>
                    <span className="rounded-full border border-magenta-300/35 bg-magenta-300/10 px-2 py-0.5">
                      7d {retryAckSplitByWindow["7d"]}/{retryResurfacedSplitByWindow["7d"]}
                    </span>
                    <span className="rounded-full border border-magenta-300/35 bg-magenta-300/10 px-2 py-0.5">
                      all {retryAckSplitByWindow.all}/{retryResurfacedSplitByWindow.all}
                    </span>
                  </div>
                </div>
              ) : null}
              <div
                className={`mt-2 grid gap-1 text-[11px] ${
                  analyticsCompactMode ? "grid-cols-3" : "grid-cols-3"
                } text-magenta-100/85`}
              >
                <span>24h {retryTrend["24h"]}</span>
                <span>7d {retryTrend["7d"]}</span>
                <span>all {retryTrend.all}</span>
              </div>
              <div className="mt-2 rounded-md border border-magenta-300/20 bg-black/20 px-2 py-2">
                <p className="text-[11px] font-medium text-magenta-100">{copy.mcpSnapshotRetryTrendLabel}</p>
                <div className="mt-1 space-y-1.5">
                  {(
                    [
                      { key: "24h", value: retryTrend["24h"] },
                      { key: "7d", value: retryTrend["7d"] },
                      { key: "all", value: retryTrend.all },
                    ] as const
                  ).map((row) => (
                    <div key={row.key} className="flex items-center gap-2 text-[10px] text-magenta-100/80">
                      <span className="w-7 shrink-0">{row.key}</span>
                      <div className="h-1.5 flex-1 rounded-full bg-white/10" aria-hidden>
                        <div
                          className="h-1.5 rounded-full bg-magenta-300/80"
                          style={{ width: retryTrendBarWidth(row.value, retryTrendMax) }}
                        />
                      </div>
                      <span className="w-5 text-right">{row.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
          <div className={`mt-3 grid gap-2 ${analyticsCompactMode ? "max-lg:grid-cols-1 md:grid-cols-2" : "md:grid-cols-2"}`}>
            {(analyticsSnapshot.module_funnel ?? []).slice(0, analyticsCompactMode ? 2 : 4).map((row) => {
              const moduleDef = APPS_TOOLS_MODULES.find((item) => item.moduleKey === row.module_key);
              const conversion = row.card_open > 0 ? Math.round((row.details_open / row.card_open) * 100) : 0;
              return (
                <article key={row.module_key} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs">
                  <p className="font-medium text-white/90">{moduleDef?.title ?? row.module_key}</p>
                  {analyticsCompactMode ? (
                    <p className="mt-1 text-[11px] text-cyan-100/80">card→details {conversion}%</p>
                  ) : (
                    <>
                      <p className="mt-1 text-white/70">
                        card {row.card_open} · details {row.details_open} · sections {row.section_quick_link}
                      </p>
                      <p className="mt-1 text-[11px] text-cyan-100/80">card→details {conversion}%</p>
                    </>
                  )}
                </article>
              );
            })}
          </div>
          {!analyticsCompactMode && analyticsSnapshot.top_movers.length > 0 ? (
            <div className="mt-3 rounded-xl border border-white/10 bg-black/20 px-3 py-2">
              <p className="text-[11px] font-medium text-white/85">{copy.topMoversTitle}</p>
              <div className="mt-1 space-y-1">
                {analyticsSnapshot.top_movers.slice(0, 3).map((row) => (
                  <p key={row.module_key} className="text-[11px] text-white/70">
                    {row.module_label ??
                      APPS_TOOLS_MODULES.find((item) => item.moduleKey === row.module_key)?.title ??
                      row.module_key}
                    :{" "}
                    {row.delta_score >= 0 ? "+" : ""}
                    {row.delta_score} ({row.previous_score} → {row.current_score})
                  </p>
                ))}
              </div>
            </div>
          ) : null}
          {analyticsSnapshot.recommendation ? (
            <div className="mt-3 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2">
              <p className="text-[11px] font-medium text-cyan-100">{copy.recommendationTitle}</p>
              <p className="mt-1 text-[11px] text-cyan-100/85">
                {analyticsSnapshot.recommendation.module_label ??
                  APPS_TOOLS_MODULES.find((item) => item.moduleKey === analyticsSnapshot.recommendation?.module_key)?.title ??
                  analyticsSnapshot.recommendation.module_key}
                : {analyticsSnapshot.recommendation.reason}
              </p>
              {retryLifecycleLabel && hasAnomalySignalSplit ? (
                <div className="mt-1">
                  <p className="text-[11px] text-cyan-100/85">
                    {copy.mcpRetryLifecycleRecommendationLabel}: {retryLifecycleLabel} · 24h{" "}
                    {retryAckSplitByWindow["24h"]}/{retryResurfacedSplitByWindow["24h"]} · 7d{" "}
                    {retryAckSplitByWindow["7d"]}/{retryResurfacedSplitByWindow["7d"]} · all{" "}
                    {retryAckSplitByWindow.all}/{retryResurfacedSplitByWindow.all}
                  </p>
                  <Link
                    href="/apps-tools/mcp-ops-studio?section=health"
                    aria-disabled={isLifecycleRecommendationCooldownActive}
                    className={`mt-1 inline-flex text-[11px] font-medium underline-offset-2 transition focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/45 ${
                      isLifecycleRecommendationCooldownActive
                        ? "cursor-not-allowed text-cyan-100/55 no-underline"
                        : "text-cyan-100 hover:text-cyan-50 hover:underline"
                    }`}
                    onClick={(event) => {
                      event.preventDefault();
                      if (isLifecycleRecommendationCooldownActive) {
                        setLifecycleOverrideConfirmArmed(false);
                        trackEvent("mcp_ops_lifecycle_recommendation_cooldown_block", {
                          moduleKey: "mcp_ops_studio",
                          href: "/apps-tools/mcp-ops-studio?section=health",
                          source: "analytics_recommendation",
                        });
                        return;
                      }
                      setLifecycleOverrideConfirmArmed(false);
                      runLifecycleRecommendationOpenAction("analytics_recommendation");
                    }}
                  >
                    {retryLifecycleRecommendationCtaLabel}
                  </Link>
                  {isLifecycleRecommendationCooldownActive ? (
                    <div className="mt-1 space-y-1">
                      <p className="text-[11px] text-cyan-100/85">
                        {copy.mcpRetryLifecycleRecommendationCooldownLabel} {recommendationCooldownRemainingMinutes}m
                      </p>
                      <button
                        type="button"
                        className="inline-flex rounded-md border border-cyan-300/35 px-2 py-0.5 text-[11px] font-medium text-cyan-100 transition hover:border-cyan-200/60 hover:text-cyan-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/45"
                        onClick={() => setLifecycleOverrideConfirmArmed((current) => !current)}
                      >
                        {copy.mcpRetryLifecycleRecommendationOverrideCta}
                      </button>
                      {lifecycleOverrideConfirmArmed ? (
                        <button
                          type="button"
                          className="inline-flex rounded-md border border-magenta-300/35 bg-magenta-300/10 px-2 py-0.5 text-[11px] font-medium text-magenta-100 transition hover:border-magenta-200/65 hover:text-magenta-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-magenta-300/45"
                          onClick={() => {
                            setLifecycleOverrideConfirmArmed(false);
                            trackEvent("mcp_ops_lifecycle_recommendation_cooldown_override", {
                              moduleKey: "mcp_ops_studio",
                              href: "/apps-tools/mcp-ops-studio?section=health",
                              source: "analytics_recommendation",
                            });
                            runLifecycleRecommendationOpenAction("analytics_recommendation_override");
                          }}
                        >
                          {copy.mcpRetryLifecycleRecommendationOverrideConfirmCta}
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}
              {lifecycleRecommendationLastAt ? (
                <p className="mt-1 text-[11px] text-cyan-100/85">
                  {copy.mcpRetryLifecycleRecommendationLastOpenedLabel} {lifecycleRecommendationLastRelative}
                </p>
              ) : null}
              {hasRecommendationOpenSignal ? (
                <p className="mt-1 text-[11px] text-cyan-100/85">
                  {copy.mcpRetryLifecycleRecommendationStripLabel} · 24h {recommendationOpenSplitByWindow["24h"]} · 7d{" "}
                  {recommendationOpenSplitByWindow["7d"]} · all {recommendationOpenSplitByWindow.all} ·{" "}
                  {copy.mcpRetryLifecycleRecommendationOverrideStripLabel} · 24h{" "}
                  {recommendationOverrideSplitByWindow["24h"]} · 7d {recommendationOverrideSplitByWindow["7d"]} · all{" "}
                  {recommendationOverrideSplitByWindow.all}
                </p>
              ) : null}
            </div>
          ) : null}
          {!analyticsCompactMode && analyticsSnapshot.recent_events.length > 0 ? (
            <div className="mt-3 space-y-1">
              {analyticsSnapshot.recent_events.slice(0, 5).map((row, idx) => (
                <p key={`${row.event}-${row.module_key}-${idx}`} className="text-[11px] text-white/65">
                  {safeLocalTime(row.at)} · {formatEventLabel(row.event)} · {row.module_key}
                </p>
              ))}
            </div>
          ) : null}
        </details>
      ) : null}
      <AppsToolsModuleGrid
        loading={loading}
        modules={APPS_TOOLS_MODULES_CORE}
        sectionLabel="CORE MODULES"
        policyByModule={policyByModule}
        workspaceByModule={workspaceByModule}
        capabilitiesByModule={capabilitiesByModule}
        headerExtras={mcpModuleHeaderExtras ? { mcp_ops_studio: mcpModuleHeaderExtras } : undefined}
        showMcpAnomalyReset={isRetryAnomalySuppressed}
        onMcpAnomalyReset={() => clearRetryAnomalyAcknowledgment("module_card")}
        mcpAnomalyResetLabel={copy.mcpRetryAnomalyCardResetCta}
        onOpenDetails={(moduleKey) => {
          trackEvent("module_details_open", {
            moduleKey,
            source: "module_card",
          });
          setActiveModuleKey(moduleKey);
        }}
        onTrackModuleOpen={(moduleDef) =>
          trackEvent("module_card_open", {
            moduleKey: moduleDef.moduleKey,
            href: moduleDef.href,
            source: "module_card",
          })}
        onTrackAvailabilityHint={(moduleKey) =>
          trackEvent("module_availability_hint_open", {
            moduleKey,
            source: "availability_hint",
          })}
        onTrackBetaHint={(moduleKey) =>
          trackEvent("module_beta_hint_open", {
            moduleKey,
            source: "beta_hint",
          })}
      />

      {!loading && APPS_TOOLS_MODULES_FROZEN.length > 0 ? (
        <details className="mt-6 rounded-2xl border border-white/10 bg-black/20 p-4">
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
            Frozen modules ({APPS_TOOLS_MODULES_FROZEN.length}) — maintained, not first-revenue priority
          </summary>
          <div className="mt-4">
            <AppsToolsModuleGrid
              loading={false}
              modules={APPS_TOOLS_MODULES_FROZEN}
              sectionLabel="FROZEN"
              policyByModule={policyByModule}
              workspaceByModule={workspaceByModule}
              capabilitiesByModule={capabilitiesByModule}
              onOpenDetails={(moduleKey) => {
                trackEvent("module_details_open", { moduleKey, source: "frozen_module_card" });
                setActiveModuleKey(moduleKey);
              }}
              onTrackModuleOpen={(moduleDef) =>
                trackEvent("module_card_open", {
                  moduleKey: moduleDef.moduleKey,
                  href: moduleDef.href,
                  source: "frozen_module_card",
                })}
              onTrackAvailabilityHint={(moduleKey) =>
                trackEvent("module_availability_hint_open", { moduleKey, source: "frozen_availability_hint" })}
              onTrackBetaHint={(moduleKey) =>
                trackEvent("module_beta_hint_open", { moduleKey, source: "frozen_beta_hint" })}
            />
          </div>
        </details>
      ) : null}

      {activeModuleDef ? (
        <HiveModalShell
          open
          onClose={() => setActiveModuleKey(null)}
          labelledBy="module-details-title"
          align="bottom-sheet"
          zIndexClass="z-[72]"
          initialFocusRef={closeButtonRef}
          panelClassName={`${hiveModalBottomSheetPanelClass} max-h-[min(90dvh,760px)] max-w-2xl`}
        >
            <header className="flex items-start justify-between gap-3 border-b border-(--qs-border) px-4 py-4 sm:px-5">
              <div className="min-w-0">
                <h3 id="module-details-title" className="text-base font-semibold text-(--qs-text)">
                  {activeModuleDef.title} module details
                </h3>
                <p className="mt-1 text-xs text-(--qs-text-3)">
                  Capability contract + governance profile with direct section deep-links.
                </p>
              </div>
              <button
                ref={closeButtonRef}
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                aria-label="Close module details"
                onClick={() => setActiveModuleKey(null)}
              >
                Close
              </button>
            </header>
            <div className="hive-scrollbar min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-5">
              {activeWorkspace ? (
                <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs">
                  <p className="font-medium text-(--qs-text)">{activeWorkspace.label}</p>
                  <p className="mt-1 text-(--qs-text-3)">{activeWorkspace.summary}</p>
                </div>
              ) : null}
              {activeModuleDef.moduleKey === "mcp_ops_studio" && showRetryAnomaly ? (
                <div className="rounded-lg border border-magenta-300/35 bg-magenta-300/10 px-3 py-2 text-xs">
                  <p className="font-medium text-magenta-100">{copy.mcpRetryAnomalyBadge}</p>
                  <p className="mt-1 text-magenta-100/90">{copy.mcpRetryAnomalyActionHint}</p>
                  <div className="mt-2">
                    <Link
                      href="/apps-tools/mcp-ops-studio?section=health#mcp-health"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      onClick={() =>
                        trackEvent("module_section_quick_link", {
                          moduleKey: activeModuleDef.moduleKey,
                          href: "/apps-tools/mcp-ops-studio?section=health#mcp-health",
                          source: "retry_anomaly_hint",
                        })
                      }
                    >
                      {copy.mcpRetryAnomalyActionCta}
                    </Link>
                  </div>
                </div>
              ) : null}

              {activeCapabilities.length > 0 ? (
                <section className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Capability contracts</p>
                  <ul className="space-y-2">
                    {activeCapabilities.map((capability) => (
                      <li key={capability.capability_key} className="rounded-lg border border-white/10 bg-black/20 p-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium text-(--qs-text)">{capability.label}</span>
                          <span className={`rounded-full border px-2 py-0.5 text-[10px] ${riskTone(capability.risk_tier)}`}>
                            {capability.risk_tier}
                          </span>
                          <span className="rounded-full border border-white/20 bg-white/5 px-2 py-0.5 text-[10px] text-white/80">
                            {capability.requires_approval ? "approval" : "auto"}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-(--qs-text-3)">{capability.summary}</p>
                        <p className="mt-2 font-mono text-[10px] text-cyan-100/85">{capability.capability_key}</p>
                        <p className="mt-1 text-[10px] text-(--qs-text-4)">
                          SLA {capability.sla_hint_sec ?? "n/a"}s · deps {capability.dependency_keys.length}
                        </p>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {activeDependencyEdges.length > 0 ? (
                <section className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Dependency graph strip</p>
                  <div className="space-y-2">
                    {activeDependencyEdges.map((edge) => {
                      const targetModule = moduleByKey[edge.ownerModuleKey];
                      return (
                        <div
                          key={`${edge.dependencyKey}:${edge.ownerModuleKey}`}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs"
                        >
                          <div className="min-w-0">
                            <p className="font-mono text-cyan-100/90">{edge.dependencyKey}</p>
                            <p className="text-(--qs-text-3)">
                              Owner module: {targetModule?.title ?? edge.ownerModuleKey}
                            </p>
                          </div>
                          {targetModule ? (
                            <Link
                              href={targetModule.href}
                              className="qs-btn qs-btn--ghost qs-btn--sm"
                              onClick={() =>
                                trackEvent("module_dependency_jump", {
                                  moduleKey: activeModuleDef.moduleKey,
                                  targetModuleKey: targetModule.moduleKey,
                                  href: targetModule.href,
                                  source: "dependency_strip",
                                })}
                            >
                              Jump to module
                            </Link>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                </section>
              ) : null}

              {activePolicy ? (
                <section className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Governance policy pack</p>
                  <div className="grid gap-2 text-xs sm:grid-cols-2">
                    <p className="rounded-lg border border-white/10 bg-black/20 px-3 py-2">
                      <span className="text-(--qs-text-3)">Risk tier</span>
                      <br />
                      <span className="font-medium text-(--qs-text)">{activePolicy.risk_tier}</span>
                    </p>
                    <p className="rounded-lg border border-white/10 bg-black/20 px-3 py-2">
                      <span className="text-(--qs-text-3)">Approval gate</span>
                      <br />
                      <span className="font-medium text-(--qs-text)">
                        {activePolicy.requires_approval ? "Required" : "Not required"}
                      </span>
                    </p>
                    {activePolicy.spend_cap_usd_24h != null ? (
                      <p className="rounded-lg border border-white/10 bg-black/20 px-3 py-2">
                        <span className="text-(--qs-text-3)">Spend cap (24h)</span>
                        <br />
                        <span className="font-medium text-(--qs-text)">${activePolicy.spend_cap_usd_24h}</span>
                      </p>
                    ) : null}
                    {activePolicy.time_limit_sec != null ? (
                      <p className="rounded-lg border border-white/10 bg-black/20 px-3 py-2">
                        <span className="text-(--qs-text-3)">Time limit</span>
                        <br />
                        <span className="font-medium text-(--qs-text)">{activePolicy.time_limit_sec}s</span>
                      </p>
                    ) : null}
                    {activePolicy.rate_limit_max_global != null && activePolicy.rate_limit_window_sec != null ? (
                      <p className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 sm:col-span-2">
                        <span className="text-(--qs-text-3)">Rate limit</span>
                        <br />
                        <span className="font-medium text-(--qs-text)">
                          {activePolicy.rate_limit_max_global} actions / {formatRateWindow(activePolicy.rate_limit_window_sec)}
                        </span>
                      </p>
                    ) : null}
                  </div>
                  {activePolicy.notes.length > 0 ? (
                    <ul className="list-disc space-y-1 pl-5 text-xs text-(--qs-text-2)">
                      {activePolicy.notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  ) : null}
                </section>
              ) : null}

              <section className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">Section quick links</p>
                <div className="grid gap-2">
                  <Link
                    href={activeModuleDef.href}
                    className="qs-btn qs-btn--ghost qs-btn--sm justify-start"
                    onClick={() =>
                      trackEvent("module_section_quick_link", {
                        moduleKey: activeModuleDef.moduleKey,
                        href: activeModuleDef.href,
                        source: "module_detail_home",
                      })}
                  >
                    Open module home
                  </Link>
                  {MODULE_SECTION_DEEP_LINKS[activeModuleDef.moduleKey].map((entry) => (
                    <Link
                      key={entry.href}
                      href={entry.href}
                      className="qs-btn qs-btn--ghost qs-btn--sm justify-start"
                      onClick={() =>
                        trackEvent("module_section_quick_link", {
                          moduleKey: activeModuleDef.moduleKey,
                          href: entry.href,
                          source: "module_detail_section",
                        })}
                    >
                      {entry.label}
                    </Link>
                  ))}
                </div>
              </section>
            </div>
        </HiveModalShell>
      ) : null}
    </>
  );
}
