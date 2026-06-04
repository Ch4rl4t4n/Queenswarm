"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { RefreshCwIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import {
  navigateMcpOpsStudioTab,
  resolveMcpOpsStudioTab,
  type McpOpsStudioTab,
} from "@/lib/apps-tools-routes";
import { useRouteHash } from "@/lib/hooks/use-route-hash";
import { formatRelativeMinutes, resolveMcpSnapshotFreshness } from "@/lib/mcp-ops-observability";
import { V4Card, V4CardHeader } from "@/components/ui/v4";

const ToolGapsPanel = dynamic(
  () => import("@/components/connectors/tool-gaps-panel").then((mod) => mod.ToolGapsPanel),
  { ssr: false },
);

type McpSectionState = "loading" | "ready" | "error";

interface McpCatalogItem {
  provider: string;
  trust_tier: "verified" | "community";
  tool_count: number;
  auth_mode: "oauth" | "api_key";
  template_id?: string | null;
  installed?: boolean;
  integrations_href?: string | null;
}

interface McpInstallItem {
  provider: string;
  requested_by: string;
  stage: "policy_review" | "pending_approval";
  template_id?: string | null;
  integrations_href?: string | null;
}

interface McpHealthItem {
  provider: string;
  status: "healthy" | "degraded" | "cold";
  checked_at: string;
  connector_slug?: string | null;
  failed_calls?: number;
  total_calls?: number;
}

interface McpOpsStudioSnapshot {
  generated_at: string;
  source: "live" | "read_only_mock";
  catalog: McpCatalogItem[];
  install: McpInstallItem[];
  health: McpHealthItem[];
}

