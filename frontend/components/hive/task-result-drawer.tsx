"use client";

import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { HiveApiError, hiveDelete, hiveFetchRaw, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { COCKPIT_POLL_TASK_DRAWER_MS } from "@/lib/cockpit-poll-profile";
import { useDocumentVisible } from "@/lib/hooks/use-document-visible";
import type { TaskLineageResponse, TaskRow, TaskWorkspaceResponse } from "@/lib/hive-types";
import { GoalProgressStrip } from "@/components/hive/goal-progress-strip";
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
  initialEdit?: boolean;
  onMutated?: () => void;
}

function displayStatus(status: string | undefined): string {
  const raw = (status ?? "").toLowerCase();
  if (raw === "pending") return "todo";
  if (raw === "triage") return "triage";
  if (raw === "ready") return "ready";
  if (raw === "blocked") return "blocked";
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
  const visible = useDocumentVisible();

  useEffect(() => {
    const dotInterval = window.setInterval(() => setDots((d) => (d.length >= 3 ? "." : `${d}.`)), 500);
    const eta = window.setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => {
      window.clearInterval(dotInterval);
      window.clearInterval(eta);
    };
  }, []);

  useEffect(() => {
    if (!visible) {
      return undefined;
    }

    let cancelled = false;
    const poll = window.setInterval(() => {
      void (async (): Promise<void> => {
        try {
          const data = await hiveGet<TaskDrawerDetail>(`tasks/${encodeURIComponent(taskId)}`);
          if (cancelled) {
            return;
          }
          onRefresh(data);
          const st = (data.status ?? "").toLowerCase();
          if (st === "completed" || st === "failed") {
            window.clearInterval(poll);
          }
        } catch {
          /* ignore transient poll failures */
        }
      })();
    }, COCKPIT_POLL_TASK_DRAWER_MS);

    return () => {
      cancelled = true;
      window.clearInterval(poll);
    };
  }, [taskId, onRefresh, visible]);

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <div className="text-4xl">🐝</div>
      <div className="font-[family-name:var(--font-poppins)] text-sm text-pollen">Bee is working{dots}</div>
      <div className="font-[family-name:var(--font-poppins)] text-[11px] text-zinc-600">{elapsed}s elapsed</div>
        <div className="h-1 w-48 overflow-hidden rounded-full bg-[#1a1a3e]">
        <div className="h-full w-3/5 animate-pulse rounded-full bg-gradient-to-r from-pollen to-alert" />
      </div>
      <p className="max-w-xs text-center text-xs text-zinc-500">
        Result will appear here automatically when the bee finishes.
      </p>
    </div>
  );
}

