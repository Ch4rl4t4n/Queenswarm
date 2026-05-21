"use client";

import Link from "next/link";
import { Loader2Icon, Moon } from "lucide-react";
import { useCallback, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";

interface DreamingSettingsResponse {
  enabled: boolean;
  frequency_hours: number;
  routine_id: string | null;
}

interface DreamCycleRow {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  items_processed: number;
  items_deduplicated: number;
  items_consolidated: number;
}

function cycleStatusTone(status: string): "ok" | "warn" | "err" | "info" {
  const s = status.toLowerCase();
  if (s.includes("complete") || s.includes("success")) {
    return "ok";
  }
  if (s.includes("fail") || s.includes("error")) {
    return "err";
  }
  if (s.includes("run") || s.includes("queue") || s.includes("pending")) {
    return "info";
  }
  return "warn";
}

/** Nightly dreaming snapshot for dashboard — full controls live in Knowledge hub. */
export function DreamingSummaryCard(): JSX.Element {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [settings, setSettings] = useState<DreamingSettingsResponse | null>(null);
  const [latest, setLatest] = useState<DreamCycleRow | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, rows] = await Promise.all([
        hiveGet<DreamingSettingsResponse>("dreaming/settings"),
        hiveGet<DreamCycleRow[]>("dreaming/cycles?limit=1"),
      ]);
      setSettings(s);
      setLatest(rows[0] ?? null);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Dreaming summary unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    initialDelayMs: DASHBOARD_BOOT_STAGGER_MS.dreamingSummary,
  });

  return (
    <V4Card className="v4-card-interactive">
      <V4CardHeader
        title="Memory · Dreaming"
        description="Nightly consolidation cycle"
        actions={
          <Link href="/knowledge" className="text-xs text-cyan underline-offset-2 hover:underline">
            Open Knowledge
          </Link>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading dream report…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && settings ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Moon className="h-4 w-4 text-(--qs-purple-bright)" aria-hidden />
            <span className="text-(--qs-text-2)">
              {settings.enabled ? `Every ${settings.frequency_hours}h` : "Disabled"}
            </span>
            <V4Badge tone={settings.enabled ? "ok" : "warn"}>{settings.enabled ? "on" : "off"}</V4Badge>
          </div>

          {latest ? (
            <div className="rounded-xl border border-(--qs-border) bg-black/25 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] text-(--qs-text-3)">
                  {new Date(latest.started_at).toLocaleString("sk-SK")}
                </span>
                <V4Badge tone={cycleStatusTone(latest.status)}>{latest.status}</V4Badge>
              </div>
              <p className="mt-2 text-sm text-(--qs-text-2)">
                processed={latest.items_processed} · consolidated=
                <span className="text-pollen">{latest.items_consolidated}</span> · dedup=
                <span className="text-cyan">{latest.items_deduplicated}</span>
              </p>
            </div>
          ) : (
            <p className="text-sm text-(--qs-text-3)">No dream reports yet — enable Dreaming in Knowledge.</p>
          )}
        </div>
      ) : null}
    </V4Card>
  );
}
