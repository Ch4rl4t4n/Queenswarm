"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { DataMonitorPlanPayload, DataMonitorWizardPayload } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface DataMonitorWizardPanelProps {
  canManage: boolean;
  onCreated: () => Promise<void>;
}

const SCHEDULE_OPTIONS = [
  { value: "6h", label: "Every 6 hours" },
  { value: "12h", label: "Every 12 hours" },
  { value: "24h", label: "Every 24 hours" },
  { value: "daily_6utc", label: "Daily · 06:00 UTC" },
] as const;

/** DG1 — One-line intent → scheduled forager + extract schema. */
export function DataMonitorWizardPanel({
  canManage,
  onCreated,
}: DataMonitorWizardPanelProps): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<DataMonitorWizardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [intent, setIntent] = useState("");
  const [schedulePreset, setSchedulePreset] = useState("24h");
  const [plan, setPlan] = useState<DataMonitorPlanPayload | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<DataMonitorWizardPayload>("foragers/data-monitor-wizard");
      setSnapshot(data);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const preview = useCallback(async () => {
    const trimmed = intent.trim();
    if (trimmed.length < 12) {
      setPlan(null);
      return;
    }
    setPreviewing(true);
    try {
      const data = await hivePostJson<DataMonitorPlanPayload>("foragers/data-monitor-wizard/preview", {
        intent: trimmed,
        schedule_preset: schedulePreset,
        trigger_first_run: true,
      });
      setPlan(data);
    } catch (e) {
      setPlan(null);
      toast.error(e instanceof HiveApiError ? e.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  }, [intent, schedulePreset]);

  useEffect(() => {
    const timer = window.setTimeout(() => void preview(), 450);
    return () => window.clearTimeout(timer);
  }, [preview]);

  const submit = useCallback(async () => {
    const trimmed = intent.trim();
    if (trimmed.length < 12) return;
    setSubmitting(true);
    try {
      const data = await hivePostJson<{
        ok: boolean;
        forager_name: string;
        message: string;
        schedule_label: string;
      }>("foragers/data-monitor-wizard/submit", {
        intent: trimmed,
        schedule_preset: schedulePreset,
        trigger_first_run: true,
      });
      toast.success(data.message || `${data.forager_name} created · ${data.schedule_label}`);
      setIntent("");
      setPlan(null);
      await onCreated();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Create monitor failed");
    } finally {
      setSubmitting(false);
    }
  }, [intent, onCreated, schedulePreset]);

  if (loading && !snapshot) {
    return (
      <V4Card className="border-cyan/20 bg-cyan/5">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading Data Monitor wizard…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <div data-testid="data-monitor-wizard-panel">
      <V4Card className="border-cyan/20 bg-cyan/5">
        <V4CardHeader
          title="Data Monitor wizard"
          description="DG1 — describe what to track in one sentence; we spawn a scheduled forager with schema."
        />
        <div className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-(--qs-text-2)">Monitor intent</span>
            <textarea
              className="qs-input min-h-[88px] resize-y"
              placeholder="e.g. Track senior Python remote jobs in EU on public job boards"
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              disabled={!canManage}
            />
          </label>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex min-w-[180px] flex-col gap-1.5">
              <span className="text-xs font-medium text-(--qs-text-2)">Schedule</span>
              <QsSelect
                value={schedulePreset}
                onValueChange={setSchedulePreset}
                options={SCHEDULE_OPTIONS.map((opt) => ({ value: opt.value, label: opt.label }))}
                disabled={!canManage}
              />
            </label>
            <button
              type="button"
              className={cn("qs-btn qs-btn--primary qs-btn--sm gap-2")}
              disabled={!canManage || submitting || intent.trim().length < 12}
              onClick={() => void submit()}
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Sparkles className="h-4 w-4" aria-hidden />
              )}
              Create monitor
            </button>
          </div>
          {snapshot.examples.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {snapshot.examples.slice(0, 4).map((example) => (
                <button
                  key={example.intent}
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--xs text-left"
                  disabled={!canManage}
                  onClick={() => setIntent(example.intent)}
                >
                  {example.label}
                </button>
              ))}
            </div>
          ) : null}
          {previewing ? (
            <div className="flex items-center gap-2 text-xs text-(--qs-text-3)">
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
              Deriving plan…
            </div>
          ) : null}
          {plan ? (
            <div className="rounded-lg border border-white/10 bg-black/20 p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <V4Badge tone="info">{plan.niche_label}</V4Badge>
                <V4Badge tone="purple">{plan.source_type}</V4Badge>
                <V4Badge tone="ok">{plan.schedule_label}</V4Badge>
                <span className="text-(--qs-text-3)">schema: {plan.extract_schema}</span>
              </div>
              <p className="mt-2 font-medium text-(--qs-text-1)">{plan.forager_name}</p>
              <p className="mt-1 text-xs text-(--qs-text-3)">{plan.source_config_summary}</p>
              {plan.skill_bundle.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {plan.skill_bundle.map((slug) => (
                    <span
                      key={slug}
                      className="inline-flex rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-(family-name:--font-jetbrains-mono) text-[10px] text-emerald-200"
                    >
                      {slug}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </V4Card>
    </div>
  );
}
