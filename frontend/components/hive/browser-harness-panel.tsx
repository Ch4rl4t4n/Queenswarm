"use client";

import type { JSX } from "react";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { BrowserAutomationActionRow, BrowserAutomationSessionRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export function BrowserHarnessPanel(): JSX.Element {
  const [createUrl, setCreateUrl] = useState("https://example.com");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actionUrl, setActionUrl] = useState("https://example.com");
  const [selector, setSelector] = useState("body");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const { data: sessions = [], mutate, isLoading } = useSWR<BrowserAutomationSessionRow[]>(
    "hive/browser-sessions",
    () => hiveGet<BrowserAutomationSessionRow[]>("agents/browser-sessions?limit=40"),
    { refreshInterval: 5000 },
  );
  const selected = useMemo(
    () => sessions.find((item) => item.id === selectedId) ?? sessions[0] ?? null,
    [sessions, selectedId],
  );
  useEffect(() => {
    if (!selected && sessions[0]) {
      setSelectedId(sessions[0].id);
      setActionUrl(sessions[0].current_url ?? sessions[0].start_url ?? "https://example.com");
    }
  }, [selected, sessions]);

  const { data: actions = [], mutate: mutateActions } = useSWR<BrowserAutomationActionRow[]>(
    selected ? `hive/browser-actions/${selected.id}` : null,
    () => hiveGet<BrowserAutomationActionRow[]>(`agents/browser-sessions/${selected?.id}/actions?limit=60`),
    { refreshInterval: 3500 },
  );

  async function createSession(): Promise<void> {
    setBusy(true);
    try {
      const row = await hivePostJson<BrowserAutomationSessionRow>("agents/browser-sessions", {
        start_url: createUrl.trim(),
        mode: "headless",
      });
      setSelectedId(row.id);
      setActionUrl(row.current_url ?? row.start_url ?? createUrl);
      await mutate();
      toast.success("Browser session created.");
    } catch (err) {
      const msg = err instanceof HiveApiError ? err.message : err instanceof Error ? err.message : "Create failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function runAction(actionType: "navigate" | "click" | "fill" | "scrape" | "snapshot"): Promise<void> {
    if (!selected) {
      toast.error("Create or select a browser session first.");
      return;
    }
    setBusy(true);
    try {
      const body: Record<string, unknown> = { action_type: actionType };
      if (actionType === "navigate") {
        body.url = actionUrl.trim();
      } else {
        body.selector = selector.trim() || "body";
      }
      if (actionType === "fill") {
        body.text = text;
      }
      await hivePostJson<BrowserAutomationSessionRow>(`agents/browser-sessions/${selected.id}/actions`, body);
      await Promise.all([mutate(), mutateActions()]);
      toast.success(`Browser action ${actionType} executed.`);
    } catch (err) {
      const msg = err instanceof HiveApiError ? err.message : err instanceof Error ? err.message : "Action failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function approvePending(approve: boolean): Promise<void> {
    if (!selected) {
      return;
    }
    setBusy(true);
    try {
      await hivePostJson<BrowserAutomationSessionRow>(`agents/browser-sessions/${selected.id}/approve`, { approve });
      await Promise.all([mutate(), mutateActions()]);
      toast.success(approve ? "Pending action approved." : "Pending action rejected.");
    } catch (err) {
      const msg = err instanceof HiveApiError ? err.message : err instanceof Error ? err.message : "Review failed";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <V4Card>
      <V4CardHeader
        as="h3"
        title="Browser Harness"
        description="Live browser sessions for agent web navigation, form fill, and scraping."
        actions={<V4Badge tone="info">{isLoading ? "loading" : `${sessions.length} sessions`}</V4Badge>}
      />

      <div className="mt-3 grid gap-2 md:grid-cols-[1fr_auto]">
        <input className="qs-input" value={createUrl} onChange={(event) => setCreateUrl(event.target.value)} placeholder="https://example.com" />
        <button type="button" className="qs-btn qs-btn--primary qs-btn--sm disabled:opacity-40" disabled={busy} onClick={() => void createSession()}>
          New browser session
        </button>
      </div>

      {sessions.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {sessions.map((row) => (
            <button
              key={row.id}
              type="button"
              className={cn(
                "qs-btn qs-btn--ghost qs-btn--sm !rounded-lg text-[11px]",
                selected?.id === row.id && "border-(--qs-cyan)/60 bg-(--qs-cyan)/15 text-(--qs-cyan)",
              )}
              onClick={() => {
                setSelectedId(row.id);
                setActionUrl(row.current_url ?? row.start_url ?? createUrl);
              }}
            >
              {row.mode} · {row.status} · {row.actions_used}/{row.max_actions}
            </button>
          ))}
        </div>
      ) : null}

      {selected ? (
        <div className="mt-4 grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-2">
            <div className="grid gap-2 md:grid-cols-[1fr_auto]">
              <input className="qs-input" value={actionUrl} onChange={(event) => setActionUrl(event.target.value)} placeholder="Navigate URL" />
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm disabled:opacity-40" disabled={busy} onClick={() => void runAction("navigate")}>
                Navigate
              </button>
            </div>
            <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
              <input className="qs-input" value={selector} onChange={(event) => setSelector(event.target.value)} placeholder="CSS selector" />
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm disabled:opacity-40" disabled={busy} onClick={() => void runAction("click")}>
                Click
              </button>
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm disabled:opacity-40" disabled={busy} onClick={() => void runAction("scrape")}>
                Scrape
              </button>
            </div>
            <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
              <input className="qs-input" value={text} onChange={(event) => setText(event.target.value)} placeholder="Fill text value" />
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm disabled:opacity-40" disabled={busy} onClick={() => void runAction("fill")}>
                Fill
              </button>
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm disabled:opacity-40" disabled={busy} onClick={() => void runAction("snapshot")}>
                Snapshot
              </button>
            </div>
            {Object.keys(selected.pending_approval_action ?? {}).length > 0 ? (
              <div className="rounded-xl border border-(--qs-gold)/30 bg-(--qs-gold)/10 p-3">
                <p className="text-xs text-(--qs-gold)">Pending critical browser action requires manual approval.</p>
                <div className="mt-2 flex gap-2">
                  <button type="button" className="qs-btn qs-btn--green qs-btn--sm disabled:opacity-40" disabled={busy} onClick={() => void approvePending(true)}>
                    Approve action
                  </button>
                  <button type="button" className="qs-btn qs-btn--danger qs-btn--sm disabled:opacity-40" disabled={busy} onClick={() => void approvePending(false)}>
                    Reject action
                  </button>
                </div>
              </div>
            ) : null}
            <p className="text-xs text-(--qs-text-3)">
              Current URL: <span className="text-(--qs-text)">{selected.current_url ?? "n/a"}</span>
            </p>
          </div>

          <div className="space-y-2">
            <div className="rounded-xl border border-(--qs-border) bg-(--qs-surface-2)/40 p-2">
              {selected.last_screenshot_base64 ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`data:image/jpeg;base64,${selected.last_screenshot_base64}`}
                  alt="Browser live preview"
                  className="h-48 w-full rounded-lg object-cover"
                />
              ) : (
                <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-(--qs-border) text-xs text-(--qs-text-3)">
                  No screenshot yet
                </div>
              )}
            </div>
            <div className="max-h-40 overflow-y-auto rounded-xl border border-(--qs-border) bg-(--qs-surface-2)/30 p-2">
              {actions.length === 0 ? (
                <p className="text-xs text-(--qs-text-3)">No actions logged yet.</p>
              ) : (
                actions.map((row) => (
                  <div key={row.id} className="border-b border-(--qs-border)/70 py-1 text-xs text-(--qs-text-3) last:border-b-0">
                    <span className="text-(--qs-text)">{row.action_type}</span> · {row.status}
                    {row.result_summary ? <span className="text-(--qs-text-3)"> · {row.result_summary}</span> : null}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      ) : (
        <p className="mt-3 text-xs text-(--qs-text-3)">Create a session to start browser automation.</p>
      )}
    </V4Card>
  );
}
