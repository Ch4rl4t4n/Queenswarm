"use client";

import { PuzzleIcon } from "lucide-react";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { PluginsUserUploader } from "@/components/hive/plugins-user-uploader";
import { V4PageCanvas } from "@/components/ui/v4";

interface PluginInstalled {
  id: string;
  title?: string;
  enabled?: boolean;
  description?: string;
  version?: string;
  status?: string;
}

interface PluginsPayload {
  reload_generation?: number;
  builtin?: PluginInstalled[];
  installed: PluginInstalled[];
  user?: PluginInstalled[];
}

interface PluginsPageClientProps {
  pack: PluginsPayload | null;
}

export function PluginsPageClient({ pack }: PluginsPageClientProps) {
  return (
    <V4PageCanvas className="gap-8">
      <HivePageHeader
        title="Plugin lattice"
        subtitle="Built-in hive modules + proxied uploads of operator ``.py`` drop-ins (`/api/v1/plugins`)."
        actions={
          <span className="flex items-center gap-2 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
            <PuzzleIcon className="h-4 w-4 text-pollen" />
            gen {pack?.reload_generation ?? "—"}
          </span>
        }
      />

      {!pack ? (
        <p className="font-[family-name:var(--font-poppins)] text-sm text-danger">
          Plugin relay offline — confirm session + proxy.
        </p>
      ) : (
        <>
          <div className="v4-plugin-grid">
            {pack.installed.map((plug) => (
              <article
                key={plug.id}
                className="rounded-3xl qs-rim bg-black/40 p-4 shadow-[0_0_32px_rgba(0,255,255,0.08)] md:p-5"
              >
                <p className="font-[family-name:var(--font-poppins)] text-xl font-semibold text-pollen">
                  {plug.title ?? plug.id}
                </p>
                <p className="mt-3 font-[family-name:var(--font-poppins)] text-xs text-zinc-400">
                  v{plug.version ?? "?"} ·{" "}
                  <span className={plug.status === "active" ? "text-success" : "text-zinc-500"}>{plug.status ?? "n/a"}</span>
                </p>
                <p className="mt-4 font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
                  {plug.description ?? "Awaiting operator notes."}
                </p>
                <p className="mt-4 font-[family-name:var(--font-poppins)] text-[11px] uppercase tracking-[0.2em] text-zinc-600">
                  Built-in toggles persist via PATCH /plugins/{plug.id}
                </p>
              </article>
            ))}
          </div>
          <PluginsUserUploader />
          <div className="rounded-3xl qs-rim bg-black/35 p-4 font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500 md:p-5">
            <p className="text-xs font-semibold text-pollen">User rows</p>
            <ul className="mt-3 space-y-2">
              {(pack.user ?? []).length === 0 ? <li>No user plugins scanned yet.</li> : null}
              {(pack.user ?? []).map((u) => (
                <li key={u.id}>
                  {u.id} · {(u.status ?? "n/a").toString()} · {String(u.description ?? "").slice(0, 140)}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      <div className="rounded-2xl border border-dashed border-pollen/35 bg-black/30 p-4 text-center font-[family-name:var(--font-poppins)] text-sm text-zinc-400 md:p-6">
        Built-in PATCH toggles persist to the hive plugin manifest · DELETE removes user ``.py`` only.
      </div>
    </V4PageCanvas>
  );
}
