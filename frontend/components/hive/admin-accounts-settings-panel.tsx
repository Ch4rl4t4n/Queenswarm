"use client";

import {
  ClipboardListIcon,
  CopyIcon,
  DownloadIcon,
  KeyRoundIcon,
  Loader2Icon,
  PlusIcon,
  SearchIcon,
  SendIcon,
  ShieldIcon,
  SparklesIcon,
  UserCogIcon,
  XIcon,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { HiveModalShell } from "@/components/hive/hive-modal-shell";
import { usePlatform } from "@/components/hive/platform-context";
import { AdminPublishOnboardingOverview } from "@/components/hive/admin-publish-onboarding-overview";
import { ResponsiveTable } from "@/components/ui/responsive-table";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveFetchRaw, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { profileKeyFor } from "@/lib/platform-features";

export interface AdminAccountMembership {
  tenant_id: string;
  tenant_slug: string;
  tenant_name: string;
  platform_mode: string;
  role: string;
  tier: string;
  subscription_status: string;
}

export interface AdminAccountRow {
  user_id: string;
  email: string;
  display_name: string | null;
  is_admin: boolean;
  is_active: boolean;
  totp_enabled: boolean;
  totp_required: boolean;
  active_tenant_id: string | null;
  created_at: string | null;
  memberships: AdminAccountMembership[];
}

interface AdminAccountListResponse {
  total: number;
  limit: number;
  offset: number;
  items: AdminAccountRow[];
}

interface AdminAccountAuditLog {
  id: string;
  tenant_id: string;
  action: string;
  target_type: string;
  target_ref: string;
  actor_user_id: string | null;
  payload: Record<string, unknown>;
  created_at: string | null;
}

interface CommercialDemoBootstrapResponse {
  email: string;
  user_id: string;
  tenant_id: string;
  tenant_slug: string;
  tenant_name: string;
  platform_mode: string;
  tier: string;
  password: string;
}

interface CommercialDemoStatus {
  ready: boolean;
  email: string;
  user_id?: string | null;
  tenant_id?: string | null;
  tenant_slug: string;
  tenant_name?: string | null;
  platform_mode?: string | null;
  tier?: string | null;
  profile_key?: string | null;
  is_active?: boolean | null;
  preview_access: boolean;
  last_bootstrapped_at?: string | null;
}

const TIERS = ["free", "pro", "enterprise"] as const;
const MODES = ["internal", "commercial"] as const;
const STATUSES = ["active", "past_due", "canceled", "trialing"] as const;

function tierTone(tier: string): "ok" | "warn" | "info" {
  if (tier === "enterprise") return "ok";
  if (tier === "pro") return "warn";
  return "info";
}

function modeTone(mode: string): "ok" | "warn" | "info" {
  return mode === "internal" ? "warn" : "info";
}

function accountProfileRecord(
  row: AdminAccountRow,
  membership: AdminAccountMembership | null,
): Record<string, unknown> {
  return {
    profile_key: membership ? profileKeyFor(membership.platform_mode, membership.tier) : null,
    email: row.email,
    user_id: row.user_id,
    display_name: row.display_name,
    is_admin: row.is_admin,
    is_active: row.is_active,
    tenant_id: membership?.tenant_id ?? null,
    tenant_slug: membership?.tenant_slug ?? null,
    tenant_name: membership?.tenant_name ?? null,
    platform_mode: membership?.platform_mode ?? null,
    tier: membership?.tier ?? null,
    role: membership?.role ?? null,
    subscription_status: membership?.subscription_status ?? null,
  };
}

function profilePayload(row: AdminAccountRow, membership: AdminAccountMembership | null): string {
  return JSON.stringify(accountProfileRecord(row, membership), null, 2);
}

async function downloadBlob(blob: Blob, filename: string): Promise<void> {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function copyText(value: string): Promise<void> {
  await navigator.clipboard.writeText(value);
}

export function AdminAccountsSettingsPanel() {
  const { isAdmin, platformMode } = usePlatform();
  const allowed = isAdmin && platformMode === "internal";

  const [items, setItems] = useState<AdminAccountRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createEmail, setCreateEmail] = useState("");
  const [createPassword, setCreatePassword] = useState("");
  const [createName, setCreateName] = useState("");
  const [createAdmin, setCreateAdmin] = useState(false);
  const [createMode, setCreateMode] = useState<(typeof MODES)[number]>("commercial");
  const [createTier, setCreateTier] = useState<(typeof TIERS)[number]>("free");

  const [resetUserId, setResetUserId] = useState<string | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetDisableTotp, setResetDisableTotp] = useState(true);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [bulkMode, setBulkMode] = useState<(typeof MODES)[number] | "">("");
  const [bulkTier, setBulkTier] = useState<(typeof TIERS)[number] | "">("");
  const [bulkActive, setBulkActive] = useState<"" | "true" | "false">("");

  const [auditUserId, setAuditUserId] = useState<string | null>(null);
  const [auditEmail, setAuditEmail] = useState<string>("");
  const [auditLogs, setAuditLogs] = useState<AdminAccountAuditLog[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const [demoResult, setDemoResult] = useState<CommercialDemoBootstrapResponse | null>(null);
  const [demoStatus, setDemoStatus] = useState<CommercialDemoStatus | null>(null);
  const [demoStatusLoading, setDemoStatusLoading] = useState(true);

  const loadDemoStatus = useCallback(async () => {
    if (!allowed) {
      setDemoStatusLoading(false);
      return;
    }
    setDemoStatusLoading(true);
    try {
      const status = await hiveGet<CommercialDemoStatus>("operator/accounts/commercial-demo/status");
      setDemoStatus(status);
    } catch {
      setDemoStatus(null);
    } finally {
      setDemoStatusLoading(false);
    }
  }, [allowed]);

  const load = useCallback(async () => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "100", offset: "0" });
      if (search.trim()) {
        params.set("q", search.trim());
      }
      const body = await hiveGet<AdminAccountListResponse>(`operator/accounts?${params.toString()}`);
      setItems(body.items);
      setTotal(body.total);
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Accounts load failed.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [allowed, search]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadDemoStatus();
  }, [loadDemoStatus]);

  const primaryMembership = useCallback((row: AdminAccountRow): AdminAccountMembership | null => {
    if (!row.memberships.length) {
      return null;
    }
    return row.memberships.find((m) => m.tenant_id === row.active_tenant_id) ?? row.memberships[0] ?? null;
  }, []);

  const patchUser = useCallback(
    async (userId: string, patch: Record<string, unknown>) => {
      setBusyId(userId);
      try {
        const updated = await hivePatchJson<AdminAccountRow>(`operator/accounts/${userId}`, patch);
        setItems((prev) => prev.map((row) => (row.user_id === userId ? updated : row)));
        toast.success("Účet aktualizovaný");
      } catch (error) {
        const msg = error instanceof HiveApiError ? error.message : "Update failed.";
        toast.error(msg);
        await load();
      } finally {
        setBusyId(null);
      }
    },
    [load],
  );

  const patchTenant = useCallback(
    async (tenantId: string, patch: Record<string, unknown>, userId: string) => {
      setBusyId(userId);
      try {
        await hivePatchJson(`operator/accounts/tenants/${tenantId}`, patch);
        await load();
        toast.success("Tenant / tier uložený");
      } catch (error) {
        const msg = error instanceof HiveApiError ? error.message : "Tenant update failed.";
        toast.error(msg);
      } finally {
        setBusyId(null);
      }
    },
    [load],
  );

  const createAccount = useCallback(async () => {
    setBusyId("create");
    try {
      await hivePostJson<AdminAccountRow>("operator/accounts", {
        email: createEmail.trim(),
        password: createPassword,
        display_name: createName.trim() || null,
        is_admin: createAdmin,
        enable_totp: false,
        platform_mode: createMode,
        tier: createTier,
      });
      toast.success("Účet vytvorený");
      setCreateOpen(false);
      setCreateEmail("");
      setCreatePassword("");
      setCreateName("");
      setCreateAdmin(false);
      await load();
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Create failed.";
      toast.error(msg);
    } finally {
      setBusyId(null);
    }
  }, [createAdmin, createEmail, createMode, createName, createPassword, createTier, load]);

  const submitPasswordReset = useCallback(async () => {
    if (!resetUserId) {
      return;
    }
    setBusyId(resetUserId);
    try {
      await hivePostJson(`operator/accounts/${resetUserId}/reset-password`, {
        password: resetPassword,
        disable_totp: resetDisableTotp,
      });
      toast.success("Heslo resetované");
      setResetUserId(null);
      setResetPassword("");
      await load();
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Password reset failed.";
      toast.error(msg);
    } finally {
      setBusyId(null);
    }
  }, [load, resetDisableTotp, resetPassword, resetUserId]);

  const toggleSelected = useCallback((userId: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(userId);
      } else {
        next.delete(userId);
      }
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(
    (checked: boolean) => {
      setSelectedIds(checked ? new Set(items.map((row) => row.user_id)) : new Set());
    },
    [items],
  );

  const runBulkPatch = useCallback(async () => {
    if (selectedIds.size === 0) {
      return;
    }
    const patch: Record<string, unknown> = {
      user_ids: Array.from(selectedIds),
    };
    if (bulkActive === "true") {
      patch.is_active = true;
    } else if (bulkActive === "false") {
      patch.is_active = false;
    }
    if (bulkMode) {
      patch.platform_mode = bulkMode;
    }
    if (bulkTier) {
      patch.tier = bulkTier;
    }
    if (patch.is_active === undefined && !patch.platform_mode && !patch.tier) {
      toast.error("Vyber aspoň jednu bulk akciu.");
      return;
    }

    setBusyId("bulk");
    try {
      const result = await hivePostJson<{ updated_users: number; updated_tenants: number }>(
        "operator/accounts/bulk",
        patch,
      );
      toast.success(`Bulk hotový · users ${result.updated_users} · tenants ${result.updated_tenants}`);
      setSelectedIds(new Set());
      setBulkActive("");
      setBulkMode("");
      setBulkTier("");
      await load();
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Bulk update failed.";
      toast.error(msg);
    } finally {
      setBusyId(null);
    }
  }, [bulkActive, bulkMode, bulkTier, load, selectedIds]);

  const openAuditDrawer = useCallback(async (row: AdminAccountRow) => {
    setAuditUserId(row.user_id);
    setAuditEmail(row.email);
    setAuditLoading(true);
    setAuditLogs([]);
    try {
      const logs = await hiveGet<AdminAccountAuditLog[]>(`operator/accounts/${row.user_id}/audit-logs?limit=80`);
      setAuditLogs(logs);
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Audit load failed.";
      toast.error(msg);
      setAuditUserId(null);
    } finally {
      setAuditLoading(false);
    }
  }, []);

  const exportAuditLogs = useCallback(
    async (format: "json" | "csv") => {
      if (!auditUserId) {
        return;
      }
      setAuditLoading(true);
      try {
        const response = await hiveFetchRaw(
          `operator/accounts/${auditUserId}/audit-logs/export?format=${format}&limit=500`,
        );
        if (!response.ok) {
          throw new HiveApiError("Audit export failed.", response.status, null);
        }
        const blob = await response.blob();
        const safeEmail = auditEmail.replace(/[^a-zA-Z0-9._-]+/g, "-");
        await downloadBlob(blob, `audit-${safeEmail}.${format}`);
        toast.success(`Audit export · ${format.toUpperCase()}`);
      } catch (error) {
        const msg = error instanceof HiveApiError ? error.message : "Audit export failed.";
        toast.error(msg);
      } finally {
        setAuditLoading(false);
      }
    },
    [auditEmail, auditUserId],
  );

  const copySelectedProfiles = useCallback(async () => {
    if (selectedIds.size === 0) {
      return;
    }
    const profiles = items
      .filter((row) => selectedIds.has(row.user_id))
      .map((row) => accountProfileRecord(row, primaryMembership(row)));
    try {
      await copyText(JSON.stringify(profiles, null, 2));
      toast.success(`Skopírovaných ${profiles.length} profilov`);
    } catch {
      toast.error("Copy failed — skontroluj clipboard permissions.");
    }
  }, [items, primaryMembership, selectedIds]);

  const bootstrapCommercialDemo = useCallback(async () => {
    setBusyId("demo");
    try {
      const result = await hivePostJson<CommercialDemoBootstrapResponse>("operator/accounts/bootstrap-commercial-demo", {
        tier: "pro",
      });
      setDemoResult(result);
      toast.success("Commercial demo workspace pripravený");
      await load();
      await loadDemoStatus();
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Commercial demo bootstrap failed.";
      toast.error(msg);
    } finally {
      setBusyId(null);
    }
  }, [load, loadDemoStatus]);

  const grantDemoPreviewAccess = useCallback(async () => {
    setBusyId("demo-preview");
    try {
      await hivePostJson("operator/accounts/commercial-demo/grant-preview-access", {});
      toast.success("Preview prístup udelený — prepni tenant v sidebar-e");
      await loadDemoStatus();
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Preview grant failed.";
      toast.error(msg);
    } finally {
      setBusyId(null);
    }
  }, [loadDemoStatus]);

  const summary = useMemo(
    () => ({
      active: items.filter((i) => i.is_active).length,
      admins: items.filter((i) => i.is_admin).length,
      commercial: items.filter((i) => primaryMembership(i)?.platform_mode === "commercial").length,
    }),
    [items, primaryMembership],
  );

  if (!allowed) {
    return (
      <V4Card>
        <V4CardHeader title="Accounts CMS" description="Dostupné len pre admin v internal tenante." />
      </V4Card>
    );
  }

  return (
    <div className="space-y-4">
      <AdminPublishOnboardingOverview />
      <V4Card className="p-4 md:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <V4CardHeader
            as="h2"
            kicker="Commercial preview"
            title="Demo workspace"
            description="Zákaznícky surface pre QA — bootstrap, potom prepni tenant v sidebar-e."
          />
          <div className="flex flex-wrap items-center gap-2">
            {demoStatus?.ready && !demoStatus.preview_access ? (
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                disabled={busyId === "demo-preview"}
                onClick={() => void grantDemoPreviewAccess()}
              >
                Grant preview access
              </button>
            ) : null}
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm gap-2"
              disabled={busyId === "demo"}
              onClick={() => void bootstrapCommercialDemo()}
            >
              {busyId === "demo" ? (
                <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <SparklesIcon className="h-4 w-4" aria-hidden />
              )}
              {demoStatus?.ready ? "Refresh demo" : "Bootstrap demo"}
            </button>
          </div>
        </div>

        {demoStatusLoading ? (
          <div className="mt-4 flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin text-pollen" aria-hidden />
            Loading demo status…
          </div>
        ) : demoStatus?.ready ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-(--qs-border) bg-black/30 p-3">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Account</p>
              <p className="mt-1 text-sm text-(--qs-text)">{demoStatus.email}</p>
            </div>
            <div className="rounded-lg border border-(--qs-border) bg-black/30 p-3">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Profile</p>
              <p className="mt-1 font-mono text-sm text-cyan">{demoStatus.profile_key ?? "—"}</p>
              <p className="text-[10px] text-(--qs-text-3)">
                {demoStatus.platform_mode}/{demoStatus.tier}
              </p>
            </div>
            <div className="rounded-lg border border-(--qs-border) bg-black/30 p-3">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Tenant</p>
              <p className="mt-1 text-sm text-(--qs-text)">{demoStatus.tenant_slug}</p>
              <V4Badge tone={demoStatus.preview_access ? "ok" : "warn"}>
                {demoStatus.preview_access ? "sidebar preview OK" : "no preview access"}
              </V4Badge>
            </div>
            <div className="rounded-lg border border-(--qs-border) bg-black/30 p-3">
              <p className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">Last bootstrap</p>
              <p className="mt-1 text-sm text-(--qs-text-2)">
                {demoStatus.last_bootstrapped_at
                  ? new Date(demoStatus.last_bootstrapped_at).toLocaleString()
                  : "—"}
              </p>
            </div>
          </div>
        ) : (
          <p className="mt-4 text-sm text-(--qs-text-3)">
            Demo ešte neexistuje. Bootstrap vytvorí <span className="font-mono text-cyan">{demoStatus?.email ?? "demo@queenswarm.love"}</span>{" "}
            v tenante <span className="font-mono text-cyan">commercial-demo</span> (pro tier).
          </p>
        )}
      </V4Card>

      <V4Card className="overflow-hidden p-0">
        <div className="border-b border-(--qs-border) px-4 py-4 md:px-6">
          <V4CardHeader
            as="h2"
            kicker="Admin · CMS"
            title="Account management"
            description="Účty, tier, platform mode, reset hesla — štandardné CMS operácie."
            actions={<HiveRefreshButton busy={loading} onClick={() => void load()} />}
          />
        </div>

        <div className="border-b border-(--qs-border) px-4 py-3 md:px-6">
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm flex w-full items-center justify-center gap-2"
            onClick={() => setCreateOpen(true)}
          >
            <PlusIcon className="h-4 w-4" aria-hidden />
            New account
          </button>
        </div>

        <div className="border-b border-(--qs-border)/70 px-4 py-3 md:px-6">
          <div className="flex items-center gap-2">
            <div className="relative min-w-0 flex-1">
              <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-(--qs-text-3)" aria-hidden />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    setSearch(query);
                  }
                }}
                placeholder="Hľadať email alebo meno…"
                className="w-full rounded-lg border border-(--qs-border) bg-black/40 py-2 pl-9 pr-3 text-sm text-(--qs-text)"
              />
            </div>
            <button
              type="button"
              aria-label="Search"
              className="v4-ballroom-send-btn qs-btn qs-btn--primary flex h-11 w-11 shrink-0 items-center justify-center p-0"
              onClick={() => setSearch(query)}
            >
              <SendIcon className="v4-ballroom-send-icon" strokeWidth={2.25} aria-hidden />
            </button>
          </div>
          <p className="v4-admin-toolbar-summary mt-3 text-xs text-(--qs-text-3)">
            {total} účtov · {summary.active} active · {summary.admins} admin · {summary.commercial} commercial
          </p>
        </div>

        {selectedIds.size > 0 ? (
          <div className="flex flex-wrap items-center gap-2 border-b border-pollen/20 bg-pollen/5 px-4 py-3 md:px-6">
            <span className="text-xs font-medium text-pollen">{selectedIds.size} selected</span>
            <select
              value={bulkActive}
              onChange={(e) => setBulkActive(e.target.value as "" | "true" | "false")}
              className="rounded border border-(--qs-border) bg-black/40 px-2 py-1 text-xs"
            >
              <option value="">Active — no change</option>
              <option value="true">Set active</option>
              <option value="false">Set disabled</option>
            </select>
            <select
              value={bulkMode}
              onChange={(e) => setBulkMode(e.target.value as (typeof MODES)[number] | "")}
              className="rounded border border-(--qs-border) bg-black/40 px-2 py-1 text-xs capitalize"
            >
              <option value="">Mode — no change</option>
              {MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {mode}
                </option>
              ))}
            </select>
            <select
              value={bulkTier}
              onChange={(e) => setBulkTier(e.target.value as (typeof TIERS)[number] | "")}
              className="rounded border border-(--qs-border) bg-black/40 px-2 py-1 text-xs capitalize"
            >
              <option value="">Tier — no change</option>
              {TIERS.map((tier) => (
                <option key={tier} value={tier}>
                  {tier}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--xs"
              disabled={busyId === "bulk"}
              onClick={() => void runBulkPatch()}
            >
              Apply bulk
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--xs gap-1"
              onClick={() => void copySelectedProfiles()}
            >
              <CopyIcon className="h-3 w-3" aria-hidden />
              Copy profiles
            </button>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--xs" onClick={() => setSelectedIds(new Set())}>
              Clear
            </button>
          </div>
        ) : null}

        <ResponsiveTable
          className="px-4 pb-4 md:px-0 md:pb-0"
          table={
            <table className="w-full min-w-[1080px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-(--qs-border) bg-black/25 text-xs uppercase tracking-wide text-(--qs-text-3)">
                <th className="px-3 py-3 md:pl-6">
                  <input
                    type="checkbox"
                    aria-label="Select all accounts"
                    checked={items.length > 0 && selectedIds.size === items.length}
                    onChange={(e) => toggleSelectAll(e.target.checked)}
                  />
                </th>
                <th className="px-3 py-3">Účet</th>
                <th className="px-3 py-3">Profile</th>
                <th className="px-3 py-3">Stav</th>
                <th className="px-3 py-3">Tenant / mode</th>
                <th className="px-3 py-3">Tier</th>
                <th className="px-3 py-3">Admin</th>
                <th className="px-3 py-3">Active</th>
                <th className="px-4 py-3 md:px-6">Akcie</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-6 py-10 text-center text-(--qs-text-3)">
                    <Loader2Icon className="mx-auto h-5 w-5 animate-spin text-pollen" aria-hidden />
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-8 text-center text-(--qs-text-3)">
                    Žiadne účty
                  </td>
                </tr>
              ) : (
                items.map((row) => {
                  const membership = primaryMembership(row);
                  const busy = busyId === row.user_id;
                  const selected = selectedIds.has(row.user_id);
                  return (
                    <tr key={row.user_id} className="border-b border-(--qs-border)/60 hover:bg-white/[0.02]">
                      <td className="px-3 py-3 md:pl-6">
                        <input
                          type="checkbox"
                          aria-label={`Select ${row.email}`}
                          checked={selected}
                          onChange={(e) => toggleSelected(row.user_id, e.target.checked)}
                        />
                      </td>
                      <td className="px-3 py-3">
                        <div className="font-medium text-(--qs-text)">{row.email}</div>
                        <input
                          type="text"
                          defaultValue={row.display_name ?? ""}
                          placeholder="Display name"
                          disabled={busy}
                          className="mt-1 w-full max-w-[220px] rounded border border-(--qs-border) bg-black/30 px-2 py-1 text-xs"
                          onBlur={(e) => {
                            const next = e.target.value.trim();
                            if (next !== (row.display_name ?? "")) {
                              void patchUser(row.user_id, { display_name: next || null });
                            }
                          }}
                        />
                        <p className="mt-1 font-mono text-[10px] text-(--qs-text-3)">{row.user_id}</p>
                      </td>
                      <td className="px-3 py-3">
                        {membership ? (
                          <div className="space-y-1">
                            <p className="font-mono text-[10px] text-cyan">
                              {profileKeyFor(membership.platform_mode, membership.tier)}
                            </p>
                            <p className="font-mono text-[10px] text-(--qs-text-3)">
                              {membership.platform_mode}/{membership.tier}
                            </p>
                            <p className="text-[10px] text-(--qs-text-3)">{membership.tenant_slug}</p>
                            <button
                              type="button"
                              className="qs-btn qs-btn--ghost qs-btn--xs gap-1"
                              onClick={() => {
                                void copyText(profilePayload(row, membership)).then(() =>
                                  toast.success("Profile skopírovaný"),
                                );
                              }}
                            >
                              <CopyIcon className="h-3 w-3" aria-hidden />
                              Copy profile
                            </button>
                          </div>
                        ) : (
                          <span className="text-(--qs-text-3)">—</span>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex flex-col gap-1">
                          <V4Badge tone={row.is_active ? "ok" : "err"}>{row.is_active ? "active" : "disabled"}</V4Badge>
                          {row.totp_enabled ? (
                            <V4Badge tone="warn">2FA on</V4Badge>
                          ) : (
                            <V4Badge tone="info">no 2FA</V4Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        {membership ? (
                          <div className="space-y-1">
                            <p className="text-xs text-(--qs-text-2)">{membership.tenant_name}</p>
                            <select
                              value={membership.platform_mode}
                              disabled={busy}
                              className="rounded border border-(--qs-border) bg-black/40 px-2 py-1 text-xs capitalize"
                              onChange={(e) =>
                                void patchTenant(
                                  membership.tenant_id,
                                  { platform_mode: e.target.value },
                                  row.user_id,
                                )
                              }
                            >
                              {MODES.map((mode) => (
                                <option key={mode} value={mode}>
                                  {mode}
                                </option>
                              ))}
                            </select>
                            <V4Badge tone={modeTone(membership.platform_mode)}>{membership.platform_mode}</V4Badge>
                          </div>
                        ) : (
                          <span className="text-(--qs-text-3)">—</span>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        {membership ? (
                          <div className="space-y-1">
                            <select
                              value={membership.tier}
                              disabled={busy}
                              className="rounded border border-(--qs-border) bg-black/40 px-2 py-1 text-xs capitalize"
                              onChange={(e) =>
                                void patchTenant(membership.tenant_id, { tier: e.target.value }, row.user_id)
                              }
                            >
                              {TIERS.map((tier) => (
                                <option key={tier} value={tier}>
                                  {tier}
                                </option>
                              ))}
                            </select>
                            <select
                              value={membership.subscription_status}
                              disabled={busy}
                              className="rounded border border-(--qs-border) bg-black/40 px-2 py-1 text-xs"
                              onChange={(e) =>
                                void patchTenant(
                                  membership.tenant_id,
                                  { subscription_status: e.target.value },
                                  row.user_id,
                                )
                              }
                            >
                              {STATUSES.map((status) => (
                                <option key={status} value={status}>
                                  {status}
                                </option>
                              ))}
                            </select>
                            <V4Badge tone={tierTone(membership.tier)}>{membership.tier}</V4Badge>
                          </div>
                        ) : (
                          <span className="text-(--qs-text-3)">—</span>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <HiveSwitch
                          checked={row.is_admin}
                          disabled={busy}
                          aria-label={`Admin ${row.email}`}
                          onCheckedChange={(next) => void patchUser(row.user_id, { is_admin: next })}
                        />
                      </td>
                      <td className="px-3 py-3">
                        <HiveSwitch
                          checked={row.is_active}
                          disabled={busy}
                          aria-label={`Active ${row.email}`}
                          onCheckedChange={(next) => void patchUser(row.user_id, { is_active: next })}
                        />
                      </td>
                      <td className="px-4 py-3 md:px-6">
                        <div className="flex flex-wrap gap-1">
                          <button
                            type="button"
                            className="qs-btn qs-btn--ghost qs-btn--xs gap-1"
                            disabled={busy}
                            onClick={() => {
                              setResetUserId(row.user_id);
                              setResetPassword("");
                            }}
                          >
                            <KeyRoundIcon className="h-3.5 w-3.5" aria-hidden />
                            Reset pwd
                          </button>
                          <button
                            type="button"
                            className="qs-btn qs-btn--ghost qs-btn--xs gap-1"
                            disabled={busy}
                            onClick={() => void openAuditDrawer(row)}
                          >
                            <ClipboardListIcon className="h-3.5 w-3.5" aria-hidden />
                            Audit
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
          }
          cards={
            loading ? (
              <div className="flex min-h-[120px] items-center justify-center px-4">
                <Loader2Icon className="h-5 w-5 animate-spin text-pollen" aria-hidden />
              </div>
            ) : items.length === 0 ? (
              <p className="px-4 py-8 text-center text-(--qs-text-3)">Žiadne účty</p>
            ) : (
              items.map((row) => {
                const membership = primaryMembership(row);
                const busy = busyId === row.user_id;
                const selected = selectedIds.has(row.user_id);
                return (
                  <article key={row.user_id} className="v4-admin-account-card">
                    <div className="v4-admin-account-card__head">
                      <input
                        type="checkbox"
                        aria-label={`Select ${row.email}`}
                        checked={selected}
                        onChange={(e) => toggleSelected(row.user_id, e.target.checked)}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-(--qs-text)">{row.email}</p>
                        <p className="truncate font-mono text-[10px] text-(--qs-text-3)">{row.user_id}</p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-1">
                        <V4Badge tone={row.is_active ? "ok" : "err"}>{row.is_active ? "active" : "disabled"}</V4Badge>
                        <V4Badge tone={row.totp_enabled ? "warn" : "info"}>{row.totp_enabled ? "2FA on" : "no 2FA"}</V4Badge>
                      </div>
                    </div>

                    <label className="block text-[10px] uppercase tracking-wide text-(--qs-text-3)">
                      Display name
                      <input
                        type="text"
                        defaultValue={row.display_name ?? ""}
                        placeholder="Display name"
                        disabled={busy}
                        className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/30 px-3 py-2 text-sm"
                        onBlur={(e) => {
                          const next = e.target.value.trim();
                          if (next !== (row.display_name ?? "")) {
                            void patchUser(row.user_id, { display_name: next || null });
                          }
                        }}
                      />
                    </label>

                    {membership ? (
                      <>
                        <div className="rounded-lg border border-(--qs-border)/70 bg-black/20 p-3 text-xs">
                          <p className="font-mono text-cyan">
                            {profileKeyFor(membership.platform_mode, membership.tier)}
                          </p>
                          <p className="mt-1 text-(--qs-text-3)">{membership.tenant_name}</p>
                          <p className="font-mono text-[10px] text-(--qs-text-3)">{membership.tenant_slug}</p>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <label className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">
                            Mode
                            <select
                              value={membership.platform_mode}
                              disabled={busy}
                              className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-2 py-2 text-xs capitalize"
                              onChange={(e) =>
                                void patchTenant(membership.tenant_id, { platform_mode: e.target.value }, row.user_id)
                              }
                            >
                              {MODES.map((mode) => (
                                <option key={mode} value={mode}>
                                  {mode}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">
                            Tier
                            <select
                              value={membership.tier}
                              disabled={busy}
                              className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-2 py-2 text-xs capitalize"
                              onChange={(e) =>
                                void patchTenant(membership.tenant_id, { tier: e.target.value }, row.user_id)
                              }
                            >
                              {TIERS.map((tier) => (
                                <option key={tier} value={tier}>
                                  {tier}
                                </option>
                              ))}
                            </select>
                          </label>
                        </div>
                        <label className="text-[10px] uppercase tracking-wide text-(--qs-text-3)">
                          Subscription
                          <select
                            value={membership.subscription_status}
                            disabled={busy}
                            className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-2 py-2 text-xs"
                            onChange={(e) =>
                              void patchTenant(
                                membership.tenant_id,
                                { subscription_status: e.target.value },
                                row.user_id,
                              )
                            }
                          >
                            {STATUSES.map((status) => (
                              <option key={status} value={status}>
                                {status}
                              </option>
                            ))}
                          </select>
                        </label>
                      </>
                    ) : null}

                    <div className="grid grid-cols-2 gap-3">
                      <label className="v4-admin-switch-row">
                        <span className="text-xs font-medium text-(--qs-text)">Admin</span>
                        <HiveSwitch
                          checked={row.is_admin}
                          disabled={busy}
                          aria-label={`Admin ${row.email}`}
                          onCheckedChange={(next) => void patchUser(row.user_id, { is_admin: next })}
                        />
                      </label>
                      <label className="v4-admin-switch-row">
                        <span className="text-xs font-medium text-(--qs-text)">Active</span>
                        <HiveSwitch
                          checked={row.is_active}
                          disabled={busy}
                          aria-label={`Active ${row.email}`}
                          onCheckedChange={(next) => void patchUser(row.user_id, { is_active: next })}
                        />
                      </label>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      {membership ? (
                        <button
                          type="button"
                          className="qs-btn qs-btn--ghost qs-btn--sm col-span-2 gap-1"
                          onClick={() => {
                            void copyText(profilePayload(row, membership)).then(() =>
                              toast.success("Profile skopírovaný"),
                            );
                          }}
                        >
                          <CopyIcon className="h-3.5 w-3.5" aria-hidden />
                          Copy profile
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                        disabled={busy}
                        onClick={() => {
                          setResetUserId(row.user_id);
                          setResetPassword("");
                        }}
                      >
                        <KeyRoundIcon className="h-3.5 w-3.5" aria-hidden />
                        Reset pwd
                      </button>
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                        disabled={busy}
                        onClick={() => void openAuditDrawer(row)}
                      >
                        <ClipboardListIcon className="h-3.5 w-3.5" aria-hidden />
                        Audit
                      </button>
                    </div>
                  </article>
                );
              })
            )
          }
        />
      </V4Card>

      {createOpen ? (
        <HiveModalShell
          open
          onClose={() => setCreateOpen(false)}
          ariaLabel="New account"
          zIndexClass="z-[70]"
          backdropClassName="bg-black/70"
          panelClassName="w-full max-w-md"
        >
          <V4Card className="space-y-4 p-5">
            <V4CardHeader as="h3" title="New account" description="Vytvorí user + personal tenant." />
            <label className="block text-xs text-(--qs-text-3)">
              Email
              <input
                type="email"
                value={createEmail}
                onChange={(e) => setCreateEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs text-(--qs-text-3)">
              Password (min 8)
              <input
                type="password"
                value={createPassword}
                onChange={(e) => setCreatePassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs text-(--qs-text-3)">
              Display name
              <input
                type="text"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-3 py-2 text-sm"
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-xs text-(--qs-text-3)">
                Platform mode
                <select
                  value={createMode}
                  onChange={(e) => setCreateMode(e.target.value as (typeof MODES)[number])}
                  className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-3 py-2 text-sm capitalize"
                >
                  {MODES.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-(--qs-text-3)">
                Tier
                <select
                  value={createTier}
                  onChange={(e) => setCreateTier(e.target.value as (typeof TIERS)[number])}
                  className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-3 py-2 text-sm capitalize"
                >
                  {TIERS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="flex items-center gap-2 text-sm text-(--qs-text-2)">
              <HiveSwitch checked={createAdmin} onCheckedChange={setCreateAdmin} aria-label="Grant admin" />
              <ShieldIcon className="h-4 w-4 text-pollen" aria-hidden />
              Admin privileges
            </label>
            <div className="flex justify-end gap-2">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setCreateOpen(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm gap-2"
                disabled={busyId === "create" || createEmail.length < 3 || createPassword.length < 8}
                onClick={() => void createAccount()}
              >
                {busyId === "create" ? <Loader2Icon className="h-4 w-4 animate-spin" /> : <UserCogIcon className="h-4 w-4" />}
                Create
              </button>
            </div>
          </V4Card>
        </HiveModalShell>
      ) : null}

      {resetUserId ? (
        <HiveModalShell
          open
          onClose={() => setResetUserId(null)}
          ariaLabel="Reset password"
          zIndexClass="z-[70]"
          backdropClassName="bg-black/70"
          panelClassName="w-full max-w-md"
        >
          <V4Card className="space-y-4 p-5">
            <V4CardHeader as="h3" title="Reset password" description="Nové heslo pre vybraný účet." />
            <label className="block text-xs text-(--qs-text-3)">
              New password
              <input
                type="password"
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-(--qs-border) bg-black/40 px-3 py-2 text-sm"
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-(--qs-text-2)">
              <HiveSwitch checked={resetDisableTotp} onCheckedChange={setResetDisableTotp} aria-label="Disable TOTP" />
              Disable 2FA requirement
            </label>
            <div className="flex justify-end gap-2">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setResetUserId(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm"
                disabled={!resetPassword || resetPassword.length < 8 || busyId === resetUserId}
                onClick={() => void submitPasswordReset()}
              >
                Reset password
              </button>
            </div>
          </V4Card>
        </HiveModalShell>
      ) : null}

      {auditUserId ? (
        <HiveModalShell
          open
          onClose={() => setAuditUserId(null)}
          ariaLabel="Audit trail"
          align="drawer-right"
          zIndexClass="z-[75]"
          backdropClassName="bg-black/60"
          panelClassName="flex h-full w-full max-w-md flex-col border-l border-(--qs-border) bg-[#050510] shadow-2xl"
        >
          <div className="flex h-full flex-col">
            <div className="flex items-start justify-between gap-3 border-b border-(--qs-border) px-4 py-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-cyan">Audit trail</p>
                <p className="text-sm font-medium text-(--qs-text)">{auditEmail}</p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--xs gap-1"
                  disabled={auditLoading}
                  onClick={() => void exportAuditLogs("json")}
                >
                  <DownloadIcon className="h-3.5 w-3.5" aria-hidden />
                  JSON
                </button>
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--xs gap-1"
                  disabled={auditLoading}
                  onClick={() => void exportAuditLogs("csv")}
                >
                  <DownloadIcon className="h-3.5 w-3.5" aria-hidden />
                  CSV
                </button>
                <button type="button" className="qs-btn qs-btn--ghost qs-btn--xs" onClick={() => setAuditUserId(null)}>
                  <XIcon className="h-4 w-4" aria-hidden />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto hive-scrollbar p-4">
              {auditLoading ? (
                <div className="flex justify-center py-10">
                  <Loader2Icon className="h-5 w-5 animate-spin text-pollen" aria-hidden />
                </div>
              ) : auditLogs.length === 0 ? (
                <p className="text-sm text-(--qs-text-3)">Žiadne audit záznamy pre tento účet.</p>
              ) : (
                <div className="space-y-3">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="rounded-lg border border-(--qs-border) bg-black/35 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-mono text-xs text-pollen">{log.action}</p>
                        <p className="text-[10px] text-(--qs-text-3)">
                          {log.created_at ? new Date(log.created_at).toLocaleString() : "—"}
                        </p>
                      </div>
                      <p className="mt-1 text-[11px] text-(--qs-text-3)">
                        {log.target_type}:{log.target_ref}
                      </p>
                      {Object.keys(log.payload).length > 0 ? (
                        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded bg-black/40 p-2 font-mono text-[10px] text-(--qs-text-2)">
                          {JSON.stringify(log.payload, null, 2)}
                        </pre>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </HiveModalShell>
      ) : null}

      {demoResult ? (
        <HiveModalShell
          open
          onClose={() => setDemoResult(null)}
          ariaLabel="Commercial demo ready"
          zIndexClass="z-[70]"
          backdropClassName="bg-black/70"
          panelClassName="w-full max-w-md"
        >
          <V4Card className="space-y-4 p-5">
            <V4CardHeader
              as="h3"
              title="Commercial demo ready"
              description="Prihlás sa týmto účtom a prepni tenant v sidebar-e pre customer preview."
            />
            <div className="space-y-2 rounded-lg border border-(--qs-border) bg-black/35 p-3 font-mono text-xs text-(--qs-text-2)">
              <p>email: {demoResult.email}</p>
              <p>password: {demoResult.password}</p>
              <p>tenant: {demoResult.tenant_slug}</p>
              <p>
                profile: {demoResult.platform_mode}/{demoResult.tier}
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
                onClick={() => {
                  void copyText(
                    JSON.stringify(
                      {
                        email: demoResult.email,
                        password: demoResult.password,
                        tenant_slug: demoResult.tenant_slug,
                        platform_mode: demoResult.platform_mode,
                        tier: demoResult.tier,
                      },
                      null,
                      2,
                    ),
                  ).then(() => toast.success("Credentials skopírované"));
                }}
              >
                <CopyIcon className="h-4 w-4" aria-hidden />
                Copy
              </button>
              <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" onClick={() => setDemoResult(null)}>
                Close
              </button>
            </div>
          </V4Card>
        </HiveModalShell>
      ) : null}
    </div>
  );
}
