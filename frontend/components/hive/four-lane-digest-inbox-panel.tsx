"use client";

import Link from "next/link";
import { CheckCircle2, ExternalLink, Loader2, ListTodo } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { InlineSectionHintKey } from "@/components/hive/inline-section-hint";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";

interface DigestInboxItem {
  session_id: string;
  lane_id: string;
  lane_label: string;
  title: string;
  excerpt: string;
  session_status: string;
  approval_state: string | null;
  created_at: string;
  promote_ready: boolean;
  session_href: string;
  task_id: string | null;
}

interface DigestInboxSnapshot {
  pending_count: number;
  items: DigestInboxItem[];
}

function FourLaneDigestInboxPanelInner() {
  const [data, setData] = useState<DigestInboxSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const body = await hiveGet<DigestInboxSnapshot>("solo-operator/four-lanes/digest-inbox?limit=15");
      setData(body);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Digest inbox unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const promote = useCallback(
    async (item: DigestInboxItem) => {
      setBusy(item.session_id);
      try {
        const result = await hivePostJson<{
          ok: boolean;
          task_id?: string;
          tasks_href?: string;
        }>(`solo-operator/four-lanes/digest-inbox/${encodeURIComponent(item.session_id)}/promote`, {
          approve_first: true,
        });
        if (result.ok) {
          toast.success("Digest → task vytvorený");
          await reload();
        }
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Promote failed");
      } finally {
        setBusy(null);
      }
    },
    [reload],
  );

  return (
    <V4Card id="digest-inbox" className="mt-4">
      <V4CardHeader
        kicker="Approve → Task"
        title="Digest Inbox"
        description="Schválené digesty z lane A/C jedným klikom do Tasks. Tech SCV → Innovation Lab."
        hint={<InlineSectionHintKey hintKey="fourLaneDigestInbox" />}
      />
      {loading && !data ? (
        <div className="flex min-h-20 items-center justify-center gap-2 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading inbox…
        </div>
      ) : null}
      {data ? (
        <p className="mb-3 text-xs text-(--qs-muted)">
          {data.pending_count} čaká na review ·{" "}
          <Link href="/agents#sessions" className="text-cyan underline">
            Všetky sessions →
          </Link>
        </p>
      ) : null}
      {!data?.items.length && !loading ? (
        <p className="text-sm text-(--qs-text-2)">Žiadne nové digesty — lane rutiny bežia podľa cronu.</p>
      ) : null}
      <ul className="space-y-2">
        {(data?.items ?? []).map((item) => (
          <li
            key={item.session_id}
            className="rounded-lg border border-(--qs-border) bg-black/20 p-3"
          >
            <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-(--qs-text)">{item.lane_label}</span>
                  <V4Badge tone={item.promote_ready ? "ok" : "warn"}>{item.session_status}</V4Badge>
                  {item.task_id ? (
                    <V4Badge tone="ok">
                      <CheckCircle2 className="mr-1 inline size-3" aria-hidden />
                      Task
                    </V4Badge>
                  ) : null}
                </div>
                <p className="mt-1 text-xs font-medium text-(--qs-text-2)">{item.title}</p>
                <p className="mt-1 line-clamp-3 text-[11px] leading-relaxed text-(--qs-muted)">{item.excerpt}</p>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                <Link href={item.session_href} className="qs-btn qs-btn--ghost qs-btn--sm gap-1">
                  <ExternalLink className="size-3.5" aria-hidden />
                  Session
                </Link>
                {item.lane_id === "tech_scv" ? (
                  <Link href="/agentic-os#innovation" className="qs-btn qs-btn--primary qs-btn--sm">
                    Innovation
                  </Link>
                ) : item.promote_ready && !item.task_id ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                    disabled={busy === item.session_id}
                    onClick={() => void promote(item)}
                  >
                    {busy === item.session_id ? (
                      <Loader2 className="size-3.5 animate-spin" aria-hidden />
                    ) : (
                      <ListTodo className="size-3.5" aria-hidden />
                    )}
                    → Task
                  </button>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </V4Card>
  );
}

export const FourLaneDigestInboxPanel = memo(FourLaneDigestInboxPanelInner);
