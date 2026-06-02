"use client";

import { ExternalLink, Loader2, Shield, Zap } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import { celebrateVerifiedOutcome } from "@/lib/celebrate-verified-outcome";
import {
  clearPendingLiveAction,
  type BrowserFallbackLane,
  type ExecutionMode,
  type PendingApprovalsSnapshot,
  type PendingLiveAction,
} from "@/lib/execution-studio-shared-types";
import { dispatchOperatorPendingRefresh, studioPendingActionHash, supervisorSessionHref } from "@/lib/operator-pending-events";
import { retryWithBackoff } from "@/lib/retry-with-backoff";
import { cn } from "@/lib/utils";

export interface ExecutionStudioLiveApprovalsPanelProps {
  pendingApprovals: PendingApprovalsSnapshot | undefined;
  browserFallback: BrowserFallbackLane | undefined;
  defaultMode: ExecutionMode;
  liveRequiresApproval: boolean;
  loading: boolean;
  onPendingApprovalsUpdate: (pending: PendingApprovalsSnapshot) => void;
  onError: (message: string | null) => void;
  onExecuteResult: (message: string | null) => void;
  onReloadOverview: () => Promise<void>;
  onNavigateToWorkspace?: () => void;
}

function ExecutionStudioLiveApprovalsPanelInner({
  pendingApprovals,
  browserFallback,
  defaultMode,
  liveRequiresApproval,
  loading,
  onPendingApprovalsUpdate,
  onError,
  onExecuteResult,
  onReloadOverview,
  onNavigateToWorkspace,
}: ExecutionStudioLiveApprovalsPanelProps) {
  const [browserBusy, setBrowserBusy] = useState(false);
  const [browserResult, setBrowserResult] = useState<string | null>(null);
  const [externalLiveBusyKey, setExternalLiveBusyKey] = useState<string | null>(null);
  const [highlightPendingId, setHighlightPendingId] = useState<string | null>(null);
  const lastConfirmAtRef = useRef(0);
  const confirmCooldownMs = 2_000;

  const pendingLiveActions = pendingApprovals?.live_actions ?? [];

  const pendingBrowserLive = useMemo(
    () => (pendingApprovals?.browser_pending ?? 0) > 0,
    [pendingApprovals?.browser_pending],
  );

  const guardConfirmCooldown = useCallback((): boolean => {
    const now = Date.now();
    if (now - lastConfirmAtRef.current < confirmCooldownMs) {
      toast.message("Please wait a moment before confirming again.");
      return false;
    }
    lastConfirmAtRef.current = now;
    return true;
  }, [confirmCooldownMs]);

  useEffect(() => {
    if (loading || typeof window === "undefined") return;
    const hash = window.location.hash.replace(/^#/, "");
    if (!hash.startsWith("pending-")) return;
    onNavigateToWorkspace?.();
    const scrollTarget = () => {
      const el = document.getElementById(hash);
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      setHighlightPendingId(hash);
      window.setTimeout(() => setHighlightPendingId(null), 2400);
    };
    window.setTimeout(scrollTarget, 120);
  }, [loading, onNavigateToWorkspace, pendingLiveActions.length]);

  const runBrowserFallback = useCallback(async () => {
    setBrowserBusy(true);
    setBrowserResult(null);
    onError(null);
    try {
      const out = await hivePostJson<{ ok: boolean; mode: ExecutionMode; message?: string; error?: string }>(
        "execution-studio/browser/step",
        {
          goal: "Verify external page reachable when connectors fail",
          start_url: "https://queenswarm.love",
          mode: defaultMode,
        },
      );
      setBrowserResult(out.message ?? out.error ?? (out.ok ? "Browser step OK" : "Browser step failed"));
      await onReloadOverview();
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Browser fallback step failed.");
    } finally {
      setBrowserBusy(false);
    }
  }, [defaultMode, onError, onReloadOverview]);

  const runBrowserLiveConfirm = useCallback(async () => {
    if (!guardConfirmCooldown()) return;
    setBrowserBusy(true);
    setBrowserResult(null);
    onError(null);
    try {
      const out = await retryWithBackoff(() =>
        hivePostJson<{
          ok: boolean;
          mode: ExecutionMode;
          message?: string;
          error?: string;
          retry_after_sec?: number;
        }>("execution-studio/browser/step", {
          goal: "Operator-confirmed live browser verification",
          start_url: "https://queenswarm.love",
          mode: "live",
          operator_confirmed: true,
        }),
      );
      if (out.error === "confirm_throttled") {
        toast.message(out.message ?? "Please wait before confirming again.");
        return;
      }
      setBrowserResult(out.message ?? out.error ?? (out.ok ? "Live browser step OK" : "Live browser step failed"));
      if (out.ok && pendingApprovals) {
        onPendingApprovalsUpdate(clearPendingLiveAction(pendingApprovals, { type: "browser" }));
        dispatchOperatorPendingRefresh({ clearedAction: { type: "browser" } });
        toast.success("Live browser step verified.");
        void celebrateVerifiedOutcome();
      }
      await onReloadOverview();
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Live browser step failed.");
    } finally {
      setBrowserBusy(false);
    }
  }, [guardConfirmCooldown, onError, onPendingApprovalsUpdate, onReloadOverview, pendingApprovals]);

  const runExternalLiveConfirm = useCallback(
    async (action: PendingLiveAction) => {
      if (!action.connector_slug) return;
      if (!guardConfirmCooldown()) return;
      const busyKey = `${action.connector_slug}:${action.tool_name ?? "search"}`;
      setExternalLiveBusyKey(busyKey);
      onError(null);
      try {
        const out = await retryWithBackoff(() =>
          hivePostJson<{ ok: boolean; message?: string; error?: string; retry_after_sec?: number }>(
            "execution-studio/execute",
            {
              connector_slug: action.connector_slug,
              tool_name: action.tool_name ?? "search",
              arguments: {},
              mode: "live",
              operator_confirmed: true,
            },
          ),
        );
        if (out.error === "confirm_throttled") {
          toast.message(out.message ?? "Please wait before confirming again.");
          return;
        }
        onExecuteResult(out.message ?? out.error ?? (out.ok ? "Live connector step OK" : "Live connector step failed"));
        if (out.ok && pendingApprovals) {
          onPendingApprovalsUpdate(clearPendingLiveAction(pendingApprovals, action));
          dispatchOperatorPendingRefresh({
            clearedAction: {
              type: "external",
              connector_slug: action.connector_slug,
              tool_name: action.tool_name,
            },
          });
          toast.success(`Live connector verified: ${action.connector_slug}`);
          void celebrateVerifiedOutcome();
        }
        await onReloadOverview();
      } catch (exc) {
        onError(exc instanceof HiveApiError ? exc.message : "Live connector confirmation failed.");
      } finally {
        setExternalLiveBusyKey(null);
      }
    },
    [guardConfirmCooldown, onError, onExecuteResult, onPendingApprovalsUpdate, onReloadOverview, pendingApprovals],
  );

  const browserSupervisorSessionId = pendingLiveActions.find((row) => row.type === "browser")?.supervisor_session_id;

  if (
    pendingLiveActions.length === 0
    && !pendingBrowserLive
    && !browserFallback
  ) {
    return null;
  }

  return (
    <>
      {pendingLiveActions.length > 0 ? (
        <div id="studio-pending-live" className="qs-bubble qs-bubble--tint-amber shrink-0 space-y-2 p-4">
          <p className="text-sm font-semibold text-pollen">Pending live confirmations ({pendingApprovals?.count ?? 0})</p>
          <ul className="space-y-2">
            {pendingLiveActions.map((action) => {
              const key = `${action.type}-${action.connector_slug ?? "browser"}-${action.at ?? action.message ?? ""}`;
              const actionId = studioPendingActionHash(action);
              const busy =
                action.type === "external" &&
                externalLiveBusyKey === `${action.connector_slug}:${action.tool_name ?? "search"}`;
              return (
                <li
                  key={key}
                  id={actionId}
                  className={cn(
                    "qs-bubble-inner flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-xs transition-shadow",
                    highlightPendingId === actionId && "ring-2 ring-pollen/70",
                  )}
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-(--qs-text)">
                      {action.type === "browser" ? "Browser harness live" : `Connector ${action.connector_slug}`}
                    </p>
                    <p className="mt-0.5 text-(--qs-text-3)">{action.message ?? "Awaiting operator confirmation"}</p>
                    {action.supervisor_session_id ? (
                      <Link
                        href={supervisorSessionHref(action.supervisor_session_id)}
                        className="mt-1 inline-flex items-center gap-1 text-[10px] text-cyan hover:text-pollen"
                      >
                        <ExternalLink className="h-3 w-3" aria-hidden />
                        Open supervisor session
                      </Link>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {action.type === "browser" ? (
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm gap-2"
                        disabled={browserBusy}
                        onClick={() => void runBrowserLiveConfirm()}
                      >
                        Confirm live
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm gap-2"
                        disabled={!!busy}
                        onClick={() => void runExternalLiveConfirm(action)}
                      >
                        {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
                        Confirm live connector
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {pendingBrowserLive ? (
        <div className="qs-bubble qs-bubble--tint-magenta shrink-0 px-4 py-3">
          <p className="text-sm font-semibold text-magenta">Browser live step pending approval</p>
          <p className="mt-1 text-xs text-(--qs-text-3)">
            Supervisor auto-simulated browser fallback after connector failure. Confirm live harness step below.
          </p>
          {browserSupervisorSessionId ? (
            <Link
              href={supervisorSessionHref(browserSupervisorSessionId)}
              className="mt-2 inline-flex items-center gap-1 text-xs text-cyan hover:text-pollen"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              View originating supervisor session
            </Link>
          ) : null}
        </div>
      ) : null}

      {browserFallback ? (
        <div className="qs-bubble shrink-0 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-(--qs-text)">Browser harness fallback</p>
              <p className="mt-1 text-xs text-(--qs-text-3)">{browserFallback.description}</p>
              <p className="mt-2 break-all font-mono text-[10px] text-(--qs-text-4)">
                Role: {browserFallback.supervisor_role} · {browserFallback.execute_api ?? browserFallback.sessions_api}
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:shrink-0 sm:items-end">
              <V4Badge tone={browserFallback.enabled ? "ok" : "warn"} className="shrink-0 whitespace-nowrap">
                {browserFallback.enabled ? "Harness ON" : "Harness off"}
              </V4Badge>
              <div className="flex flex-wrap gap-2 sm:justify-end">
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm flex-1 justify-center gap-2 sm:flex-none"
                  disabled={browserBusy || !browserFallback.enabled}
                  onClick={() => void runBrowserFallback()}
                >
                  {browserBusy ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  ) : (
                    <Zap className="h-4 w-4" aria-hidden />
                  )}
                  Test browser fallback
                </button>
                {liveRequiresApproval ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm flex-1 justify-center gap-2 sm:flex-none"
                    disabled={browserBusy || !browserFallback.enabled}
                    onClick={() => void runBrowserLiveConfirm()}
                  >
                    {browserBusy ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Shield className="h-4 w-4" aria-hidden />
                    )}
                    Confirm live browser step
                  </button>
                ) : null}
              </div>
            </div>
          </div>
          {browserResult ? <p className="mt-2 text-xs text-(--qs-text-3)">{browserResult}</p> : null}
        </div>
      ) : null}
    </>
  );
}

export const ExecutionStudioLiveApprovalsPanel = memo(ExecutionStudioLiveApprovalsPanelInner);
