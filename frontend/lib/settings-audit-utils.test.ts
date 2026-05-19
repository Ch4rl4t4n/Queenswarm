import { describe, expect, it } from "vitest";

import {
  actionCategory,
  auditActorLabel,
  filterAuditRows,
  formatAuditAction,
  ipFromAuditPayload,
  type TenantAuditLogRow,
} from "@/lib/settings-audit-utils";
import { SETTINGS_NAV_SECTIONS } from "@/lib/settings-nav";

const sampleRow = (overrides: Partial<TenantAuditLogRow> = {}): TenantAuditLogRow => ({
  id: "00000000-0000-4000-8000-000000000001",
  action: "totp_confirmed",
  target_type: "tenant",
  target_ref: "tenant-1",
  actor_user_id: "00000000-0000-4000-8000-000000000099",
  payload: { ip: "203.0.113.10" },
  created_at: "2026-05-19T12:00:00.000Z",
  ...overrides,
});

describe("settings audit utils", () => {
  it("actionCategory maps auth and key actions", () => {
    expect(actionCategory("totp_confirmed")).toBe("auth");
    expect(actionCategory("api_key_created")).toBe("keys");
    expect(actionCategory("member_removed")).toBe("team");
    expect(actionCategory("share_created")).toBe("sharing");
  });

  it("formatAuditAction prefers known labels and provider suffix", () => {
    expect(formatAuditAction(sampleRow())).toBe("Enabled 2FA for tenant");
    expect(formatAuditAction(sampleRow({ action: "llm_secret_rotated", payload: { provider: "openai" } }))).toBe(
      "Rotated LLM API key · openai",
    );
  });

  it("auditActorLabel resolves member email to display name", () => {
    const map = new Map([["00000000-0000-4000-8000-000000000099", "admin@queenswarm.love"]]);
    expect(auditActorLabel(sampleRow(), map)).toBe("Admin");
  });

  it("ipFromAuditPayload reads ip aliases", () => {
    expect(ipFromAuditPayload({ client_ip: "198.51.100.7" })).toBe("198.51.100.7");
    expect(ipFromAuditPayload({})).toBe("—");
  });

  it("filterAuditRows applies category filter", () => {
    const rows = [sampleRow(), sampleRow({ id: "2", action: "api_key_created" })];
    expect(filterAuditRows(rows, "auth")).toHaveLength(1);
    expect(filterAuditRows(rows, "all")).toHaveLength(2);
  });
});

describe("settings nav", () => {
  it("includes security, api keys, and audit routes", () => {
    const hrefs = SETTINGS_NAV_SECTIONS.map((section) => section.href);
    expect(hrefs).toContain("/settings/security");
    expect(hrefs).toContain("/settings/api-keys");
    expect(hrefs).toContain("/settings/audit");
  });
});
