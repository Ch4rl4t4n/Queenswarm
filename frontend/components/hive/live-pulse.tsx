"use client";

import { ActivityIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { buildHiveWebsocketHref } from "@/lib/public-ws";

interface PulsePayload {
  type?: string;
  agents?: number;
  tasks_pending?: number;
  pollen_points_total?: number;
}

function finalizeSocketUrl(urlStr: string | null, guest: boolean, token?: string): string | null {
  if (!urlStr) {
    return null;
  }
  const url = new URL(urlStr);
  if (!guest && token) {
    url.searchParams.set("token", token);
  }
  return url.toString();
}

export function LivePulse() {
  const [payload, setPayload] = useState<PulsePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const url = useMemo(() => {
    const guest = process.env.NEXT_PUBLIC_HIVE_WS_GUEST === "true";
    const token =
      typeof window !== "undefined" ? window.sessionStorage.getItem("hive_jwt_optional") ?? undefined : undefined;
    const base =
      typeof window !== "undefined"
        ? (process.env.NEXT_PUBLIC_API_BASE ?? `${window.location.origin}/api/v1`)
        : process.env.NEXT_PUBLIC_API_BASE ?? "";
    const raw = buildHiveWebsocketHref(base, "/ws/live");
    return finalizeSocketUrl(raw, guest, token);
  }, []);

  useEffect(() => {
    if (!url) {
      setError("invalid_ws_url");
      return;
    }

    let alive = true;
    const ws = new WebSocket(url);

    ws.onmessage = (evt) => {
      if (!alive) {
        return;
      }
      try {
        const data = JSON.parse(evt.data as string) as PulsePayload;
        setPayload(data);
        setError(null);
      } catch {
        /* ignore malformed */
      }
    };

    ws.onerror = () => {
      setError("socket_error");
    };

    ws.onclose = () => {
      alive = false;
    };

    return () => {
      alive = false;
      ws.close();
    };
  }, [url]);

  return (
    <section className="rounded-2xl border border-[#00FFFF]/35 bg-black/35 p-4 shadow-[0_0_38px_rgba(0,255,255,0.18)]">
      <div className="mb-2 flex items-center gap-3">
        <ActivityIcon aria-hidden className="h-5 w-5 text-[#FFB800]" />
        <div>
          <p className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen">
            live hive pulse
          </p>
          <p className="font-[family-name:var(--font-poppins)] text-[11px] text-cyan/70">
            WebSocket `/api/v1/ws/live` fan-out snapshots
          </p>
        </div>
      </div>
      {error ? (
        <p className="font-[family-name:var(--font-poppins)] text-xs text-alert">
          realtime degraded · {error}
        </p>
      ) : null}
      {payload?.type === "hive.snapshot" ? (
        <dl className="mt-4 grid gap-4 font-[family-name:var(--font-poppins)] text-sm text-[#CCFFFF] sm:grid-cols-3">
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#FFB800]/80">agents</dt>
            <dd>{payload.agents ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#FFB800]/80">queue depth</dt>
            <dd>{payload.tasks_pending ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[#FFB800]/80">pollen Σ</dt>
            <dd>{payload.pollen_points_total?.toFixed(2) ?? "—"}</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-4 font-[family-name:var(--font-poppins)] text-xs text-cyan/60">
          awaiting swarm snapshot telemetry…
        </p>
      )}
    </section>
  );
}
