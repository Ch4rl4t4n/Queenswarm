export type AuditDigestHealth = "healthy" | "stale" | "never_sent" | "disabled";

export interface AuditDigestHealthSummary {
  healthy?: number;
  stale?: number;
  never_sent?: number;
  disabled?: number;
}

/** Map digest health codes to operator-facing labels. */
export function auditDigestHealthLabel(health: AuditDigestHealth): string {
  switch (health) {
    case "healthy":
      return "On schedule";
    case "stale":
      return "Stale delivery";
    case "never_sent":
      return "Never sent";
    case "disabled":
      return "Digest off";
    default:
      return health;
  }
}

/** Badge tone for digest health in command center rollup table. */
export function auditDigestHealthTone(
  health: AuditDigestHealth,
): "ok" | "warn" | "err" | "info" {
  switch (health) {
    case "healthy":
      return "ok";
    case "stale":
      return "err";
    case "never_sent":
      return "warn";
    case "disabled":
      return "info";
    default:
      return "info";
  }
}

/** Whether command center should offer bulk send for stale/never_sent tenants. */
export function rollupDigestNeedsBulkSend(summary?: AuditDigestHealthSummary): boolean {
  return (summary?.stale ?? 0) > 0 || (summary?.never_sent ?? 0) > 0;
}

/** Whether command center should offer a per-tenant manual digest send action. */
export function tenantDigestNeedsManualSend(health: AuditDigestHealth): boolean {
  return health === "stale" || health === "never_sent";
}

export function formatDigestSentAt(iso: string | null | undefined): string | null {
  if (!iso) {
    return null;
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
