"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePutJson } from "@/lib/api";
import { CURATED_MEMORY_MAX_CHARS } from "@/lib/curated-memory-limits";

const KINDS = [
  { key: "mission", label: "Mission" },
  { key: "ideal_state", label: "Ideal state" },
  { key: "soul", label: "Soul" },
  { key: "skills_hierarchy", label: "Skills hierarchy" },
  { key: "instructions", label: "Instructions" },
] as const;

/** Tenant curated memory bundle — Queen context bootstrap files. */
export function CuratedMemoryPanel() {
  const [bundle, setBundle] = useState<Record<string, string>>({});
  const [active, setActive] = useState<string>("mission");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const data = await hiveGet<Record<string, string>>("memory/curated");
      setBundle(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Curated memory unavailable");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    setDraft(bundle[active] ?? "");
  }, [active, bundle]);

  async function save() {
    setBusy(true);
    try {
      await hivePutJson(`memory/curated/${encodeURIComponent(active)}`, { content_md: draft });
      toast.success("Curated memory saved");
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <V4Card>
      <V4CardHeader
        title="Curated memory"
        description="Queen bootstrap markdown — mission, ideal state, soul, skills hierarchy, and behavioral instructions."
      />
      {err ? <p className="mb-3 text-sm text-(--qs-red)">{err}</p> : null}
      <div className="mb-3 flex flex-wrap gap-2">
        {KINDS.map((kind) => (
          <button
            key={kind.key}
            type="button"
            className={active === kind.key ? "qs-btn qs-btn--primary qs-btn--sm" : "qs-btn qs-btn--ghost qs-btn--sm"}
            onClick={() => setActive(kind.key)}
          >
            {kind.label}
          </button>
        ))}
      </div>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        rows={14}
        maxLength={CURATED_MEMORY_MAX_CHARS}
        className="qs-input min-h-[280px] font-mono text-xs leading-relaxed"
        placeholder="Markdown for Queen context bootstrap…"
      />
      <div className="mt-2 text-xs text-(--qs-text-3)">
        {draft.length}/{CURATED_MEMORY_MAX_CHARS} characters
      </div>
      <div className="mt-3 flex justify-end">
        <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={busy} onClick={() => void save()}>
          {busy ? "Saving…" : "Save file"}
        </button>
      </div>
    </V4Card>
  );
}
