"use client";

import { CheckIcon, LinkIcon, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface PendingCapture {
  id: string;
  idea: string;
  connects_to: string[];
  might_use_for: string;
  key_tension: string;
  captured_at?: string | null;
}

interface ApproveResponse {
  id: string;
  obsidian_filename: string;
  wiki_slug: string;
  wikilinks: string[];
}

export interface SecondBrainCaptureApprovePanelProps {
  onApproved?: () => void;
}

/** SB3 — approve pending captures so Obsidian export includes auto wikilinks. */
export function SecondBrainCaptureApprovePanel({
  onApproved,
}: SecondBrainCaptureApprovePanelProps): JSX.Element | null {
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingCapture[]>([]);

  const reload = useCallback(async () => {
    try {
      const rows = await hiveGet<PendingCapture[]>("memory/wiki-layer/capture/pending");
      setPending(rows);
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 404) {
        setPending([]);
        return;
      }
      toast.error(e instanceof HiveApiError ? e.message : "Pending captures unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function approve(captureId: string) {
    setBusyId(captureId);
    try {
      const result = await hivePostJson<ApproveResponse>(
        `memory/wiki-layer/capture/${encodeURIComponent(captureId)}/approve`,
        {},
      );
      toast.success(`Approved — Obsidian wikilink [[${result.obsidian_filename}]]`);
      await reload();
      onApproved?.();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Approve failed.");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) {
    return (
      <V4Card>
        <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Loading pending captures…
        </div>
      </V4Card>
    );
  }

  if (pending.length === 0) {
    return null;
  }

  return (
    <V4Card data-testid="second-brain-capture-approve">
      <V4CardHeader
        title="Pending captures"
        description="Approve before Obsidian export — CONNECTS TO becomes vault wikilinks (SB3)."
        actions={<V4Badge tone="warn">{pending.length} pending</V4Badge>}
      />
      <ul className="space-y-3">
        {pending.map((item) => (
          <li
            key={item.id}
            className="rounded border border-white/10 bg-white/[0.02] p-3"
            data-testid={`capture-pending-${item.id}`}
          >
            <p className="text-sm font-medium">{item.idea}</p>
            {item.connects_to.length > 0 ? (
              <p className="mt-1 inline-flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
                <LinkIcon className="size-3" aria-hidden />
                {item.connects_to.map((link) => (
                  <span key={link} className="font-mono text-(--qs-cyan)">
                    [[{link}]]
                  </span>
                ))}
              </p>
            ) : null}
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm inline-flex items-center gap-1"
                disabled={busyId === item.id}
                onClick={() => void approve(item.id)}
              >
                {busyId === item.id ? (
                  <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                ) : (
                  <CheckIcon className="size-3.5" aria-hidden />
                )}
                Approve for vault
              </button>
            </div>
          </li>
        ))}
      </ul>
    </V4Card>
  );
}
