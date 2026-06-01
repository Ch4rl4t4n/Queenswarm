"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import type { ReactNode } from "react";
import { useMemo } from "react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import {
  APPS_TOOLS_MODULES,
  APPS_TOOLS_MODULE_CATEGORY,
  appsToolsModuleAgentUsage,
  type AppsToolsModuleDef,
} from "@/lib/apps-tools-modules";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

type PolicyRiskTier = "read" | "write" | "publish" | "financial";

interface ModulePolicyPack {
  module_key: AppsToolsModuleDef["moduleKey"];
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
  dependency_keys: string[];
}

const STATUS_LABEL: Record<AppsToolsModuleDef["status"], string> = {
  live: "Live",
  beta: "Beta",
  stub: "Stub",
};

function statusBadgeTone(
  moduleDef: AppsToolsModuleDef,
  workspace: CapabilityWorkspace | null | undefined,
): "ok" | "warn" | "err" | "info" {
  if (moduleDef.status === "stub" || workspace?.enabled === false) return "err";
  if (moduleDef.status === "beta") return "warn";
  return "ok";
}

function statusBadgeLabel(
  moduleDef: AppsToolsModuleDef,
  workspace: CapabilityWorkspace | null | undefined,
): string {
  if (moduleDef.status === "stub" || workspace?.enabled === false) return "not available";
  if (moduleDef.status === "beta") return "beta · guarded";
  return "active";
}

function riskBadgeTone(riskTier: PolicyRiskTier): "ok" | "warn" | "err" | "info" {
  if (riskTier === "financial") return "err";
  if (riskTier === "publish") return "warn";
  if (riskTier === "write") return "info";
  return "ok";
}

function compactApprovalLabel(requiresApproval: boolean): string {
  return requiresApproval ? "approval gate" : "auto allowed";
}

function formatRateWindow(seconds: number): string {
  if (seconds < 3600) {
    return `${Math.max(1, Math.round(seconds / 60))}m`;
  }
  return `${Math.max(1, Math.round(seconds / 3600))}h`;
}

function compactGovernanceSummary(policy: ModulePolicyPack): string {
  const parts = [compactApprovalLabel(policy.requires_approval)];
  if (policy.cooldown_sec) {
    parts.push(`cooldown ${policy.cooldown_sec}s`);
  }
  if (policy.rate_limit_max_global && policy.rate_limit_window_sec) {
    parts.push(`${policy.rate_limit_max_global}/${formatRateWindow(policy.rate_limit_window_sec)}`);
  }
  return parts.join(" · ");
}

export interface AppsToolsModuleGridProps {
  loading: boolean;
  policyByModule: Record<string, ModulePolicyPack>;
  workspaceByModule: Record<string, CapabilityWorkspace>;
  capabilitiesByModule: Record<string, CapabilityContract[]>;
  headerExtras?: Partial<Record<AppsToolsModuleDef["moduleKey"], ReactNode>>;
  showMcpAnomalyReset?: boolean;
  onMcpAnomalyReset?: () => void;
  mcpAnomalyResetLabel?: string;
  onOpenDetails: (moduleKey: AppsToolsModuleDef["moduleKey"]) => void;
  onTrackModuleOpen: (moduleDef: AppsToolsModuleDef) => void;
  onTrackAvailabilityHint: (moduleKey: AppsToolsModuleDef["moduleKey"]) => void;
  onTrackBetaHint: (moduleKey: AppsToolsModuleDef["moduleKey"]) => void;
}