/** MCP Ops Studio — embedded in Apps & Tools integrated shell (Catalog · Install · Health subnav). */
export function McpOpsStudioPageClient(): JSX.Element {
  const routeHash = useRouteHash();
  const section = useMemo(() => resolveMcpOpsStudioTab({ hash: routeHash }), [routeHash]);
  const [sectionState, setSectionState] = useState<McpSectionState>("loading");
  const [sectionError, setSectionError] = useState<string | null>(null);
  const [catalogItems, setCatalogItems] = useState<McpCatalogItem[]>([]);
  const [installItems, setInstallItems] = useState<McpInstallItem[]>([]);
  const [healthItems, setHealthItems] = useState<McpHealthItem[]>([]);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [snapshotSource, setSnapshotSource] = useState<McpOpsStudioSnapshot["source"] | null>(null);

  const freshness = resolveMcpSnapshotFreshness(generatedAt);
  const freshnessLabel =
    freshness.tone === "fresh" ? "Fresh snapshot" : freshness.tone === "aging" ? "Aging snapshot" : "Stale snapshot";

  useEffect(() => {
    if (!routeHash && typeof window !== "undefined") {
      navigateMcpOpsStudioTab("catalog");
    }
  }, [routeHash]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const legacySection = params.get("section");
    if (legacySection === "catalog" || legacySection === "install" || legacySection === "health") {
      navigateMcpOpsStudioTab(legacySection as McpOpsStudioTab);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const load = async (): Promise<void> => {
      setSectionState("loading");
      setSectionError(null);
      try {
        const snapshot = await hiveGet<McpOpsStudioSnapshot>("operator/apps-tools/mcp-ops-studio/snapshot");
        if (!active) return;
        setCatalogItems(Array.isArray(snapshot.catalog) ? snapshot.catalog : []);
        setInstallItems(Array.isArray(snapshot.install) ? snapshot.install : []);
        setHealthItems(Array.isArray(snapshot.health) ? snapshot.health : []);
        setGeneratedAt(typeof snapshot.generated_at === "string" ? snapshot.generated_at : null);
        setSnapshotSource(snapshot.source);
        setSectionState("ready");
      } catch (error) {
        if (!active) return;
        const message =
          error instanceof HiveApiError
            ? error.message
            : error instanceof Error
              ? error.message
              : "Failed to load MCP Ops snapshot.";
        setSectionError(message);
        setSectionState("error");
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [reloadToken]);

  const rerunSectionLoad = useCallback(() => {
    void hivePostJson("operator/apps-tools-index/events", {
      event: "mcp_ops_snapshot_retry",
      module_key: "mcp_ops_studio",
      source: "mcp_ops_studio_retry",
      href: typeof window !== "undefined" ? window.location.pathname + window.location.search : undefined,
    }).catch(() => {
      /* best-effort telemetry */
    });
    setReloadToken((current) => current + 1);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-(--qs-text)">MCP Ops Studio</p>
            <ModulePolicyPackPill moduleKey="mcp_ops_studio" />
          </div>
          <p className="mt-0.5 text-xs text-(--qs-text-3)">
            Catalog-first MCP provider operations — discovery, governed installs, and runtime health.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/integrations?tab=hub&hubSection=roster" className="qs-btn qs-btn--ghost qs-btn--sm">
            Integrations Hub
          </Link>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            onClick={() => setReloadToken((value) => value + 1)}
          >
            <RefreshCwIcon className="size-3.5" aria-hidden />
            Refresh
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs text-(--qs-text-3)">
        <p>
          Snapshot: {snapshotSource ?? "n/a"} · refreshed {formatRelativeMinutes(freshness.ageMinutes)}
        </p>
        <span
          className={`rounded-full border px-2 py-0.5 ${
            freshness.tone === "fresh"
              ? "border-emerald-300/45 bg-emerald-300/10 text-emerald-100"
              : freshness.tone === "aging"
                ? "border-amber-300/45 bg-amber-300/10 text-amber-100"
                : "border-red-300/45 bg-red-300/10 text-red-100"
          }`}
          aria-live="polite"
        >
          {freshnessLabel}
        </span>
      </div>

      {actionNotice ? (
        <div
          role="status"
          className="rounded-xl border border-cyan-300/35 bg-cyan-300/10 px-3 py-2 text-xs text-cyan-100"
        >
          {actionNotice}
        </div>
      ) : null}

      {sectionState === "loading" ? (
        <V4Card>
          <V4CardHeader
            title="Loading MCP Ops Studio…"
            description="Hydrating read-only backend snapshot for this workspace lane."
          />
          <div className="space-y-2" aria-hidden>
            <div className="h-10 animate-pulse rounded-lg bg-white/10" />
            <div className="h-10 animate-pulse rounded-lg bg-white/10" />
          </div>
        </V4Card>
      ) : null}

      {sectionState === "error" ? (
        <V4Card>
          <V4CardHeader
            title="MCP Ops section unavailable"
            description="Read-only backend snapshot failed. Retry without mutating runtime state."
          />
          <p className="text-sm text-(--qs-text-3)">{sectionError ?? "Unknown MCP error."}</p>
          <div className="mt-3">
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={rerunSectionLoad}>
              Retry section load
            </button>
          </div>
        </V4Card>
      ) : null}

      {sectionState === "ready" && section === "catalog" ? (
        <ToolGapsPanel onInstalled={() => setReloadToken((c) => c + 1)} />
      ) : null}

      {section === "catalog" && sectionState === "ready" ? (
        <V4Card id="mcp-catalog">
          <V4CardHeader
            title="Provider catalog discovery"
            description="Phase3 marketplace templates from Integrations — install from hub to activate tools."
          />
          {catalogItems.length === 0 ? (
            <p className="text-sm text-(--qs-text-3)">No catalog providers matched this view.</p>
          ) : (
            <div className="space-y-2">
              {catalogItems.map((row) => (
                <div
                  key={`${row.provider}-${row.template_id ?? "row"}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs"
                >
                  <span className="font-medium text-(--qs-text)">{row.provider}</span>
                  <span className="text-(--qs-text-3)">
                    {row.trust_tier} · {row.tool_count} tools · {row.auth_mode}
                    {row.installed ? " · installed" : ""}
                  </span>
                  {row.integrations_href ? (
                    <Link href={row.integrations_href} className="text-cyan underline">
                      {row.installed ? "Manage" : "Install"}
                    </Link>
                  ) : null}
                </div>
              ))}
            </div>
          )}
          <div className="mt-3">
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={() => {
                setActionNotice("Catalog snapshot refreshed from read-only backend source.");
                setReloadToken((current) => current + 1);
              }}
            >
              Refresh catalog snapshot
            </button>
          </div>
        </V4Card>
      ) : null}

      {section === "install" && sectionState === "ready" ? (
        <V4Card id="mcp-install">
          <V4CardHeader
            title="Recommended installs"
            description="Featured marketplace templates not yet installed on this workspace."
          />
          {installItems.length === 0 ? (
            <p className="text-sm text-(--qs-text-3)">All featured templates installed — browse catalog for more.</p>
          ) : (
            <div className="space-y-2">
              {installItems.map((row) => (
                <div
                  key={`${row.provider}-${row.template_id ?? row.requested_by}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs"
                >
                  <span className="font-medium text-(--qs-text)">{row.provider}</span>
                  <span className="text-(--qs-text-3)">
                    {row.stage.replaceAll("_", " ")} · {row.requested_by}
                  </span>
                  {row.integrations_href ? (
                    <Link href={row.integrations_href} className="text-cyan underline">
                      Install in Integrations
                    </Link>
                  ) : null}
                </div>
              ))}
            </div>
          )}
          <div className="mt-3">
            <Link href="/integrations?tab=marketplace" className="qs-btn qs-btn--ghost qs-btn--sm">
              Open marketplace
            </Link>
          </div>
        </V4Card>
      ) : null}

      {section === "health" && sectionState === "ready" ? (
        <V4Card id="mcp-health">
          <V4CardHeader
            title="Runtime health diagnostics"
            description="Per-connector invoke metrics from agent sessions (Redis, 24h window)."
          />
          {healthItems.length === 0 ? (
            <p className="text-sm text-(--qs-text-3)">No installed connectors with traffic yet — install from catalog.</p>
          ) : (
            <div className="space-y-2">
              {healthItems.map((row) => (
                <div
                  key={`${row.provider}-${row.checked_at}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs"
                >
                  <span className="font-medium text-(--qs-text)">{row.provider}</span>
                  <span className="text-(--qs-text-3)">
                    {row.status}
                    {typeof row.total_calls === "number" && row.total_calls > 0
                      ? ` · ${row.failed_calls ?? 0}/${row.total_calls} failed`
                      : " · no traffic"}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div className="mt-3">
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={() => {
                setActionNotice("Health metrics refreshed from live connector counters.");
                setReloadToken((current) => current + 1);
              }}
            >
              Refresh health metrics
            </button>
          </div>
        </V4Card>
      ) : null}
    </div>
  );
}
