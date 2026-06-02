"use client";

import Link from "next/link";
import { CalendarClock, Copy, Loader2Icon } from "lucide-react";
import { useCallback, useId, useState, type JSX } from "react";
import { toast } from "sonner";

import { HiveModalShell } from "@/components/hive/hive-modal-shell";
import { InlineSectionHintKey } from "@/components/hive/inline-section-hint";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type { RecipeRoutineCreateBody, RecipeRoutineCreateResponse } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

const SCHEDULE_KIND_OPTIONS = [
  { value: "cron", label: "Cron (daily at fixed time)" },
  { value: "interval", label: "Interval (every N seconds)" },
  { value: "event", label: "Event (webhook only)" },
] as const;

const INTERVAL_PRESETS = [
  { label: "1 hour", seconds: 3600 },
  { label: "6 hours", seconds: 21_600 },
  { label: "12 hours", seconds: 43_200 },
  { label: "24 hours", seconds: 86_400 },
] as const;

type ScheduleKind = (typeof SCHEDULE_KIND_OPTIONS)[number]["value"];

interface RecipeScheduleRoutineDialogProps {
  recipeId: string;
  recipeName: string;
  open: boolean;
  onClose: () => void;
}

/** L3 Automation Ladder — schedule verified recipe as supervisor routine (optional L4 webhook). */
export function RecipeScheduleRoutineDialog({
  recipeId,
  recipeName,
  open,
  onClose,
}: RecipeScheduleRoutineDialogProps): JSX.Element {
  const titleId = useId();
  const descId = useId();
  const [busy, setBusy] = useState(false);
  const [scheduleKind, setScheduleKind] = useState<ScheduleKind>("cron");
  const [cronExpr, setCronExpr] = useState("0 9 * * *");
  const [intervalSeconds, setIntervalSeconds] = useState(86_400);
  const [enableWebhook, setEnableWebhook] = useState(false);
  const [result, setResult] = useState<RecipeRoutineCreateResponse | null>(null);

  const resetForm = useCallback(() => {
    setScheduleKind("cron");
    setCronExpr("0 9 * * *");
    setIntervalSeconds(86_400);
    setEnableWebhook(false);
    setResult(null);
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onClose();
  }, [onClose, resetForm]);

  async function submit(): Promise<void> {
    setBusy(true);
    try {
      const body: RecipeRoutineCreateBody = {
        name: recipeName.slice(0, 160),
        schedule_kind: scheduleKind,
        runtime_mode: "durable",
        enable_webhook: enableWebhook || scheduleKind === "event",
      };
      if (scheduleKind === "cron") {
        body.cron_expr = cronExpr.trim() || "0 9 * * *";
      }
      if (scheduleKind === "interval") {
        body.interval_seconds = intervalSeconds;
      }
      const res = await hivePostJson<RecipeRoutineCreateResponse>(
        `recipes/${encodeURIComponent(recipeId)}/routine`,
        body,
      );
      setResult(res);
      toast.success(`Routine scheduled: ${res.routine_name}`);
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Could not schedule routine.");
    } finally {
      setBusy(false);
    }
  }

  async function copyToken(token: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(token);
      toast.message("Webhook token copied");
    } catch {
      toast.error("Clipboard unavailable");
    }
  }

  return (
    <HiveModalShell
      open={open}
      onClose={handleClose}
      labelledBy={titleId}
      describedBy={descId}
      panelClassName="qs-bubble flex w-full max-w-lg flex-col gap-5 p-5 sm:p-6"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id={titleId} className="text-lg font-semibold text-(--qs-text)">
            Schedule as routine
          </h2>
          <p id={descId} className="mt-1 text-sm text-(--qs-text-3)">
            Automation Ladder L3 — cloud cron from verified recipe{" "}
            <span className="text-pollen">{recipeName}</span>.
          </p>
        </div>
        <InlineSectionHintKey hintKey="knowledgeRecipes" />
      </div>

      {result ? (
        <div className="space-y-4 rounded-xl border border-(--qs-cyan)/25 bg-(--qs-cyan)/5 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <V4Badge tone="ok">Routine created</V4Badge>
            <V4Badge tone="info">{result.schedule_kind}</V4Badge>
          </div>
          <p className="text-sm text-(--qs-text)">
            <span className="v4-field-label">Name</span> — {result.routine_name}
          </p>
          <p className="text-xs font-mono text-(--qs-text-3)">ID {result.routine_id}</p>
          {result.roles.length ? (
            <p className="text-xs text-(--qs-text-3)">Roles: {result.roles.join(", ")}</p>
          ) : null}
          {result.webhook_url && result.webhook_token ? (
            <div className="space-y-2 rounded-lg border border-pollen/30 bg-pollen/5 p-3">
              <p className="text-xs font-medium text-pollen">L4 webhook — copy token now (shown once)</p>
              <p className="break-all font-mono text-[11px] text-(--qs-text-2)">{result.webhook_url}</p>
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                onClick={() => void copyToken(result.webhook_token ?? "")}
              >
                <Copy className="h-3.5 w-3.5" aria-hidden />
                Copy token
              </button>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2 pt-1">
            <Link href="/agents#sessions" className="qs-btn qs-btn--primary qs-btn--sm">
              Open Agents → routines
            </Link>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={handleClose}>
              Close
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            <label className="block space-y-1.5">
              <span className="v4-field-label">Schedule kind</span>
              <QsSelect
                value={scheduleKind}
                onValueChange={(next) => setScheduleKind(next as ScheduleKind)}
                options={SCHEDULE_KIND_OPTIONS.map((row) => ({ value: row.value, label: row.label }))}
              />
            </label>

            {scheduleKind === "cron" ? (
              <label className="block space-y-1.5">
                <span className="v4-field-label">Cron expression</span>
                <input
                  type="text"
                  value={cronExpr}
                  onChange={(e) => setCronExpr(e.target.value)}
                  placeholder="0 9 * * *"
                  className="qs-input w-full font-mono text-sm"
                />
                <p className="text-xs text-(--qs-text-3)">Default: daily at 09:00 UTC.</p>
              </label>
            ) : null}

            {scheduleKind === "interval" ? (
              <label className="block space-y-1.5">
                <span className="v4-field-label">Interval</span>
                <QsSelect
                  value={String(intervalSeconds)}
                  onValueChange={(next) => setIntervalSeconds(Number(next))}
                  options={INTERVAL_PRESETS.map((row) => ({
                    value: String(row.seconds),
                    label: row.label,
                  }))}
                />
              </label>
            ) : null}

            {scheduleKind !== "event" ? (
              <label className="flex items-start gap-3 text-sm text-(--qs-text-2)">
                <input
                  type="checkbox"
                  checked={enableWebhook}
                  onChange={(e) => setEnableWebhook(e.target.checked)}
                  className="mt-1"
                />
                <span>
                  Also enable L4 webhook ingress (Make/n8n middleware can trigger between cron runs).
                </span>
              </label>
            ) : (
              <p className="rounded-lg border border-(--qs-magenta)/30 bg-(--qs-magenta)/5 px-3 py-2 text-xs text-(--qs-text-2)">
                Event schedule runs only when an external webhook POST arrives — configure Make/n8n after
                creation.
              </p>
            )}
          </div>

          <div className="flex flex-wrap justify-end gap-2 border-t border-(--qs-border)/40 pt-4">
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={handleClose}>
              Cancel
            </button>
            <button
              type="button"
              className={cn("qs-btn qs-btn--primary qs-btn--sm", busy && "opacity-70")}
              disabled={busy}
              onClick={() => void submit()}
            >
              {busy ? (
                <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <CalendarClock className="h-4 w-4" aria-hidden />
              )}
              Schedule routine
            </button>
          </div>
        </>
      )}
    </HiveModalShell>
  );
}
