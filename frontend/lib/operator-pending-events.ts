/** Cross-panel operator pending refresh + Execution Studio deep-link helpers. */

export const OPERATOR_PENDING_REFRESH_EVENT = "queenswarm:operator-pending-refresh";

export const OPERATOR_PENDING_ALERT_EVENT = "queenswarm:operator-pending-alert";

export interface OperatorPendingAlertDetail {
  fingerprint: string;
  type: "browser" | "external";
  message: string;
  supervisor_session_id?: string;
}

export interface OperatorPendingRefreshDetail {
  clearedAction?: {
    type: "browser" | "external";
    connector_slug?: string;
    tool_name?: string | null;
  };
}

export interface StudioPendingActionRef {
  type: "browser" | "external";
  connector_slug?: string;
  tool_name?: string | null;
  supervisor_session_id?: string | null;
}

/** DOM id / URL hash for a pending live action row in Execution Studio. */
export function studioPendingActionHash(action: StudioPendingActionRef): string {
  if (action.type === "browser") return "pending-browser";
  const slug = (action.connector_slug ?? "external").replace(/[^a-z0-9_-]/gi, "-").toLowerCase();
  const tool = (action.tool_name ?? "search").replace(/[^a-z0-9_-]/gi, "-").toLowerCase();
  return `pending-external-${slug}-${tool}`;
}

export function studioPendingActionHref(action: StudioPendingActionRef): string {
  return `/integrations?tab=studio#${studioPendingActionHash(action)}`;
}

/** Deep link when badge counts codebase proposals (no live browser/connector step). */
export function studioCodebasePendingHref(): string {
  return "/integrations?tab=studio&section=lanes#codebase-pending";
}

/** Prefer live-action hash; fall back to codebase proposals lane. */
export function studioPendingApprovalsHref(studio: {
  count?: number;
  codebase_pending?: number;
  live_actions?: StudioPendingActionRef[];
}): string {
  const firstLive = studio.live_actions?.[0];
  if (firstLive) {
    if (firstLive.supervisor_session_id) {
      return supervisorSessionHref(firstLive.supervisor_session_id);
    }
    return studioPendingActionHref(firstLive);
  }
  if ((studio.codebase_pending ?? 0) > 0) {
    return studioCodebasePendingHref();
  }
  return "/integrations?tab=studio&section=lanes";
}

/** Notify sidebar badge + notification center to refetch pending snapshot immediately. */
export function dispatchOperatorPendingRefresh(detail?: OperatorPendingRefreshDetail): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<OperatorPendingRefreshDetail>(OPERATOR_PENDING_REFRESH_EVENT, { detail }));
}

/** Push toast-worthy pending alert when WS fingerprint changes. */
export function dispatchOperatorPendingAlert(detail: OperatorPendingAlertDetail): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<OperatorPendingAlertDetail>(OPERATOR_PENDING_ALERT_EVENT, { detail }));
}

export function supervisorSessionHref(sessionId: string): string {
  return `/ballroom?supervisor_session=${encodeURIComponent(sessionId)}`;
}
