"use client";

import { Activity, PackageCheck, Search } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ModulePolicyPackPill } from "@/components/apps-tools/module-policy-pack-pill";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { formatRelativeMinutes, resolveMcpSnapshotFreshness } from "@/lib/mcp-ops-observability";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";

type McpOpsSection = "catalog" | "install" | "health";
type McpSectionState = "loading" | "ready" | "error";

interface McpCatalogItem {
  provider: string;
  trust_tier: "verified" | "community";
  tool_count: number;
  auth_mode: "oauth" | "api_key";
}

interface McpInstallItem {
  provider: string;
  requested_by: string;
  stage: "policy_review" | "pending_approval";
}

interface McpHealthItem {
  provider: string;
  status: "healthy" | "degraded";
  checked_at: string;
}

interface McpOpsStudioSnapshot {
  generated_at: string;
  source: "read_only_mock";
  catalog: McpCatalogItem[];
  install: McpInstallItem[];
  health: McpHealthItem[];
}

const SECTION_TO_HASH: Record<McpOpsSection, string> = {
  catalog: "mcp-catalog",
  install: "mcp-install",
  health: "mcp-health",
};

function sectionFromHash(hash: string): McpOpsSection | null {
  const key = hash.replace(/^#/, "").trim().toLowerCase();
  if (key === "mcp-catalog") return "catalog";
  if (key === "mcp-install") return "install";
  if (key === "mcp-health") return "health";
  return null;
}

function sectionFromQuery(raw: string | null): McpOpsSection | null {
  if (raw === "catalog" || raw === "install" || raw === "health") {
    return raw;
  }
  return null;
}

export function McpOpsStudioPageClient() {
  const searchParams = useSearchParams();
  const [section, setSection] = useState<McpOpsSection>("catalog");
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

  const updateUrl = useCallback((next: McpOpsSection) => {
    const hash = SECTION_TO_HASH[next];
    window.history.replaceState(null, "", `/apps-tools/mcp-ops-studio?section=${next}#${hash}`);
  }, []);

  useEffect(() => {
    const fromQuery = sectionFromQuery(searchParams.get("section"));
    const fromHash = sectionFromHash(typeof window !== "undefined" ? window.location.hash : "");
    const next = fromQuery ?? fromHash;
    if (next) {
      setSection(next);
    }
  }, [searchParams]);

  useEffect(() => {
    const target = document.getElementById(SECTION_TO_HASH[section]);
    if (target) {
      target.scrollIntoView({ behavior: scrollBehaviorForMotion(), block: "start" });
    }
  }, [section]);

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
      // Retry telemetry is best-effort and must never block operators.
    });
    setReloadToken((current) => current + 1);
  }, []);

  return (
    <HivePageShell
      title="MCP Ops Studio"
      subtitle="Catalog-first MCP provider operations lane for discovery, governed installs, and runtime health."
      status={<ModulePolicyPackPill moduleKey="mcp_ops_studio" />}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/integrations?tab=hub&hubSection=roster" className="qs-btn qs-btn--primary qs-btn--sm">
            Open Integrations Hub
          </Link>
          <Link href="/apps-tools" className="qs-btn qs-btn--ghost qs-btn--sm">
            Back to Apps & Tools
          </Link>
        </div>
      }
      subnav={
        <>
          <div className="flex flex-wrap items-center gap-2 text-xs text-(--qs-text-3)">
            <p>
              Snapshot source: {snapshotSource ?? "n/a"} · refreshed {formatRelativeMinutes(freshness.ageMinutes)}
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
          <HiveSubnavRow
            items={[
              { id: "catalog", label: "Catalog", icon: Search },
              { id: "install", label: "Install queue", icon: PackageCheck },
              { id: "health", label: "Health checks", icon: Activity },
            ]}
            activeId={section}
            onChange={(id) => {
              const next = id as McpOpsSection;
              setSection(next);
              updateUrl(next);
            }}
            ariaLabel="MCP ops studio sections"
            menuKey="apps-tools-mcp-ops-studio"
          />
        </>
      }
    >
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
            title="Loading MCP Ops Studio section..."
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
          <p className="text-sm text-(--qs-text-3)">{sectionError ?? "Unknown MCP mock error."}</p>
          <div className="mt-3">
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={rerunSectionLoad}>
              Retry section load
            </button>
          </div>
        </V4Card>
      ) : null}

      {section === "catalog" && sectionState === "ready" ? (
        <V4Card id="mcp-catalog">
          <V4CardHeader
            title="Provider catalog discovery"
            description="Read-only provider list with trust metadata, policy fit, and capability compatibility signals."
          />
          {catalogItems.length === 0 ? (
            <p className="text-sm text-(--qs-text-3)">No catalog providers matched this view.</p>
          ) : (
            <div className="space-y-2">
              {catalogItems.map((row) => (
                <div
                  key={row.provider}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs"
                >
                  <span className="font-medium text-(--qs-text)">{row.provider}</span>
                  <span className="text-(--qs-text-3)">
                      {row.trust_tier} · {row.tool_count} tools · {row.auth_mode}
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
            title="Governed install queue"
            description="Approval-gated install and lifecycle actions with immutable operator audit trail."
          />
          {installItems.length === 0 ? (
            <p className="text-sm text-(--qs-text-3)">No install requests queued right now.</p>
          ) : (
            <div className="space-y-2">
              {installItems.map((row) => (
                <div
                  key={`${row.provider}-${row.requested_by}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs"
                >
                  <span className="font-medium text-(--qs-text)">{row.provider}</span>
                  <span className="text-(--qs-text-3)">
                    {row.stage.replaceAll("_", " ")} · by {row.requested_by}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div className="mt-3">
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={() => setActionNotice("Install request queued in read-only preview mode.")}
            >
              Queue governed install
            </button>
          </div>
        </V4Card>
      ) : null}

      {section === "health" && sectionState === "ready" ? (
        <V4Card id="mcp-health">
          <V4CardHeader
            title="Runtime health diagnostics"
            description="Connector/tool availability probes and auth state diagnostics for fast remediation."
          />
          {healthItems.length === 0 ? (
            <p className="text-sm text-(--qs-text-3)">No health probes yet for this window.</p>
          ) : (
            <div className="space-y-2">
              {healthItems.map((row) => (
                <div
                  key={`${row.provider}-${row.checked_at}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs"
                >
                  <span className="font-medium text-(--qs-text)">{row.provider}</span>
                  <span className="text-(--qs-text-3)">
                    {row.status} · {row.checked_at}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div className="mt-3">
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={() => setActionNotice("Health probe scheduled in read-only preview mode.")}
            >
              Run health probe
            </button>
          </div>
        </V4Card>
      ) : null}
    </HivePageShell>
  );
}
