"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveSwitch } from "@/components/ui/hive-switch";
import { HiveApiError, hivePatchJson } from "@/lib/api";
import type { DashboardOperatorMe } from "@/lib/hive-dashboard-session";

const ROWS: { id: string; label: string; defaultOn: boolean }[] = [
  { id: "task", label: "Task completed", defaultOn: true },
  { id: "confidence", label: "Confidence below 70%", defaultOn: true },
  { id: "cost", label: "Cost threshold reached", defaultOn: false },
  { id: "offline", label: "Agent went offline", defaultOn: true },
  { id: "battle", label: "New recipe battle-tested", defaultOn: true },
];

interface NotificationsSettingsClientProps {
  initialMe: DashboardOperatorMe | null;
}

export function NotificationsSettingsClient({ initialMe }: NotificationsSettingsClientProps) {
  const [states, setStates] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(ROWS.map((r) => [r.id, r.defaultOn])) as Record<string, boolean>,
  );

  useEffect(() => {
    if (!initialMe) {
      return;
    }
    setStates((prev) => {
      const next = { ...prev };
      const prefs = initialMe.notification_prefs ?? {};
      for (const r of ROWS) {
        if (prefs[r.id] !== undefined) {
          next[r.id] = prefs[r.id] ?? false;
        }
      }
      return next;
    });
  }, [initialMe]);

  async function pushPref(id: string, value: boolean): Promise<void> {
    try {
      const refreshed = await hivePatchJson<DashboardOperatorMe>("auth/me/notifications", { [id]: value });
      setStates((prev) => {
        const out = { ...prev, [id]: value };
        for (const k of ROWS.map((x) => x.id)) {
          const vpref = refreshed.notification_prefs[k];
          if (typeof vpref === "boolean") {
            out[k] = vpref;
          }
        }
        return out;
      });
    } catch (e) {
      if (e instanceof HiveApiError) {
        toast.error(e.message);
      } else {
        toast.error("Notification sync failed.");
      }
    }
  }

  if (!initialMe) {
    return (
      <article className="rounded-2xl border border-alert/30 bg-hive-card/90 p-6 md:p-8">
        <p className="text-sm text-danger">Konfigurácia notifikácií potrebuje platnú hive session.</p>
      </article>
    );
  }

  return (
    <article className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-6 md:p-8">
      <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
        Notifications
      </h2>
      <ul className="mt-8 space-y-4">
        {ROWS.map((r) => (
          <li key={r.id} className="flex items-center justify-between gap-4 border-b border-cyan/[0.06] pb-4">
            <span className="font-[family-name:var(--font-inter)] text-sm text-[#e4e4e7]">{r.label}</span>
            <HiveSwitch
              checked={states[r.id] ?? false}
              onCheckedChange={(value) => {
                void pushPref(r.id, value);
              }}
              aria-label={r.label}
            />
          </li>
        ))}
      </ul>
    </article>
  );
}
