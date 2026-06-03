"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import type { OperatorPendingWsStrip } from "@/lib/cockpit-ws-delta";
import { hiveGet } from "@/lib/api";
import { isDocumentVisible } from "@/lib/document-visible";
import { subscribeHiveLivePulse } from "@/lib/hive-live-pulse-subscriber";
import {
  OPERATOR_PENDING_ALERT_EVENT,
  OPERATOR_PENDING_REFRESH_EVENT,
  type OperatorPendingAlertDetail,
  type OperatorPendingRefreshDetail,
  studioPendingActionHref,
  supervisorSessionHref,
} from "@/lib/operator-pending-events";
import type { PendingReviewStats } from "@/lib/hive-types";

export interface OperatorPendingApprovals {
  count: number;
  browser_pending: number;
  external_pending: number;
  codebase_pending: number;
  codebase_auto_approve_enabled?: boolean;
  live_actions: Array<{
    type: "browser" | "external";
    message?: string;
    connector_slug?: string;
    tool_name?: string | null;
    supervisor_session_id?: string | null;
  }>;
  pending_alert?: OperatorPendingAlertDetail;
}

export interface OperatorPendingSnapshot {
  tasksPending: number;
  reviewPending: number;
  studioPending: number;
  studio: OperatorPendingApprovals;
  total: number;
  refresh: () => void;
  wsConnected: boolean;
}

const EMPTY_STUDIO: OperatorPendingApprovals = {
  count: 0,
  browser_pending: 0,
  external_pending: 0,
  codebase_pending: 0,
  codebase_auto_approve_enabled: false,
  live_actions: [],
};

function effectiveStudioCount(studio: OperatorPendingApprovals): number {
  const browser = studio.browser_pending ?? 0;
  const external = studio.external_pending ?? 0;
  const codebase = studio.codebase_pending ?? 0;
  if (studio.codebase_auto_approve_enabled) {
    return browser + external;
  }
  return Math.max(0, studio.count ?? browser + external + codebase);
}

function applyOptimisticClear(
  studio: OperatorPendingApprovals,
  detail: OperatorPendingRefreshDetail | undefined,
): OperatorPendingApprovals {
  const cleared = detail?.clearedAction;
  if (!cleared) return studio;

  const live_actions = studio.live_actions.filter((row) => {
    if (cleared.type === "browser") return row.type !== "browser";
    return !(
      row.type === "external" &&
      row.connector_slug === cleared.connector_slug &&
      (row.tool_name ?? "search") === (cleared.tool_name ?? "search")
    );
  });
  const browser_pending = live_actions.filter((row) => row.type === "browser").length;
  const external_pending = live_actions.filter((row) => row.type === "external").length;
  const count = browser_pending + external_pending + Math.max(0, studio.codebase_pending ?? 0);
  return { ...studio, live_actions, browser_pending, external_pending, count };
}

function applyWsStrip(studio: OperatorPendingApprovals, strip: OperatorPendingWsStrip): OperatorPendingApprovals {
  return {
    ...studio,
    count: strip.count,
    browser_pending: strip.browser_pending,
    external_pending: strip.external_pending,
    codebase_pending: strip.codebase_pending,
    pending_alert: strip.pending_alert,
  };
}

function emitPendingAlertToast(alert: OperatorPendingAlertDetail): void {
  if (!isDocumentVisible()) {
    return;
  }

  const href = alert.supervisor_session_id
    ? supervisorSessionHref(alert.supervisor_session_id)
    : studioPendingActionHref({ type: alert.type });

  toast.warning(alert.message, {
    description: "Execution Studio approval required",
    action: {
      label: "Open",
      onClick: () => {
        window.location.assign(href);
      },
    },
    duration: 12_000,
  });
}