/** Apps & Tools module index — marketplace-style cards + numbered pagination. */
export function AppsToolsModuleGrid({
  loading,
  policyByModule,
  workspaceByModule,
  capabilitiesByModule,
  headerExtras,
  showMcpAnomalyReset = false,
  onMcpAnomalyReset,
  mcpAnomalyResetLabel = "Reset anomaly ack",
  onOpenDetails,
  onTrackModuleOpen,
  onTrackAvailabilityHint,
  onTrackBetaHint,
}: AppsToolsModuleGridProps): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const pagination = usePaginatedSlice(
    APPS_TOOLS_MODULES,
    pageSize,
    `${pageSize}|${APPS_TOOLS_MODULES.length}|${loading}`,
  );

  const totalLabel = useMemo(() => `${APPS_TOOLS_MODULES.length} modules`, []);

  if (loading) {
    return (
      <div className="apps-tools-module-grid-wrap mt-4 min-w-0 space-y-3">
        <div className="apps-tools-module-grid-head flex flex-wrap items-center gap-2">
          <p className="hub-catalog-section-head__label">ALL MODULES</p>
          <V4Badge tone="info">{totalLabel}</V4Badge>
        </div>
        <div className="hub-catalog-grid">
          {APPS_TOOLS_MODULES.map((moduleDef) => (
            <article
              key={`skeleton-${moduleDef.slug}`}
              className="apps-tools-module-card v4-dream-cycle-card animate-pulse"
              aria-hidden
            >
              <div className="h-4 w-40 rounded bg-white/15" />
              <div className="mt-3 h-3 w-full rounded bg-white/10" />
              <div className="mt-2 h-16 w-full rounded bg-white/10" />
              <div className="mt-4 h-8 w-28 rounded bg-white/10" />
            </article>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="apps-tools-module-grid-wrap mt-4 min-w-0 space-y-3">
      <div className="apps-tools-module-grid-head flex flex-wrap items-center gap-2">
        <p className="hub-catalog-section-head__label">ALL MODULES</p>
        <V4Badge tone="info">{totalLabel}</V4Badge>
      </div>

      <ViewportBoundedPanel
        className="v4-recipe-catalog-panel apps-tools-module-grid-panel"
        footer={
          <ListPaginator
            page={pagination.page}
            totalPages={pagination.totalPages}
            totalItems={pagination.totalItems}
            pageSize={pageSize}
            onPageChange={pagination.setPage}
          />
        }
      >
        <div className="hub-catalog-grid">
          {pagination.slice.map((moduleDef) => {
            const policy = policyByModule[moduleDef.moduleKey];
            const workspace = workspaceByModule[moduleDef.moduleKey];
            const moduleCapabilities = capabilitiesByModule[moduleDef.moduleKey] ?? [];
            const moduleUnavailable = moduleDef.status === "stub" || workspace?.enabled === false;
            const moduleDegraded = !moduleUnavailable && moduleDef.status === "beta";
            const unavailableHintId = `${moduleDef.slug}-availability-hint`;
            const degradedHintId = `${moduleDef.slug}-degraded-hint`;
            const extraBadges = headerExtras?.[moduleDef.moduleKey];

            return (
              <article key={moduleDef.slug} className="apps-tools-module-card v4-dream-cycle-card flex h-full flex-col gap-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 space-y-1">
                  <p className="qs-card-title text-sm font-semibold text-(--qs-text)">{moduleDef.title}</p>
                    <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
                      {APPS_TOOLS_MODULE_CATEGORY[moduleDef.moduleKey]}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                    {extraBadges}
                    <V4Badge tone={statusBadgeTone(moduleDef, workspace)}>{statusBadgeLabel(moduleDef, workspace)}</V4Badge>
                    <V4Badge tone="info">{STATUS_LABEL[moduleDef.status]}</V4Badge>
                  </div>
                </div>

                <p className="text-xs leading-relaxed text-(--qs-text-3)">{moduleDef.summary}</p>

                <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
                  <p className="v4-field-label text-[10px] text-cyan-300/90">How agents use this</p>
                  <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">{appsToolsModuleAgentUsage(moduleDef)}</p>
                </div>

                <p className="font-mono text-[11px] text-(--qs-text-3)">
                  {moduleDef.slug} · {moduleDef.capabilityKeys.length} capabilities
                </p>

                {policy ? (
                  <>
                    <p className="text-[11px] text-(--qs-text-3)">{compactGovernanceSummary(policy)}</p>
                    <div className="flex flex-wrap gap-2 qs-tag-row">
                      <V4Badge tone={riskBadgeTone(policy.risk_tier)}>{policy.risk_tier}</V4Badge>
                      <V4Badge tone="info">{compactApprovalLabel(policy.requires_approval)}</V4Badge>
                      {policy.cooldown_sec ? <V4Badge tone="warn">cooldown {policy.cooldown_sec}s</V4Badge> : null}
                      {moduleCapabilities.length > 0 ? (
                        <V4Badge tone="info">{moduleCapabilities.length} capabilities</V4Badge>
                      ) : null}
                    </div>
                  </>
                ) : null}

                <Link
                  href={moduleDef.href}
                  className="inline-flex items-center gap-1.5 text-xs text-pollen hover:underline"
                  onClick={() => onTrackModuleOpen(moduleDef)}
                >
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                  Module workspace
                </Link>

                <div className="v4-dream-cycle-card-actions mt-auto flex flex-wrap gap-2">
                  {moduleDef.moduleKey === "mcp_ops_studio" && showMcpAnomalyReset && onMcpAnomalyReset ? (
                    <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={onMcpAnomalyReset}>
                      {mcpAnomalyResetLabel}
                    </button>
                  ) : null}
                  {policy ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      onClick={() => onOpenDetails(moduleDef.moduleKey)}
                    >
                      Module details
                    </button>
                  ) : null}
                  {moduleUnavailable ? (
                    <button
                      type="button"
                      className={cn("qs-btn qs-btn--primary qs-btn--sm min-w-[5.5rem] cursor-not-allowed opacity-60")}
                      disabled
                      aria-disabled="true"
                      aria-describedby={unavailableHintId}
                    >
                      Configure
                    </button>
                  ) : (
                    <Link
                      href={moduleDef.href}
                      className="qs-btn qs-btn--primary qs-btn--sm min-w-[5.5rem]"
                      aria-describedby={moduleDegraded ? degradedHintId : undefined}
                      onClick={() => onTrackModuleOpen(moduleDef)}
                    >
                      Configure
                    </Link>
                  )}
                </div>

                {moduleUnavailable ? (
                  <p id={unavailableHintId} className="text-xs text-amber-100/85">
                    This module is not available yet. Capability contract is visible, but execution is disabled.
                  </p>
                ) : null}
                {moduleUnavailable ? (
                  <details
                    className="mt-1"
                    onToggle={(event) => {
                      if (event.currentTarget.open) {
                        onTrackAvailabilityHint(moduleDef.moduleKey);
                      }
                    }}
                  >
                    <summary className="inline-flex cursor-pointer items-center rounded-md px-1 text-xs font-medium text-amber-100/90">
                      Availability hint
                    </summary>
                    <p className="mt-1 text-xs text-white/70">
                      Execution entry stays disabled until this workspace becomes live, but governance and contract signals stay visible for planning.
                    </p>
                  </details>
                ) : null}
                {moduleDegraded ? (
                  <p id={degradedHintId} className="text-xs text-cyan-100/85">
                    Beta module is available with guarded execution paths. Validate policy details before critical runs.
                  </p>
                ) : null}
                {moduleDegraded ? (
                  <details
                    className="mt-1"
                    onToggle={(event) => {
                      if (event.currentTarget.open) {
                        onTrackBetaHint(moduleDef.moduleKey);
                      }
                    }}
                  >
                    <summary className="inline-flex cursor-pointer items-center rounded-md px-1 text-xs font-medium text-cyan-100/90">
                      Beta readiness hint
                    </summary>
                    <p className="mt-1 text-xs text-white/70">
                      Use module details to verify approvals, cooldown, and limits before enabling higher-risk automation flows.
                    </p>
                  </details>
                ) : null}
              </article>
            );
          })}
        </div>
      </ViewportBoundedPanel>
    </div>
  );
}
