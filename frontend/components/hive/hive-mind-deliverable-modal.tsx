"use client";

import { X } from "lucide-react";

import { HiveModalShell } from "@/components/hive/hive-modal-shell";

interface HiveMindDeliverableModalProps {
  title: string;
  body: string;
  busy: boolean;
  onClose: () => void;
}

/** Full deliverable inspect overlay — keeps HiveMind canvas clean like V4 design. */
export function HiveMindDeliverableModal({ title, body, busy, onClose }: HiveMindDeliverableModalProps): JSX.Element | null {
  const open = Boolean(title || body || busy);

  return (
    <HiveModalShell
      open={open}
      onClose={onClose}
      ariaLabel="Deliverable preview"
      backdropClassName="bg-black/70 backdrop-blur-sm"
      panelClassName="v4-card flex max-h-[85vh] w-full max-w-2xl flex-col gap-4 overflow-hidden"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="v4-label-kicker">Deliverable prism</span>
          <h3 className="mt-1 truncate text-lg font-semibold text-(--qs-text)">{title || "Loading…"}</h3>
        </div>
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={onClose} aria-label="Close">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>
      {busy ? (
        <p className="text-sm text-(--qs-text-3)">Fetching markdown mirror…</p>
      ) : (
        <pre className="hive-scrollbar max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-(--qs-radius-lg) border border-(--qs-border) bg-black/40 p-4 font-mono text-xs leading-relaxed text-(--qs-text-2)">
          {body}
        </pre>
      )}
    </HiveModalShell>
  );
}
