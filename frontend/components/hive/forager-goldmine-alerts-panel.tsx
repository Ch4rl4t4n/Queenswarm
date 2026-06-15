"use client";

import { Loader2, Send } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { ForagerGoldmineAlertRow, ForagerGoldmineAlertsPayload } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface ForagerGoldmineAlertsPanelProps {
  canManage: boolean;
  busy: string | null;
  onDispatched: () => Promise<void>;
}

function SkillBundleBadges({ slugs }: { slugs: string[] }): JSX.Element | null {
  if (!slugs.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {slugs.map((slug) => (
        <span
          key={slug}
          className="inline-flex max-w-full items-center rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-(family-name:--font-jetbrains-mono) text-[10px] text-emerald-200"
        >
          {slug}
        </span>
      ))}
    </div>
  );
}

/** DG7 — Delta alert inbox with one-click Kanban dispatch + skill bundle. */
export function ForagerGoldmineAlertsPanel({
  canManage,
  busy,
  onDispatched,
}: ForagerGoldmineAlertsPanelProps): JSX.Element | null {
  const [payload, setPayload] = useState<ForagerGoldmineAlertsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [dispatchingId, setDispatchingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<ForagerGoldmineAlertsPayload>("dashboard/forager-goldmine-alerts?limit=12");
      setPayload(data);
      setErr(null);
    } catch (e) {
      setPayload(null);
      setErr(e instanceof HiveApiError ? e.message : "Goldmine alerts unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function dispatchAlert(alert: ForagerGoldmineAlertRow) {
    if (!canManage) return;
    setDispatchingId(alert.forager_id);
    try {
      const res = await hivePostJson<{
        ok: boolean;
        title?: string;
        skill_slugs?: string[];
        new_item_count?: number;
      }>(`foragers/${encodeURIComponent(alert.forager_id)}/promote-task`, {
        mode: "alert",
        title: `Goldmine alert · ${alert.forager_name} · ${alert.new_item_count} new`,
        include_skill_bundle: true,
      });
      const skillNote =
        res.skill_slugs && res.skill_slugs.length
          ? ` · skills: ${res.skill_slugs.slice(0, 3).join(", ")}`
          : "";
      toast.success(
        res.title ? `${res.title} → Triage${skillNote}` : "Goldmine alert dispatched to Mission Kanban",
      );
      await onDispatched();
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Dispatch failed.");
    } finally {
      setDispatchingId(null);
    }
  }

  if (!loading && !err && (payload?.enabled === false || !payload?.alerts?.length)) {
    return null;
  }

  const alerts = payload?.alerts ?? [];

  return (
    <div data-testid="forager-goldmine-alerts-panel">
      <V4Card className="border-pollen/25 bg-pollen/5">
        <V4CardHeader
          title="Goldmine alerts"
          description="DG7 — new signals since last run · dispatch to Mission Kanban with skill bundle."
        />
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Loading delta alerts…
          </div>
        ) : err ? (
          <p className="text-sm text-(--qs-text-3)">{err}</p>
        ) : !alerts.length ? (
          <p className="text-sm text-(--qs-text-3)">No new signals since last scheduled run.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {alerts.map((alert) => {
              const dispatchBusy = busy === `goldmine-${alert.forager_id}` || dispatchingId === alert.forager_id;
              return (
                <div
                  key={alert.forager_id}
                  className="rounded-lg border border-white/10 bg-black/20 p-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-(--qs-text-1)">{alert.forager_name}</span>
                        <V4Badge tone="info">{alert.source_type}</V4Badge>
                        <V4Badge tone="warn">{alert.headline}</V4Badge>
                      </div>
                      <SkillBundleBadges slugs={alert.skill_bundle} />
                      {alert.preview_items.length > 0 ? (
                        <ul className="space-y-1 text-xs text-(--qs-text-3)">
                          {alert.preview_items.slice(0, 3).map((item) => (
                            <li key={item.id} className="truncate">
                              {item.title}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      className={cn("qs-btn qs-btn--primary qs-btn--sm gap-2 shrink-0")}
                      disabled={!canManage || dispatchBusy}
                      onClick={() => void dispatchAlert(alert)}
                    >
                      {dispatchBusy ? (
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      ) : (
                        <Send className="h-4 w-4" aria-hidden />
                      )}
                      Dispatch
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </V4Card>
    </div>
  );
}
