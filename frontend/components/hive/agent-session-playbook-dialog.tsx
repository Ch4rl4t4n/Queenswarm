"use client";

import type { JSX } from "react";

import { Loader2Icon } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveModalShell } from "@/components/hive/hive-modal-shell";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import {
  defaultPlaybookTopicTags,
  parsePlaybookTopicTags,
  type SessionPlaybookPreview,
} from "@/lib/session-playbook-utils";

interface AgentSessionPlaybookDialogProps {
  sessionId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved?: () => void;
}

/** Preview and edit operator playbook metadata before Recipe Library save. */
export function AgentSessionPlaybookDialog({
  sessionId,
  open,
  onOpenChange,
  onSaved,
}: AgentSessionPlaybookDialogProps): JSX.Element | null {
  const [preview, setPreview] = useState<SessionPlaybookPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [topicTagsRaw, setTopicTagsRaw] = useState(defaultPlaybookTopicTags().join(", "));
  const [markVerified, setMarkVerified] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setPreview(null);
    void hiveGet<SessionPlaybookPreview>(`agents/sessions/${encodeURIComponent(sessionId)}/playbook/preview`)
      .then((body) => {
        if (cancelled) {
          return;
        }
        setPreview(body);
        setName(body.suggested_name);
        setDescription(
          `Operator playbook from supervisor session (${body.session_status}, ${body.sub_agent_count} sub-agents).`,
        );
        setTopicTagsRaw(defaultPlaybookTopicTags().join(", "));
        setMarkVerified(body.can_mark_verified);
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }
        toast.error(err instanceof HiveApiError ? err.message : "Playbook preview unavailable");
        onOpenChange(false);
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, onOpenChange, sessionId]);

  async function handleSave(): Promise<void> {
    const trimmedName = name.trim();
    if (trimmedName.length < 1) {
      toast.error("Playbook name is required.");
      return;
    }
    setSaving(true);
    try {
      const saved = await hivePostJson<{
        recipe_id: string;
        name: string;
        step_count: number;
        verified: boolean;
      }>(`agents/sessions/${encodeURIComponent(sessionId)}/playbook`, {
        name: trimmedName,
        description: description.trim() || undefined,
        topic_tags: parsePlaybookTopicTags(topicTagsRaw),
        mark_verified: markVerified,
      });
      toast.success(
        <span>
          Playbook saved ({saved.step_count} steps{saved.verified ? ", verified" : ""}).{" "}
          <Link href="/recipes" className="underline text-pollen">
            Open recipes
          </Link>
        </span>,
      );
      onOpenChange(false);
      onSaved?.();
    } catch (err) {
      if (err instanceof HiveApiError && err.status === 403) {
        toast.error("Saving playbooks requires dash:recipe_write scope.");
      } else {
        toast.error(err instanceof HiveApiError ? err.message : "Playbook save failed");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <HiveModalShell
      open={open}
      onClose={() => onOpenChange(false)}
      labelledBy="session-playbook-title"
      zIndexClass="z-[70]"
      panelClassName="w-full max-w-lg rounded-2xl border border-[color:var(--qs-border-2)] bg-[#070d16] p-5 shadow-[0_0_40px_rgba(255,184,0,0.08)]"
    >
      <h2 id="session-playbook-title" className="text-lg font-semibold text-zinc-100">
        Save operator playbook
      </h2>
      <p className="mt-1 text-xs text-zinc-500">
        Persist this supervisor session as a reusable Recipe Library template.
      </p>

      {loading ? (
        <div className="mt-6 flex items-center gap-2 text-sm text-zinc-400">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
          Loading preview…
        </div>
      ) : preview ? (
        <>
          <div className="mt-4 flex flex-wrap gap-2 text-[10px] uppercase tracking-wider text-zinc-500">
            <span className="rounded-md border border-zinc-800 px-2 py-1">{preview.step_count} steps</span>
            <span className="rounded-md border border-zinc-800 px-2 py-1">{preview.sub_agent_count} sub-agents</span>
            <span className="rounded-md border border-zinc-800 px-2 py-1">{preview.session_status}</span>
          </div>

          <label className="mt-4 block text-xs text-zinc-400">
            Playbook name
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={200}
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-pollen/50"
            />
          </label>

          <label className="mt-3 block text-xs text-zinc-400">
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              maxLength={4000}
              className="mt-1 w-full resize-y rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-pollen/50"
            />
          </label>

          <label className="mt-3 block text-xs text-zinc-400">
            Topic tags (comma-separated)
            <input
              value={topicTagsRaw}
              onChange={(event) => setTopicTagsRaw(event.target.value)}
              placeholder="supervisor, operator_playbook, pricing"
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-pollen/50"
            />
          </label>

          <label className="mt-4 flex items-start gap-2 text-xs text-zinc-300">
            <input
              type="checkbox"
              checked={markVerified}
              disabled={!preview.can_mark_verified}
              onChange={(event) => setMarkVerified(event.target.checked)}
              className="mt-0.5 accent-[color:var(--qs-pollen)]"
            />
            <span>
              Mark as verified recipe
              {!preview.can_mark_verified ? (
                <span className="mt-0.5 block text-zinc-500">Available when the session is completed or mostly verified.</span>
              ) : null}
            </span>
          </label>
        </>
      ) : null}

      <div className="mt-6 flex flex-wrap justify-end gap-3">
        <button type="button" className="qs-btn qs-btn--ghost min-w-[9rem]" onClick={() => onOpenChange(false)}>
          Cancel
        </button>
        <button
          type="button"
          disabled={loading || saving || !preview}
          className="qs-btn qs-btn--primary min-w-[9rem] gap-1.5 disabled:opacity-40"
          onClick={() => void handleSave()}
        >
          {saving ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : null}
          Save playbook
        </button>
      </div>
    </HiveModalShell>
  );
}
