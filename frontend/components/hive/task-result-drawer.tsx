"use client";

import { HiveApiError, hiveFetchRaw, hiveGet, hivePostJson } from "@/lib/api";
import type { TaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";
import { useCallback, useEffect, useState } from "react";

interface TaskDrawerDetail extends TaskRow {
  output_format?: string | null;
  error_msg?: string | null;
  completed_at?: string | null;
}

interface TaskResultDrawerProps {
  taskId: string | null;
  onClose: () => void;
}

function displayStatus(status: string | undefined): string {
  const raw = (status ?? "").toLowerCase();
  if (raw === "pending") return "queued";
  return raw || "loading";
}

function normalizeOutput(result: unknown): string {
  if (typeof result === "string") return result;
  const r = result as Record<string, unknown> | undefined | null;
  if (!r || typeof r !== "object") return "";

  const out = r.output ?? r.content ?? r.text;
  if (typeof out === "string") return out;
  if (out !== undefined && out !== null) {
    return JSON.stringify(out, null, 2);
  }
  return JSON.stringify(r, null, 2);
}

function MarkdownPreview({ content }: { content: string }): JSX.Element {
  try {
    const escaped = content
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
    const html = escaped
      .replace(/^### (.+)$/gm, '<h3 class="text-[#FFB800] text-sm font-semibold mt-4 mb-1">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 class="text-[#FFB800] text-base font-bold mt-5 mb-1">$1</h2>')
      .replace(/^# (.+)$/gm, '<h2 class="text-[#FFB800] text-xl font-bold mt-6 mb-2">$1</h2>')
      .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
      .replace(/\*(.+?)\*/g, '<em class="text-zinc-300">$1</em>')
      .replace(/`(.+?)`/g, '<code class="bg-[#1a1a3e] text-data px-1 rounded text-[0.85em]">$1</code>')
      .replace(/^- (.+)$/gm, '<li class="my-1 text-zinc-300">$1</li>')
      .replace(/^(\d+)\. (.+)$/gm, '<li class="my-1 text-zinc-300"><span class="text-pollen">$1.</span> $2</li>')
      .replaceAll(/\n\n/g, "<br><br>")
      .replaceAll(/\n/g, "<br>");
    return (
      <div className="text-sm leading-relaxed text-gray-200" dangerouslySetInnerHTML={{ __html: html }} />
    );
  } catch {
    return <pre className="whitespace-pre-wrap text-xs font-mono text-gray-200">{content}</pre>;
  }
}

function LiveStatusPoller({
  taskId,
  onRefresh,
}: {
  taskId: string;
  onRefresh: (t: TaskDrawerDetail) => void;
}): JSX.Element {
  const [dots, setDots] = useState(".");
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const dotInterval = window.setInterval(() => setDots((d) => (d.length >= 3 ? "." : `${d}.`)), 500);
    const eta = window.setInterval(() => setElapsed((e) => e + 1), 1000);
    const poll = window.setInterval(() => {
      void (async (): Promise<void> => {
        try {
          const data = await hiveGet<TaskDrawerDetail>(`tasks/${encodeURIComponent(taskId)}`);
          onRefresh(data);
          const st = (data.status ?? "").toLowerCase();
          if (st === "completed" || st === "failed") {
            window.clearInterval(poll);
            window.clearInterval(dotInterval);
            window.clearInterval(eta);
          }
        } catch {
          /* ignore transient poll failures */
        }
      })();
    }, 3000);
    return () => {
      window.clearInterval(poll);
      window.clearInterval(dotInterval);
      window.clearInterval(eta);
    };
  }, [taskId, onRefresh]);

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <div className="text-4xl">🐝</div>
      <div className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-pollen">Bee is working{dots}</div>
      <div className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-600">{elapsed}s elapsed</div>
        <div className="h-1 w-48 overflow-hidden rounded-full bg-[#1a1a3e]">
        <div className="h-full w-3/5 animate-pulse rounded-full bg-gradient-to-r from-pollen to-alert" />
      </div>
      <p className="max-w-xs text-center text-xs text-zinc-500">
        Result will appear here automatically when the bee finishes.
      </p>
    </div>
  );
}