/** Poll + WS actionable operator pending counts for badge + notification center. */
export function useOperatorPendingSnapshot(tasksPending = 0): OperatorPendingSnapshot {
  const [reviewPending, setReviewPending] = useState(0);
  const [studio, setStudio] = useState<OperatorPendingApprovals>(EMPTY_STUDIO);
  const [wsConnected, setWsConnected] = useState(false);
  const lastWsRevisionRef = useRef(0);
  const lastAlertFingerprintRef = useRef("");
  const refreshRef = useRef<() => void>(() => undefined);

  const refresh = useCallback(() => {
    void (async () => {
      try {
        const [stats, studioPayload] = await Promise.all([
          hiveGet<PendingReviewStats>("learning/pending-review/stats"),
          hiveGet<OperatorPendingApprovals>("execution-studio/pending-approvals").catch(() => EMPTY_STUDIO),
        ]);
        setReviewPending(Math.max(0, stats.pending_count ?? 0));
        setStudio(studioPayload);
        const alert = studioPayload.pending_alert;
        if (alert?.fingerprint && alert.fingerprint !== lastAlertFingerprintRef.current) {
          const hadPrior = lastAlertFingerprintRef.current.length > 0;
          lastAlertFingerprintRef.current = alert.fingerprint;
          if (hadPrior) {
            emitPendingAlertToast(alert);
          }
        }
      } catch {
        /* keep last snapshot */
      }
    })();
  }, []);

  refreshRef.current = refresh;

  useEffect(() => {
    const timer = window.setTimeout(refresh, 600);
    const interval = window.setInterval(refresh, wsConnected ? 120_000 : 60_000);

    const onRefresh = (event: Event) => {
      const detail = (event as CustomEvent<OperatorPendingRefreshDetail>).detail;
      if (detail?.clearedAction) {
        setStudio((prev) => applyOptimisticClear(prev, detail));
      }
      refreshRef.current();
    };

    const onAlert = (event: Event) => {
      const detail = (event as CustomEvent<OperatorPendingAlertDetail>).detail;
      if (!detail?.fingerprint || detail.fingerprint === lastAlertFingerprintRef.current) {
        return;
      }
      lastAlertFingerprintRef.current = detail.fingerprint;
      emitPendingAlertToast(detail);
    };

    window.addEventListener(OPERATOR_PENDING_REFRESH_EVENT, onRefresh);
    window.addEventListener(OPERATOR_PENDING_ALERT_EVENT, onAlert);

    const unsubscribeWs = subscribeHiveLivePulse((pulse) => {
      setWsConnected(true);
      const strip = pulse.operator_pending_strip;
      if (!strip || strip.revision <= lastWsRevisionRef.current) {
        return;
      }
      lastWsRevisionRef.current = strip.revision;

      if (strip.pending_alert?.fingerprint && strip.pending_alert.fingerprint !== lastAlertFingerprintRef.current) {
        const hadPrior = lastAlertFingerprintRef.current.length > 0;
        lastAlertFingerprintRef.current = strip.pending_alert.fingerprint;
        if (hadPrior) {
          emitPendingAlertToast(strip.pending_alert);
          window.dispatchEvent(
            new CustomEvent<OperatorPendingAlertDetail>(OPERATOR_PENDING_ALERT_EVENT, {
              detail: strip.pending_alert,
            }),
          );
        }
      }

      setStudio((prev) => {
        const next = applyWsStrip(prev, strip);
        if (next.count !== prev.count) {
          window.setTimeout(() => refreshRef.current(), 0);
        }
        return next;
      });
      if (typeof strip.review_pending === "number") {
        setReviewPending(Math.max(0, strip.review_pending));
      }
    });

    return () => {
      window.clearTimeout(timer);
      window.clearInterval(interval);
      window.removeEventListener(OPERATOR_PENDING_REFRESH_EVENT, onRefresh);
      window.removeEventListener(OPERATOR_PENDING_ALERT_EVENT, onAlert);
      unsubscribeWs();
      setWsConnected(false);
    };
  }, [refresh, wsConnected]);

  const studioPending = effectiveStudioCount(studio);
  return {
    tasksPending,
    reviewPending,
    studioPending,
    studio,
    total: tasksPending + reviewPending + studioPending,
    refresh,
    wsConnected,
  };
}
