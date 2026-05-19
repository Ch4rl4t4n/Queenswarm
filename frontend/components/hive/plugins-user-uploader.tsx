"use client";

import { useCallback, useState } from "react";

import { NeonButton } from "@/components/ui/neon-button";

/** Proxied multipart POST to `/api/v1/plugins/upload`. */
export function PluginsUserUploader() {
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState<string | null>(null);

  const onPick = useCallback(async (files: FileList | null) => {
    const f = files?.[0];
    if (!f) return;
    setBusy(true);
    setHint(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const res = await fetch("/api/proxy/plugins/upload", { method: "POST", credentials: "include", body: fd });
      const text = await res.text();
      if (!res.ok) {
        setHint(`Upload failed (${String(res.status)}): ${text.slice(0, 200)}`);
        return;
      }
      setHint("Uploaded — reloading…");
      window.location.reload();
    } catch (e) {
      setHint(e instanceof Error ? e.message : "upload_failed");
    } finally {
      setBusy(false);
    }
  }, []);

  return (
    <div className="rounded-2xl border border-dashed border-pollen/40 bg-black/30 p-4 md:p-6">
      <div className="v4-plugin-uploader-row flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen">
            Drop-in Python plugins
          </p>
          <p className="mt-2 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
            Mount path <code className="font-mono text-data">backend/plugins/user</code> maps into all API workers.
          </p>
        </div>
        <NeonButton
          type="button"
          variant="primary"
          className="w-full text-[10px] uppercase sm:w-auto"
          disabled={busy}
          onClick={() => document.getElementById("qs-plugin-py")?.click()}
        >
          {busy ? "Uploading…" : "Choose .py file"}
        </NeonButton>
        <input
          id="qs-plugin-py"
          type="file"
          accept=".py,text/x-python"
          className="hidden"
          onChange={(e) => void onPick(e.target.files)}
        />
      </div>
      {hint ? <p className="mt-4 font-[family-name:var(--font-poppins)] text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