export function TaskResultDrawer({
  taskId,
  onClose,
  initialEdit = false,
  onMutated,
}: TaskResultDrawerProps): JSX.Element | null {
  const [task, setTask] = useState<TaskDrawerDetail | null>(null);
  const [lineage, setLineage] = useState<TaskLineageResponse | null>(null);
  const [workspace, setWorkspace] = useState<TaskWorkspaceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);
  const [slideIn, setSlideIn] = useState(false);
  const [noteDraft, setNoteDraft] = useState("");
  const [noteBusy, setNoteBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editTaskText, setEditTaskText] = useState("");
  const [saveBusy, setSaveBusy] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const pollComplete = useCallback((next: TaskDrawerDetail) => setTask(next), []);

  useEffect(() => {
    if (!taskId) {
      setTask(null);
      setLineage(null);
      setWorkspace(null);
      setSlideIn(false);
      return;
    }
    setSlideIn(false);
    setDrawerError(null);
    setLoading(true);
    Promise.all([
      hiveGet<TaskDrawerDetail>(`tasks/${encodeURIComponent(taskId)}`),
      hiveGet<TaskLineageResponse>(`tasks/${encodeURIComponent(taskId)}/lineage`).catch(() => null),
      hiveGet<TaskWorkspaceResponse>(`tasks/${encodeURIComponent(taskId)}/workspace`).catch(() => null),
    ])
      .then(([detail, tree, files]) => {
        setTask(detail);
        setLineage(tree);
        setWorkspace(files);
        setEditTitle(detail.title);
        const text =
          detail.payload && typeof detail.payload.task_text === "string" ? detail.payload.task_text : "";
        setEditTaskText(text);
        setEditing(initialEdit);
        setLoading(false);
        requestAnimationFrame(() => setSlideIn(true));
      })
      .catch((e: unknown) => {
        setLoading(false);
        const msg =
          e instanceof HiveApiError ? `${e.message} (${e.status})` : e instanceof Error ? e.message : "Load failed";
        setDrawerError(msg);
      });
  }, [taskId, initialEdit]);

  function beginEdit(): void {
    if (!task) return;
    setEditTitle(task.title);
    const text =
      task.payload && typeof task.payload.task_text === "string" ? task.payload.task_text : "";
    setEditTaskText(text);
    setEditing(true);
  }

  async function handleSaveEdit(): Promise<void> {
    if (!taskId) return;
    const title = editTitle.trim();
    if (title.length < 2) {
      window.alert("Title must be at least 2 characters.");
      return;
    }
    setSaveBusy(true);
    try {
      const next = await hivePatchJson<TaskDrawerDetail>(`tasks/${encodeURIComponent(taskId)}`, {
        title,
        task_text: editTaskText.trim(),
      });
      setTask(next);
      setEditing(false);
      onMutated?.();
    } catch (e) {
      window.alert(e instanceof HiveApiError ? e.message : "Save failed");
    } finally {
      setSaveBusy(false);
    }
  }

  async function handleDeleteTask(): Promise<void> {
    if (!taskId) return;
    setDeleteOpen(false);
    try {
      await hiveDelete<void>(`tasks/${encodeURIComponent(taskId)}`);
      onMutated?.();
      onClose();
    } catch (e) {
      window.alert(e instanceof HiveApiError ? e.message : "Could not remove task");
    }
  }

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
  const isWorking =
    statusKey === "pending" ||
    statusKey === "running" ||
    statusKey === "ready" ||
    statusKey === "triage";

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

  async function handlePatchStatus(status: string): Promise<void> {
    if (!taskId) return;
    try {
      const next = await hivePatchJson<TaskDrawerDetail>(`tasks/${encodeURIComponent(taskId)}`, { status });
      setTask(next);
      onMutated?.();
      if (status === "completed") {
        const { celebrateVerifiedOutcome } = await import("@/lib/celebrate-verified-outcome");
        await celebrateVerifiedOutcome();
      }
    } catch (e) {
      window.alert(e instanceof HiveApiError ? e.message : "Status update failed");
    }
  }

  async function handleSendNote(): Promise<void> {
    const text = noteDraft.trim();
    if (!taskId || text.length < 1) return;
    setNoteBusy(true);
    try {
      const next = await hivePatchJson<TaskDrawerDetail>(`tasks/${encodeURIComponent(taskId)}`, {
        operator_note: text,
      });
      setTask(next);
      setNoteDraft("");
    } catch (e) {
      window.alert(e instanceof HiveApiError ? e.message : "Could not save note");
    } finally {
      setNoteBusy(false);
    }
  }

  const taskText =
    task?.payload && typeof task.payload.task_text === "string" ? task.payload.task_text : null;
  const operatorNotes = parseOperatorNotes(task?.payload);

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
          "fixed right-0 top-0 z-[125] flex h-full w-full max-w-2xl flex-col border-l border-(--qs-border) bg-(--qs-surface) shadow-2xl transition-transform duration-300 ease-out",
          slideIn ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex items-start justify-between border-b border-[color:var(--qs-border)] p-5">
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full border px-2 py-0.5 qs-chip capitalize ${statusCls}`}
              >
                {badgeStatus}
              </span>
              {outputFmt && outputFmt !== "text" ? (
                <span className="rounded-full border border-data/35 bg-data/10 px-2 py-0.5 qs-chip uppercase text-data">
                  {outputFmt.toUpperCase()}
                </span>
              ) : null}
            </div>
            <h2 className="truncate font-[family-name:var(--font-poppins)] text-base font-semibold text-[#fafafa]">
              {editing ? (
                <input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full rounded-lg border border-[color:var(--qs-border)] bg-black/45 px-2 py-1 text-base text-[#fafafa] focus:border-pollen/35 focus:outline-none"
                />
              ) : (
                (task?.title ?? "Loading...")
              )}
            </h2>
            {task?.created_at ? (
              <p className="mt-0.5 font-[family-name:var(--font-poppins)] text-[11px] text-zinc-600">
                {new Date(task.created_at).toLocaleString()}
              </p>
            ) : null}
          </div>
          <div className="ml-3 flex items-center gap-2">
            {statusKey === "completed" && outputText ? (
              <button
                type="button"
                onClick={() => void handleDownload()}
                className="rounded-lg border border-success/35 px-3 py-1.5 font-[family-name:var(--font-poppins)] text-xs font-semibold text-success transition hover:bg-success/10"
              >
                ⬇ Download
              </button>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-[color:var(--qs-border)] text-lg text-zinc-400 transition hover:border-zinc-500 hover:text-[#fafafa]"
            >
              ×
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 hive-scrollbar">
          {loading ? (
            <p className="animate-pulse font-[family-name:var(--font-poppins)] text-sm text-pollen">
              Loading result…
            </p>
          ) : null}

          {!loading && drawerError ? (
            <p className="font-[family-name:var(--font-poppins)] text-sm text-danger">{drawerError}</p>
          ) : null}

          {!loading && task ? (
            <div className="mb-6 space-y-4">
              {taskText ? (
                <div>
                  <p className="qs-meta-label mb-2 text-zinc-500">Description</p>
                  {editing ? (
                    <textarea
                      value={editTaskText}
                      onChange={(e) => setEditTaskText(e.target.value)}
                      rows={12}
                      className="w-full rounded-xl border border-[color:var(--qs-border)] bg-black/40 p-3 text-xs text-zinc-300 focus:border-pollen/35 focus:outline-none"
                    />
                  ) : (
                    <pre className="whitespace-pre-wrap rounded-xl border border-[color:var(--qs-border)] bg-black/40 p-3 text-xs text-zinc-300">
                      {taskText}
                    </pre>
                  )}
                </div>
              ) : editing ? (
                <div>
                  <p className="qs-meta-label mb-2 text-zinc-500">Description</p>
                  <textarea
                    value={editTaskText}
                    onChange={(e) => setEditTaskText(e.target.value)}
                    rows={8}
                    placeholder="Mission prompt / task description…"
                    className="w-full rounded-xl border border-[color:var(--qs-border)] bg-black/40 p-3 text-xs text-zinc-300 focus:border-pollen/35 focus:outline-none"
                  />
                </div>
              ) : null}
              <GoalProgressStrip progress={lineage?.goal_progress} />
              {lineage?.parent ? (
                <LineageSection title="Parent" rows={[lineage.parent]} onOpen={onClose} />
              ) : null}
              {lineage?.children?.length ? (
                <LineageSection title="Children" rows={lineage.children} onOpen={onClose} />
              ) : null}
              {workspace?.files?.length ? (
                <div>
                  <p className="qs-meta-label mb-2 text-zinc-500">
                    Workspace ({workspace.files.length} file{workspace.files.length === 1 ? "" : "s"})
                  </p>
                  <ul className="space-y-2">
                    {workspace.files.map((file) => (
                      <li
                        key={file.deliverable_id}
                        className="rounded-lg border border-[color:var(--qs-border)] bg-black/35 px-3 py-2 text-sm"
                      >
                        <a
                          href={`/api/proxy/outputs/${encodeURIComponent(file.deliverable_id)}/markdown.md`}
                          className="font-medium text-cyan hover:underline"
                          target="_blank"
                          rel="noreferrer"
                        >
                          {file.title}
                        </a>
                        {file.archive_relpath ? (
                          <p className="mt-1 font-mono text-[10px] text-zinc-600">{file.archive_relpath}</p>
                        ) : null}
                        {file.preview ? (
                          <p className="mt-1 line-clamp-2 text-xs text-zinc-500">{file.preview}</p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <TaskOperatorThread
                notes={operatorNotes}
                draft={noteDraft}
                busy={noteBusy}
                onDraftChange={setNoteDraft}
                onSend={() => void handleSendNote()}
              />
            </div>
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
                      <p className="qs-meta-label mb-2 text-zinc-500">Tools used</p>
                      <div className="flex flex-wrap gap-2">
                        {keys.map((tool) => (
                          <span
                            key={tool}
                            className="rounded-full bg-black/55 px-2 py-0.5 font-[family-name:var(--font-poppins)] text-[11px] text-zinc-400"
                          >
                            ✓ {tool}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null;
                })()
              ) : null}
              <p className="qs-meta-label mb-2 text-zinc-500">Output</p>
              {outputFmt === "markdown" ? (
                <MarkdownPreview content={outputText} />
              ) : outputFmt === "json" ? (
                <pre className="hive-readable-prose whitespace-pre-wrap rounded-xl border border-[color:var(--qs-border)] bg-[#050510] p-4 font-[family-name:var(--font-jetbrains-mono)] text-xs text-data">
                  {outputText}
                </pre>
              ) : outputFmt === "html" ? (
                <div
                  className="max-h-96 overflow-auto rounded-xl border border-white/10 bg-white p-4 text-sm text-black"
                  dangerouslySetInnerHTML={{ __html: outputText }}
                />
              ) : (
                <pre className="hive-readable-prose whitespace-pre-wrap rounded-xl border border-[color:var(--qs-border)] bg-[#050510] p-4 font-[family-name:var(--font-jetbrains-mono)] text-sm text-zinc-200">
                  {outputText}
                </pre>
              )}
              {(outputFmt === "excel" || outputFmt === "csv") ? (
                <div className="mt-3 rounded-lg border border-success/25 bg-success/10 p-3 font-[family-name:var(--font-poppins)] text-xs leading-relaxed text-success">
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
              <p className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-danger">Task failed</p>
              <pre className="mt-2 whitespace-pre-wrap font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-400">
                {typeof showErr === "string" ? showErr : outputText ?? "No error detail returned."}
              </pre>
            </div>
          ) : null}
        </div>
        {!loading && task ? (
          <footer className="border-t border-(--qs-border) bg-(--qs-surface-2) p-4 pr-40 sm:pr-44">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              {statusKey !== "running" ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--danger qs-btn--sm"
                  onClick={() => setDeleteOpen(true)}
                >
                  Remove
                </button>
              ) : null}
              {editing ? (
                <>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={saveBusy}
                    onClick={() => setEditing(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm"
                    disabled={saveBusy}
                    onClick={() => void handleSaveEdit()}
                  >
                    Save
                  </button>
                </>
              ) : (
                <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={beginEdit}>
                  Edit
                </button>
              )}
              {statusKey !== "blocked" && statusKey !== "completed" && !editing ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                  onClick={() => void handlePatchStatus("blocked")}
                >
                  Block
                </button>
              ) : null}
              {statusKey === "blocked" && !editing ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                  onClick={() => void handlePatchStatus("pending")}
                >
                  Unblock
                </button>
              ) : null}
              {statusKey !== "completed" && !editing ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                  onClick={() => void handlePatchStatus("completed")}
                >
                  Complete
                </button>
              ) : null}
              {task.agent_id && !editing ? (
                <button type="button" className="qs-btn qs-btn--cyan qs-btn--sm" onClick={() => void handleRerunAgent()}>
                  Re-run agent
                </button>
              ) : null}
            </div>
          </footer>
        ) : null}
      </div>

      <ConfirmModal
        open={deleteOpen}
        title="Remove task?"
        message="This cancels the task and removes it from Mission Kanban. Running tasks cannot be removed."
        confirmLabel="Remove"
        danger
        onConfirm={() => void handleDeleteTask()}
        onCancel={() => setDeleteOpen(false)}
      />
    </>
  );
}

function LineageSection({
  title,
  rows,
}: {
  title: string;
  rows: TaskRow[];
  onOpen?: () => void;
}): JSX.Element {
  return (
    <div>
      <p className="qs-meta-label mb-2 text-zinc-500">{title}</p>
      <ul className="space-y-2">
        {rows.map((row) => (
          <li
            key={row.id}
            className="rounded-lg border border-[color:var(--qs-border)] bg-black/35 px-3 py-2 text-sm text-zinc-300"
          >
            <span className="text-[#fafafa]">{row.title}</span>
            <span className="ml-2 text-xs uppercase text-zinc-500">{row.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function parseOperatorNotes(payload?: Record<string, unknown>): { text: string; at: string }[] {
  const raw = payload?.operator_notes;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((entry): entry is { text: string; at: string } => {
      return (
        typeof entry === "object" &&
        entry !== null &&
        typeof (entry as { text?: unknown }).text === "string" &&
        typeof (entry as { at?: unknown }).at === "string"
      );
    })
    .slice(-20);
}

function TaskOperatorThread({
  notes,
  draft,
  busy,
  onDraftChange,
  onSend,
}: {
  notes: { text: string; at: string }[];
  draft: string;
  busy: boolean;
  onDraftChange: (value: string) => void;
  onSend: () => void;
}): JSX.Element {
  return (
    <div>
      <p className="qs-meta-label mb-2 text-zinc-500">Task thread</p>
      {notes.length ? (
        <ul className="mb-3 max-h-40 space-y-2 overflow-y-auto hive-scrollbar">
          {notes.map((note, idx) => (
            <li
              key={`${note.at}-${idx}`}
              className="rounded-lg border border-[color:var(--qs-border)] bg-black/35 px-3 py-2 text-xs text-zinc-300"
            >
              <p className="whitespace-pre-wrap text-zinc-200">{note.text}</p>
              <p className="mt-1 text-[10px] text-zinc-600">{new Date(note.at).toLocaleString()}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mb-3 text-xs text-zinc-600">Add context or instructions for this task.</p>
      )}
      <div className="flex gap-2">
        <input
          value={draft}
          onChange={(e) => onDraftChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder="Message this task…"
          className="min-w-0 flex-1 rounded-xl border border-[color:var(--qs-border)] bg-black/45 px-3 py-2 text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
        />
        <button
          type="button"
          disabled={busy || draft.trim().length === 0}
          onClick={onSend}
          className="qs-btn qs-btn--cyan qs-btn--sm shrink-0"
        >
          Send
        </button>
      </div>
    </div>
  );
}
