"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { QsSelect } from "@/components/ui/qs-select";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import type { TeamOverviewPayload } from "@/lib/hive-types";

const TEAM_ROLES = ["owner", "admin", "member", "viewer", "guest"] as const;
const TEAM_ROLE_OPTIONS = TEAM_ROLES.map((role) => ({ value: role, label: role }));

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
    return (
      <V4Card>
        <p className="text-sm text-(--qs-text-3)">Loading team…</p>
      </V4Card>
    );
  }
  if (error && !data) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-red)">{error}</p>
      </V4Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <V4Card>
        <V4CardHeader
          title="Team & RBAC"
          description={
            <>
              Tenant role: <span className="font-medium text-(--qs-amber)">{data?.tenant_role ?? "guest"}</span> ·
              permissions: {(data?.permissions ?? []).join(", ")}
            </>
          }
          hint={sectionHintNode("settingsTeam")}
        />
      </V4Card>

      <V4Card>
        <V4CardHeader
          title="Invite member"
          description="Send an email invite with a tenant role."
          hint={sectionHintNode("teamInvite")}
        />
        <div className="v4-settings-inline-form grid gap-3">
          <input
            value={inviteForm.email}
            onChange={(event) => setInviteForm((prev) => ({ ...prev, email: event.target.value }))}
            placeholder="teammate@company.com"
            className="qs-input min-w-0"
            disabled={!canManage || saving}
          />
          <QsSelect
            value={inviteForm.role}
            onValueChange={(next) => setInviteForm((prev) => ({ ...prev, role: next }))}
            className="min-h-11 w-full rounded-(--qs-radius-sm) sm:w-auto"
            disabled={!canManage || saving}
            options={TEAM_ROLE_OPTIONS}
          />
          <button
            type="button"
            onClick={() => void submitInvite()}
            disabled={!canManage || saving || !inviteForm.email.trim()}
            className="qs-btn qs-btn--primary qs-btn--sm w-full sm:w-auto"
          >
            Send invite
          </button>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          title="Members"
          description="Active tenant memberships and roles."
          hint={sectionHintNode("teamMembers")}
        />
        <div className="flex flex-col gap-2">
          {(data?.members ?? []).map((member) => (
            <div
              key={member.id}
              className="v4-settings-member-row grid gap-2 rounded-(--qs-radius-sm) border border-(--qs-border) bg-white/2 p-3 sm:grid-cols-[1fr_auto_auto] sm:items-center"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-(--qs-text) break-all">{member.email}</p>
                <p className="text-xs text-(--qs-text-3)">Joined {new Date(member.joined_at).toLocaleString()}</p>
              </div>
              <QsSelect
                value={member.role}
                disabled={!canManage || saving}
                onValueChange={(next) => void updateRole(member.id, next)}
                className="min-h-10 w-full rounded-(--qs-radius-sm) text-sm sm:w-auto"
                options={TEAM_ROLE_OPTIONS}
              />
              <button
                type="button"
                onClick={() => void removeMember(member.id)}
                disabled={!canManage || saving}
                className="qs-btn qs-btn--danger qs-btn--sm w-full sm:w-auto"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          title="Pending invites"
          description="Outstanding invite tokens awaiting acceptance."
          hint={sectionHintNode("teamPendingInvites")}
        />
        <div className="flex flex-col gap-2">
          {(data?.invites ?? []).length ? (
            data?.invites.map((invite) => (
              <div
                key={invite.id}
                className="rounded-(--qs-radius-sm) border border-(--qs-border) bg-white/2 p-3 text-sm text-(--qs-text-2)"
              >
                {invite.email} · {invite.role} · token{" "}
                <span className="font-mono text-xs text-(--qs-text-3)">{invite.invite_token}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-(--qs-text-3)">No pending invites.</p>
          )}
        </div>
      </V4Card>

      {error ? <p className="text-sm text-(--qs-red)">{error}</p> : null}
    </div>
  );
}
