"use client";

import { useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hivePatchJson } from "@/lib/api";
import type { DashboardOperatorMe } from "@/lib/hive-dashboard-session";

interface ProfileSettingsClientProps {
  initialMe: DashboardOperatorMe | null;
}

function roleLabel(me: DashboardOperatorMe): string {
  if (me.is_admin) {
    return "Hive Admin";
  }
  return me.scopes.some((s) => s.includes("operator")) ? "Operator" : "Viewer";
}

export function ProfileSettingsClient({ initialMe }: ProfileSettingsClientProps) {
  const [me, setMe] = useState<DashboardOperatorMe | null>(initialMe);
  const [displayName, setDisplayName] = useState(initialMe?.display_name ?? "");
  const [timezone, setTimezone] = useState(initialMe?.timezone ?? "Europe/Bratislava");
  const [saving, setSaving] = useState(false);

  async function persist(): Promise<void> {
    if (!me) {
      toast.error("Not signed in");
      return;
    }
    try {
      setSaving(true);
      const next = await hivePatchJson<DashboardOperatorMe>("auth/me/profile", {
        display_name: displayName.trim() || null,
        timezone: timezone.trim() || null,
      });
      setMe(next);
      toast.success("Profile saved");
    } catch (e) {
      if (e instanceof HiveApiError) {
        toast.error(e.message);
      } else {
        toast.error("Unable to reach hive API");
      }
    } finally {
      setSaving(false);
    }
  }

  if (!me) {
    return (
      <article className="rounded-2xl border border-alert/30 bg-hive-card/90 p-6 md:p-8">
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger">
          Could not load /auth/me — check INTERNAL_BACKEND_ORIGIN and session cookie.
        </p>
      </article>
    );
  }

  const initialsSource = displayName.trim() || me.email;
  const initials = initialsSource.includes(" ")
    ? initialsSource
        .split(/\s+/)
        .map((w) => w[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : (me.email.split("@")[0] ?? "?").slice(0, 2).toUpperCase();

  return (
    <article className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-6 md:p-8">
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-orange-400 via-pollen to-[#FF6B9D] font-[family-name:var(--font-space-grotesk)] text-lg font-bold uppercase text-black shadow-[0_0_24px_rgb(255_184_0/0.35)] ring-4 ring-black/50">
            {initials}
          </div>
          <div>
            <p className="font-[family-name:var(--font-space-grotesk)] text-xl font-semibold text-[#fafafa]">
              {displayName.trim() || me.email.split("@")[0]}
            </p>
            <p className="font-[family-name:var(--font-inter)] text-sm text-muted-foreground">{me.email}</p>
          </div>
        </div>
        <p className="self-start rounded-xl border border-dashed border-cyan/[0.14] px-4 py-2 font-[family-name:var(--font-inter)] text-xs text-zinc-500">
          Avatar upload ships with media pipeline — JWT identity stays email-bound.
        </p>
      </div>
      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <label className="space-y-2">
          <span className="block font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Display name
          </span>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-2.5 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] focus:border-pollen/35 focus:outline-none focus:ring-2 focus:ring-pollen/20"
          />
        </label>
        <label className="space-y-2">
          <span className="block font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Timezone
          </span>
          <input
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            className="w-full rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-2.5 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] focus:border-pollen/35 focus:outline-none focus:ring-2 focus:ring-pollen/20"
          />
        </label>
        <label className="space-y-2">
          <span className="block font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Email
          </span>
          <input readOnly value={me.email} className="cursor-not-allowed w-full rounded-xl border border-cyan/[0.08] bg-black/35 px-4 py-2.5 font-[family-name:var(--font-inter)] text-sm text-zinc-400" />
          <span className="block font-[family-name:var(--font-inter)] text-xs text-zinc-500">JWT identity from login</span>
        </label>
        <label className="space-y-2">
          <span className="block font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Role
          </span>
          <input readOnly value={roleLabel(me)} className="cursor-not-allowed w-full rounded-xl border border-cyan/[0.08] bg-black/35 px-4 py-2.5 font-[family-name:var(--font-inter)] text-sm text-zinc-400" />
        </label>
      </div>
      <div className="mt-8 flex justify-end">
        <button
          type="button"
          disabled={saving}
          onClick={() => void persist()}
          className="rounded-xl bg-[#FFB800] px-5 py-2.5 font-[family-name:var(--font-space-grotesk)] text-sm font-semibold uppercase tracking-[0.08em] text-[#050510] shadow-[0_0_22px_rgba(255,184,0,0.35)] disabled:opacity-50"
        >
          Save profile
        </button>
      </div>
    </article>
  );
}
