export type AuditFilter = "all" | "auth" | "keys" | "team" | "sharing";

export interface TenantAuditLogRow {
  id: string;
  action: string;
  target_type: string;
  target_ref: string;
  actor_user_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export const AUDIT_ACTION_LABELS: Record<string, string> = {
  password_changed: "Changed hive password",
  totp_provisioned: "Started 2FA enrollment",
  totp_confirmed: "Enabled 2FA for tenant",
  totp_disabled: "Disabled 2FA",
  totp_backup_codes_regenerated: "Regenerated 2FA backup codes",
  totp_admin_setup: "Admin configured 2FA policy",
  llm_secret_rotated: "Rotated LLM API key",
  llm_secret_cleared: "Cleared LLM vault override",
  api_key_created: "Minted script bearer key",
  api_key_revoked: "Revoked script bearer key",
  invite_created: "Sent team invite",
  member_role_updated: "Updated team member role",
  member_removed: "Removed team member",
  share_created: "Created public share link",
  share_revoked: "Revoked public share link",
  tenant_switched: "Switched active tenant",
};

export function actionCategory(action: string): Exclude<AuditFilter, "all"> {
  if (action.startsWith("totp_") || action === "password_changed" || action === "tenant_switched") {
    return "auth";
  }
  if (action.startsWith("llm_secret_") || action.startsWith("api_key_")) {
    return "keys";
  }
  if (action.startsWith("share_")) {
    return "sharing";
  }
  return "team";
}

export function formatAuditAction(row: TenantAuditLogRow): string {
  const base = AUDIT_ACTION_LABELS[row.action] ?? row.action.replaceAll("_", " ");
  const extra = row.payload?.provider;
  if (typeof extra === "string" && extra.length > 0) {
    return `${base} · ${extra}`;
  }
  if (row.target_type && row.target_ref && !AUDIT_ACTION_LABELS[row.action]) {
    return `${base} · ${row.target_type}:${row.target_ref.slice(0, 8)}`;
  }
  return base;
}

export function formatAuditTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "—";
  }
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

export function auditActorLabel(row: TenantAuditLogRow, memberMap: Map<string, string>): string {
  if (!row.actor_user_id) {
    return "system";
  }
  const mapped = memberMap.get(row.actor_user_id);
  if (mapped) {
    const local = mapped.split("@")[0] ?? mapped;
    return local.replace(/[._]/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
  }
  return row.actor_user_id.slice(0, 8);
}

export function ipFromAuditPayload(payload: Record<string, unknown>): string {
  const raw = payload.ip ?? payload.client_ip ?? payload.remote_ip;
  return typeof raw === "string" && raw.trim().length > 0 ? raw.trim() : "—";
}

export function filterAuditRows(rows: TenantAuditLogRow[], filter: AuditFilter): TenantAuditLogRow[] {
  if (filter === "all") {
    return rows;
  }
  return rows.filter((row) => actionCategory(row.action) === filter);
}
