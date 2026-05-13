import { PuzzleIcon } from "lucide-react";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { PluginsUserUploader } from "@/components/hive/plugins-user-uploader";
import { hiveServerRawJson } from "@/lib/hive-server";

export const dynamic = "force-dynamic";

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

export default async function PluginsPhasePage() {
  const pack = await hiveServerRawJson<PluginsPayload>("/plugins");

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Plugin lattice"
        subtitle="Built-in hive modules + proxied uploads of operator ``.py`` drop-ins (`/api/v1/plugins`)."
        actions={
          <span className="flex items-center gap-2 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-500">
            <PuzzleIcon className="h-4 w-4 text-pollen" />
            gen {pack?.reload_generation ?? "—"}
          </span>
        }
      />
      {!pack ? (
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger">
          Plugin relay offline — confirm session + proxy.
        </p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {pack.installed.map((plug) => (
              <article
                key={plug.id}
                className="rounded-3xl border border-white/[0.08] bg-black/40 p-5 neon-border-pg shadow-[0_0_32px_rgba(0,255,255,0.08)]"
              >
                <p className="font-[family-name:var(--font-poppins)] text-xl font-semibold text-pollen">
                  {plug.title ?? plug.id}
                </p>
                <p className="mt-3 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-400">
                  v{plug.version ?? "?"} ·{" "}
                  <span className={plug.status === "active" ? "text-success" : "text-zinc-500"}>{plug.status ?? "n/a"}</span>
                </p>
                <p className="mt-4 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
                  {plug.description ?? "Awaiting operator notes."}
                </p>
                <p className="mt-4 font-[family-name:var(--font-jetbrains-mono)] text-[11px] uppercase tracking-[0.2em] text-zinc-600">
                  PATCH /plugins/{plug.id} wired for future hot toggles
                </p>
              </article>
            ))}
          </div>
          <PluginsUserUploader />
          <div className="rounded-3xl border border-white/[0.08] bg-black/35 p-5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
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
      <div className="rounded-2xl border border-dashed border-pollen/35 bg-black/30 p-6 text-center font-[family-name:var(--font-inter)] text-sm text-zinc-400">
        PATCH toggles bump reload generation · DELETE removes user ``.py`` only.
      </div>
    </div>
  );
}
