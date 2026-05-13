"use client";

import { useState } from "react";

async function relayPost(segment: string): Promise<Response> {
  return fetch(`/api/proxy/${segment}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

/** Emergency swarm controls routed through Next.js JWT proxy (`/api/proxy`). */
export function HumanOverrideStrip() {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="rounded-xl border border-danger/35 bg-[#0d0d2b] p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">
            Human override
          </h3>
          <p className="mt-1 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
            Emergency pause or wake the full roster (JWT-proxied to FastAPI).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy !== null}
            onClick={async () => {
              if (!window.confirm("Pause every idle or running agent?")) return;
              setError(null);
              setBusy("pause");
              try {
                const r = await relayPost("agents/pause-all");
                if (!r.ok) setError(`pause-all HTTP ${String(r.status)}`);
              } catch (e) {
                setError(e instanceof Error ? e.message : "pause failed");
              } finally {
                setBusy(null);
              }
            }}
            className="rounded-lg border border-danger/40 px-3 py-2 font-[family-name:var(--font-poppins)] text-xs text-danger transition hover:bg-danger/10"
          >
            ⏸ Pause all
          </button>
          <button
            type="button"
            disabled={busy !== null}
            onClick={async () => {
              setError(null);
              setBusy("wake");
              try {
                const r = await relayPost("agents/wake-all");
                if (!r.ok) setError(`wake-all HTTP ${String(r.status)}`);
              } catch (e) {
                setError(e instanceof Error ? e.message : "wake failed");
              } finally {
                setBusy(null);
              }
            }}
            className="rounded-lg border border-success/40 px-3 py-2 font-[family-name:var(--font-poppins)] text-xs text-success transition hover:bg-success/10"
          >
            ▶ Wake all
          </button>
        </div>
      </div>
      {busy ? (
        <p className="mt-3 font-[family-name:var(--font-poppins)] text-[11px] text-pollen">Working… {busy}</p>
      ) : null}
      {error ? <p className="mt-2 font-[family-name:var(--font-poppins)] text-[11px] text-danger">{error}</p> : null}
    </div>
  );
}
