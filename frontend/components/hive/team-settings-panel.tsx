"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { TeamOverviewPayload } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

const TEAM_ROLES = ["owner", "admin", "member", "viewer", "guest"] as const;

interface InviteFormState {
  email: string;
  role: string;
}

export function TeamSettingsPanel() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TeamOverviewPayload | null>(null);
  const [inviteForm, setInviteForm] = useState<InviteFormState>({ email: "", role: "member" });
  const [saving, setSaving] = useState(false);

  const canManage = useMemo(() => Boolean(data?.permissions.includes("team:manage")), [data?.permissions]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/proxy/settings/team", { cache: "no-store" });
      const json = (await res.json().catch(() => ({}))) as TeamOverviewPayload | { detail?: string };
      if (!res.ok) {
        throw new Error(typeof json === "object" && json && "detail" in json ? String(json.detail) : "Load failed");
      }
      setData(json as TeamOverviewPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load team settings.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const submitInvite = useCallback(async () => {
    if (!inviteForm.email.trim()) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await fetch("/api/proxy/settings/team/invites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: inviteForm.email.trim().toLowerCase(),
          role: inviteForm.role,
        }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(String((json as { detail?: string }).detail ?? "Invite failed"));
      }
      setInviteForm((prev) => ({ ...prev, email: "" }));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed.");
    } finally {
      setSaving(false);
    }
  }, [inviteForm.email, inviteForm.role, load]);

  const updateRole = useCallback(async (membershipId: string, role: string) => {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/proxy/settings/team/members/${membershipId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(String((json as { detail?: string }).detail ?? "Role update failed"));
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Role update failed.");
    } finally {
      setSaving(false);
    }
  }, [load]);

  const removeMember = useCallback(async (membershipId: string) => {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`/api/proxy/settings/team/members/${membershipId}`, { method: "DELETE" });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(String((json as { detail?: string }).detail ?? "Remove failed"));
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Remove failed.");
    } finally {
      setSaving(false);
    }
  }, [load]);

  if (loading) {
    return <div className="rounded-2xl border border-cyan/20 bg-hive-card/70 p-5 text-sm text-zinc-400">Loading team…</div>;
  }
  if (error && !data) {
    return <div className="rounded-2xl border border-rose-500/30 bg-rose-950/30 p-5 text-sm text-rose-200">{error}</div>;
  }

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <h2 className="text-lg font-semibold text-zinc-100">Team & RBAC</h2>
        <p className="mt-2 text-sm text-zinc-400">
          Tenant role: <span className="font-medium text-amber-300">{data?.tenant_role ?? "guest"}</span> · permissions:{" "}
          {(data?.permissions ?? []).join(", ")}
        </p>
      </header>

      <div className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-200">Invite member</h3>
        <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
          <input
            value={inviteForm.email}
            onChange={(event) => setInviteForm((prev) => ({ ...prev, email: event.target.value }))}
            placeholder="teammate@company.com"
            className="rounded-xl border border-cyan/20 bg-hive-void/70 px-3 py-2 text-sm text-zinc-100 outline-none ring-cyan/40 focus:ring-2"
            disabled={!canManage || saving}
          />
          <select
            value={inviteForm.role}
            onChange={(event) => setInviteForm((prev) => ({ ...prev, role: event.target.value }))}
            className="rounded-xl border border-cyan/20 bg-hive-void/70 px-3 py-2 text-sm text-zinc-100 outline-none ring-cyan/40 focus:ring-2"
            disabled={!canManage || saving}
          >
            {TEAM_ROLES.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void submitInvite()}
            disabled={!canManage || saving || !inviteForm.email.trim()}
            className="rounded-xl bg-amber-400 px-4 py-2 text-sm font-semibold text-black transition enabled:hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send invite
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-200">Members</h3>
        <div className="mt-3 space-y-2">
          {(data?.members ?? []).map((member) => (
            <div
              key={member.id}
              className={cn("grid gap-2 rounded-xl border border-cyan/10 p-3", "sm:grid-cols-[1fr_auto_auto] sm:items-center")}
            >
              <div>
                <p className="text-sm font-medium text-zinc-100">{member.email}</p>
                <p className="text-xs text-zinc-500">Joined {new Date(member.joined_at).toLocaleString()}</p>
              </div>
              <select
                value={member.role}
                disabled={!canManage || saving}
                onChange={(event) => void updateRole(member.id, event.target.value)}
                className="rounded-lg border border-cyan/20 bg-hive-void/70 px-3 py-2 text-sm text-zinc-100"
              >
                {TEAM_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => void removeMember(member.id)}
                disabled={!canManage || saving}
                className="rounded-lg border border-rose-400/40 px-3 py-2 text-xs text-rose-200 transition enabled:hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-cyan/15 bg-hive-card/70 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-200">Pending invites</h3>
        <div className="mt-3 space-y-2">
          {(data?.invites ?? []).length ? (
            data?.invites.map((invite) => (
              <div key={invite.id} className="rounded-xl border border-cyan/10 p-3 text-sm text-zinc-300">
                {invite.email} · {invite.role} · token <span className="font-mono text-xs text-cyan-300">{invite.invite_token}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-zinc-500">No pending invites.</p>
          )}
        </div>
      </div>

      {error ? <p className="text-sm text-rose-300">{error}</p> : null}
    </section>
  );
}
