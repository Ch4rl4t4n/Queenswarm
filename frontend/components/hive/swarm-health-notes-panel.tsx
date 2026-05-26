"use client";

import { AlertTriangle, Bell, CheckCircle2, Info } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveDelete, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

interface HealthNote {
  id: string;
  at: string;
  severity: "info" | "warn" | "error";
  source: string;
  message: string;
  manager_agent_id: string | null;
  metadata: Record<string, unknown>;
}

interface SwarmHealthNotesPanelProps {
  swarmId: string;
  onChanged?: () => void;
}

function formatTimeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) return "just now";
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 90) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 36) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function SeverityIcon({ s }: { s: HealthNote["severity"] }) {
  if (s === "error") return <AlertTriangle className="h-3.5 w-3.5 text-(--qs-red)" aria-hidden />;
  if (s === "warn") return <Bell className="h-3.5 w-3.5 text-pollen" aria-hidden />;
  return <Info className="h-3.5 w-3.5 text-(--qs-cyan)" aria-hidden />;
}

export function SwarmHealthNotesPanel({ swarmId, onChanged }: SwarmHealthNotesPanelProps) {
  const [notes, setNotes] = useState<HealthNote[]>([]);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [severity, setSeverity] = useState<HealthNote["severity"]>("warn");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<{ items: HealthNote[] }>(
        `swarms/${encodeURIComponent(swarmId)}/health-notes`,
      );
      setNotes(data.items ?? []);
    } catch (e) {
      if (e instanceof HiveApiError && e.status !== 404) {
        toast.error(e.message);
      }
      setNotes([]);
    } finally {
      setLoading(false);
    }
  }, [swarmId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function addNote() {
    const message = draft.trim();
    if (!message) return;
    setBusy(true);
    try {
      await hivePostJson(`swarms/${encodeURIComponent(swarmId)}/health-notes`, {
        message,
        severity,
        source: "operator",
      });
      setDraft("");
      await reload();
      onChanged?.();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Failed to add note");
    } finally {
      setBusy(false);
    }
  }

  async function ackNote(noteId: string | null) {
    setBusy(true);
    try {
      const qs = noteId ? `?note_id=${encodeURIComponent(noteId)}` : "";
      await hiveDelete(`swarms/${encodeURIComponent(swarmId)}/health-notes${qs}`);
      await reload();
      onChanged?.();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Failed to clear note");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-(--qs-radius-sm) border border-(--qs-border) bg-(--qs-surface) p-4">
      <header className="mb-3 flex items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wider text-(--qs-text-3)">Health notes</p>
          <p className="text-xs text-(--qs-text-3)">
            Advisory signals from Queen + operator. Cap of 10 most recent. Acknowledge to clear.
          </p>
        </div>
        {notes.length > 0 ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            disabled={busy}
            onClick={() => void ackNote(null)}
          >
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
            Clear all
          </button>
        ) : null}
      </header>

      <div className="mb-3 flex flex-wrap gap-2">
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value as HealthNote["severity"])}
          className="qs-input w-28 text-xs"
        >
          <option value="info">info</option>
          <option value="warn">warn</option>
          <option value="error">error</option>
        </select>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="e.g. Marketing Manager slow on Notion writes — increase tool timeout"
          className="qs-input flex-1 text-xs"
          onKeyDown={(e) => {
            if (e.key === "Enter") void addNote();
          }}
        />
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm"
          disabled={busy || !draft.trim()}
          onClick={() => void addNote()}
        >
          Add note
        </button>
      </div>

      {loading ? (
        <p className="text-xs text-(--qs-text-3)">Loading…</p>
      ) : notes.length === 0 ? (
        <p className="text-xs text-(--qs-text-3)">No active notes — swarm is clean.</p>
      ) : (
        <ul className="space-y-1.5">
          {notes.map((n) => (
            <li
              key={n.id}
              className={cn(
                "flex items-start gap-2 rounded-(--qs-radius-sm) border bg-(--qs-surface-2) px-3 py-2 text-xs",
                n.severity === "error" && "border-(--qs-red)/40",
                n.severity === "warn" && "border-pollen/40",
                n.severity === "info" && "border-(--qs-cyan)/30",
              )}
            >
              <SeverityIcon s={n.severity} />
              <div className="min-w-0 flex-1">
                <p className="text-(--qs-text)">{n.message}</p>
                <p className="mt-0.5 text-[10px] text-(--qs-text-3)">
                  {n.source} · {formatTimeAgo(n.at)}
                </p>
              </div>
              <button
                type="button"
                title="Acknowledge"
                className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
                disabled={busy}
                onClick={() => void ackNote(n.id)}
              >
                ✓
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