export function TaskResultDrawer({ taskId, onClose }: TaskResultDrawerProps): JSX.Element | null {
  const [task, setTask] = useState<TaskDrawerDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);
  const [slideIn, setSlideIn] = useState(false);
  const pollComplete = useCallback((next: TaskDrawerDetail) => setTask(next), []);

  useEffect(() => {
    if (!taskId) {
      setTask(null);
      setSlideIn(false);
      return;
    }
    setSlideIn(false);
    setDrawerError(null);
    setLoading(true);
    hiveGet<TaskDrawerDetail>(`tasks/${encodeURIComponent(taskId)}`)
      .then((d) => {
        setTask(d);
        setLoading(false);
        requestAnimationFrame(() => setSlideIn(true));
      })
      .catch((e: unknown) => {
        setLoading(false);
        const msg =
          e instanceof HiveApiError ? `${e.message} (${e.status})` : e instanceof Error ? e.message : "Load failed";
        setDrawerError(msg);
      });
  }, [taskId]);

  if (!taskId) {
    return null;
  }

  const showErr = drawerError ?? (task?.error_msg as string | undefined);
  const result = task?.result ?? null;
  const outputFmt =
    typeof task?.output_format === "string"
      ? task.output_format.toLowerCase()
      : typeof (result as Record<string, unknown> | undefined)?.format === "string"
        ? String((result as { format?: string }).format).toLowerCase()
        : "text";
  const outputText = normalizeOutput(result);

  const statusKey = (task?.status ?? "").toLowerCase();
  const isWorking = statusKey === "pending" || statusKey === "running";

  async function handleDownload(): Promise<void> {
    if (!taskId) return;
    const extMap: Record<string, string> = {
      excel: "xlsx",
      csv: "csv",
      json: "json",
      html: "html",
      markdown: "md",
      text: "txt",
    };
    const extension = extMap[outputFmt] ?? "txt";

    try {
      const res = await hiveFetchRaw(`tasks/${encodeURIComponent(taskId)}/download`);
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const titlePart = task?.title ? task.title.replaceAll(/\s+/g, "_") : "output";
        a.href = url;
        a.download = `${titlePart}.${extension}`;
        a.click();
        URL.revokeObjectURL(url);
        return;
      }
      const mime =
        outputFmt === "excel"
          ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          : outputFmt === "csv"
            ? "text/csv"
            : outputFmt === "json"
              ? "application/json"
              : outputFmt === "html"
                ? "text/html"
                : outputFmt === "markdown"
                  ? "text/markdown"
                  : "text/plain";
      const blob = new Blob([outputText], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `output.${extension}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      const blob = new Blob([outputText], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `output.${extension}`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }

  async function handleRerunAgent(): Promise<void> {
    const aid = task?.agent_id;
    if (!aid) {
      return;
    }
    try {
      await hivePostJson<{ task_id?: string }>(`agents/${encodeURIComponent(aid)}/run`, {});
      if (taskId) {
        const next = await hiveGet<TaskDrawerDetail>(`tasks/${encodeURIComponent(taskId)}`);
        setTask(next);
      }
    } catch (e) {
      window.alert(e instanceof HiveApiError ? e.message : "Re-run failed");
    }
  }

  const badgeStatus = displayStatus(task?.status);
  const statusColor: Record<string, string> = {
    queued: "text-pollen border-pollen/30 bg-pollen/10",
    pending: "text-pollen border-pollen/30 bg-pollen/10",
    running: "text-data border-data/30 bg-data/10",
    completed: "text-success border-success/30 bg-success/10",
    failed: "text-danger border-danger/30 bg-danger/10",
  };
  const statusCls = statusColor[badgeStatus] ?? statusColor.queued ?? statusColor.pending;

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 bg-black/60 cursor-default"
        aria-label="Close task drawer backdrop"
        onClick={onClose}
      />

      <div
        className={cn(
          "fixed right-0 top-0 z-50 flex h-full w-full max-w-2xl flex-col border-l border-[var(--qs-border)] bg-[var(--qs-surface)] shadow-2xl transition-transform duration-300 ease-out",
          slideIn ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex items-start justify-between border-b border-cyan/[0.12] p-5">
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full border px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-xs ${statusCls}`}
              >
                {badgeStatus}
              </span>
              {outputFmt && outputFmt !== "text" ? (
                <span className="rounded-full border border-data/35 bg-data/10 px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-xs text-data">
                  {outputFmt.toUpperCase()}
                </span>
              ) : null}
            </div>
            <h2 className="truncate font-[family-name:var(--font-poppins)] text-base font-semibold text-[#fafafa]">
              {task?.title ?? "Loading..."}
            </h2>
            {task?.created_at ? (
              <p className="mt-0.5 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-600">
                {new Date(task.created_at).toLocaleString()}
              </p>
            ) : null}
          </div>
          <div className="ml-3 flex items-center gap-2">
            {statusKey === "completed" && outputText ? (
              <button
                type="button"
                onClick={() => void handleDownload()}
                className="rounded-lg border border-success/35 px-3 py-1.5 font-[family-name:var(--font-jetbrains-mono)] text-xs text-success transition hover:bg-success/10"
              >
                ⬇ Download
              </button>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan/[0.12] text-lg text-zinc-400 transition hover:border-zinc-500 hover:text-[#fafafa]"
            >
              ×
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 hive-scrollbar">
          {loading ? (
            <p className="animate-pulse font-[family-name:var(--font-jetbrains-mono)] text-sm text-pollen">
              Loading result…
            </p>
          ) : null}

          {!loading && drawerError ? (
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger">{drawerError}</p>
          ) : null}

          {!loading && task && isWorking ? (
            <LiveStatusPoller taskId={taskId} onRefresh={pollComplete} />
          ) : null}

          {!loading && task?.status?.toLowerCase() === "completed" && outputText ? (
            <div>
              {result && typeof result === "object" && "tool_results" in result ? (
                (() => {
                  const tr = (result as { tool_results?: Record<string, unknown> }).tool_results;
                  const keys =
                    typeof tr === "object" && tr !== null
                      ? Object.keys(tr).filter((k): boolean => !!k.length)
                      : [];
                  return keys.length > 0 ? (
                    <div className="mb-4">
                      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Tools used</p>
                      <div className="flex flex-wrap gap-2">
                        {keys.map((tool) => (
                          <span
                            key={tool}
                            className="rounded-full bg-black/55 px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-400"
                          >
                            ✓ {tool}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null;
                })()
              ) : null}
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Output</p>
              {outputFmt === "markdown" ? (
                <MarkdownPreview content={outputText} />
              ) : outputFmt === "json" ? (
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-xl border border-cyan/[0.12] bg-[#050510] p-4 font-[family-name:var(--font-jetbrains-mono)] text-xs text-data">
                  {outputText}
                </pre>
              ) : outputFmt === "html" ? (
                <div
                  className="max-h-96 overflow-auto rounded-xl border border-white/10 bg-white p-4 text-sm text-black"
                  dangerouslySetInnerHTML={{ __html: outputText }}
                />
              ) : (
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-xl border border-cyan/[0.12] bg-[#050510] p-4 font-[family-name:var(--font-jetbrains-mono)] text-sm text-zinc-200">
                  {outputText}
                </pre>
              )}
              {(outputFmt === "excel" || outputFmt === "csv") ? (
                <div className="mt-3 rounded-lg border border-success/25 bg-success/10 p-3 font-[family-name:var(--font-jetbrains-mono)] text-xs text-success">
                  📊{" "}
                  {outputFmt === "excel"
                    ? "Excel document — tap Download above for the generated sheet."
                    : "CSV data — tap Download above for raw bytes."}
                </div>
              ) : null}
            </div>
          ) : null}

          {!loading && task?.status?.toLowerCase() === "failed" ? (
            <div className="rounded-xl border border-danger/30 bg-danger/10 p-4">
              <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger">Task failed</p>
              <pre className="mt-2 whitespace-pre-wrap font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-400">
                {typeof showErr === "string" ? showErr : outputText ?? "No error detail returned."}
              </pre>
            </div>
          ) : null}
        </div>
        {!loading && task?.agent_id ? (
          <footer className="flex justify-end gap-2 border-t border-[var(--qs-border)] bg-[var(--qs-surface-2)] p-4">
            <button type="button" className="qs-btn qs-btn--cyan qs-btn--sm" onClick={() => void handleRerunAgent()}>
              Re-run agent
            </button>
          </footer>
        ) : null}
      </div>
    </>
  );
}
