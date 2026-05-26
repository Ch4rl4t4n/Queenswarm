"use client";

import { Building2, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { memo, useCallback, useEffect, useState } from "react";

import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface MediaAgencyClientLane {
  id: string;
  label: string;
  channel: string;
  status: string;
  detail: string;
}

interface MediaAgencyAction {
  id: string;
  label: string;
  detail: string;
  priority: string;
  href?: string | null;
}

interface MediaAgencySnapshot {
  enabled: boolean;
  brand_name: string;
  white_label_ready: boolean;
  hide_platform_branding: boolean;
  publish_prep_pct: number;
  live_posts: number;
  client_lanes: MediaAgencyClientLane[];
  actions: MediaAgencyAction[];
}

export interface ExecutionStudioMediaAgencyPanelProps {
  onError: (message: string | null) => void;
}

function laneTone(status: string): "ok" | "warn" | "info" | "err" {
  if (status === "live_ok") return "ok";
  if (status === "simulate_ok") return "warn";
  if (status === "pending") return "info";
  return "err";
}

function ExecutionStudioMediaAgencyPanelInner({ onError }: ExecutionStudioMediaAgencyPanelProps) {
  const [snapshot, setSnapshot] = useState<MediaAgencySnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<MediaAgencySnapshot>("media-agency");
      setSnapshot(data);
    } catch (err) {
      if (err instanceof HiveApiError && err.status === 404) {
        setSnapshot(null);
        return;
      }
      onError(err instanceof Error ? err.message : "Media agency snapshot failed.");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!loading && snapshot && !snapshot.enabled) {
    return null;
  }

  return (
    <div id="media-agency" className="qs-bubble qs-bubble--tint-magenta shrink-0 space-y-3 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Building2 className="size-4 text-[#FF00AA]" aria-hidden />
          <h3 className="font-heading text-sm font-semibold text-(--qs-text)">Media Agency in a Box</h3>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-md p-1 text-(--qs-text-3) hover:text-cyan"
          aria-label="Refresh media agency snapshot"
        >
          {loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
        </button>
      </div>

      {loading && !snapshot ? (
        <p className="text-xs text-(--qs-text-3)">Loading agency lane…</p>
      ) : snapshot ? (
        <>
          <div className="flex flex-wrap gap-2 text-xs">
            <V4Badge tone={snapshot.white_label_ready ? "ok" : "warn"}>{snapshot.brand_name}</V4Badge>
            <V4Badge tone="info">Prep {snapshot.publish_prep_pct}%</V4Badge>
            <V4Badge tone="info">{snapshot.live_posts} live</V4Badge>
          </div>

          <ul className="space-y-1 text-xs">
            {snapshot.client_lanes.slice(0, 6).map((lane) => (
              <li key={lane.id} className="flex flex-wrap items-center justify-between gap-2 rounded bg-black/20 px-2 py-1">
                <span className="text-(--qs-text)">{lane.label}</span>
                <div className="flex items-center gap-2">
                  <span className="uppercase text-cyan">{lane.channel}</span>
                  <V4Badge tone={laneTone(lane.status)}>{lane.status}</V4Badge>
                </div>
              </li>
            ))}
          </ul>

          {snapshot.actions.length > 0 ? (
            <ul className="space-y-2">
              {snapshot.actions.map((action) => (
                <li key={action.id} className="rounded border border-white/10 bg-black/20 p-2 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium text-(--qs-text)">{action.label}</span>
                    {action.href ? (
                      <Link href={action.href} className="text-cyan hover:underline">
                        Open
                      </Link>
                    ) : null}
                  </div>
                  <p className="mt-1 text-(--qs-text-3)">{action.detail}</p>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export const ExecutionStudioMediaAgencyPanel = memo(ExecutionStudioMediaAgencyPanelInner);
