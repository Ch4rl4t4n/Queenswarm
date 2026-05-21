"use client";

import { ClipboardCopyIcon, Loader2Icon, SparklesIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { QsSelect } from "@/components/ui/qs-select";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { HarnessSnapshotPayload, RubricEvaluateResponse, RubricTemplateRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface RubricTemplatesPanelProps {
  snapshot: HarnessSnapshotPayload;
}

/** Subjective scoring rubrics for design, copy, and product output (harness tester). */
export function RubricTemplatesPanel({ snapshot }: RubricTemplatesPanelProps): JSX.Element | null {
  const rubricMeta = snapshot.rubric_templates;
  const [templates, setTemplates] = useState<RubricTemplateRow[]>([]);
  const [templateId, setTemplateId] = useState("design-ux");
  const [sampleText, setSampleText] = useState(
    "Launch Queenswarm Product Ship — PRD to Kanban slices with verified simulation gates.",
  );
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<RubricEvaluateResponse | null>(null);

  const loadTemplates = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const rows = await hiveGet<RubricTemplateRow[]>("harness/rubric-templates");
      setTemplates(rows);
      if (rows.length > 0 && !rows.some((row) => row.id === templateId)) {
        setTemplateId(rows[0].id);
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Failed to load rubric templates.");
    } finally {
      setLoading(false);
    }
  }, [templateId]);

  useEffect(() => {
    if (rubricMeta?.enabled) {
      void loadTemplates();
    } else {
      setLoading(false);
    }
  }, [loadTemplates, rubricMeta?.enabled]);

  const selected = templates.find((row) => row.id === templateId) ?? null;

  async function evaluateSample(): Promise<void> {
    const text = sampleText.trim();
    if (text.length < 8) {
      toast.error("Sample text must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      const body = await hivePostJson<RubricEvaluateResponse>("harness/rubric-templates/evaluate", {
        template_id: templateId,
        text,
      });
      setResult(body);
      toast.success(body.is_valid ? "Rubric pass" : "Rubric needs revision");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Rubric evaluation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function copyCriteria(): Promise<void> {
    if (!selected) {
      return;
    }
    try {
      const body = await hivePostJson<{ evaluation_criteria: Record<string, unknown> }>(
        "harness/rubric-templates/apply",
        { template_id: templateId, base_criteria: {} },
      );
      await navigator.clipboard.writeText(JSON.stringify(body.evaluation_criteria, null, 2));
      toast.success("evaluation_criteria copied to clipboard");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Copy failed.");
    }
  }

  if (!rubricMeta?.enabled) {
    return (
      <V4Card>
        <V4CardHeader
          kicker="Rubrics"
          title="Subjective scoring templates"
          description="Rubric templates are disabled via RUBRIC_TEMPLATES_ENABLED."
        />
      </V4Card>
    );
  }

  return (
    <V4Card>
      <V4CardHeader
        kicker="Rubrics"
        title="Subjective output scoring"
        description="Curated evaluation_criteria for design, copy, PRD, code review, and a11y — generator-evaluator gate."
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <V4Badge tone="ok">{rubricMeta.count} templates</V4Badge>
        {selected ? (
          <V4Badge tone="info">Pass ≥ {(selected.pass_threshold * 100).toFixed(0)}%</V4Badge>
        ) : null}
      </div>

      {loading ? (
        <p className="mt-3 flex items-center gap-2 text-sm text-(--qs-muted)">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Loading rubrics…
        </p>
      ) : (
        <>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <label className="block text-xs text-(--qs-muted)">
              Template
              <QsSelect
                className="mt-1 w-full"
                value={templateId}
                onValueChange={setTemplateId}
                options={templates.map((row) => ({
                  value: row.id,
                  label: `${row.name} (${row.category})`,
                }))}
                aria-label="Rubric template"
              />
            </label>
            <div className="flex items-end gap-2">
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-1" onClick={() => void copyCriteria()}>
                <ClipboardCopyIcon className="size-3.5" aria-hidden />
                Copy criteria JSON
              </button>
            </div>
          </div>

          {selected ? (
            <p className="mt-3 text-sm text-(--qs-text-2)">{selected.description}</p>
          ) : null}

          <label className="mt-4 block text-xs text-(--qs-muted)">
            Sample output to score
            <textarea
              className="mt-1 min-h-24 w-full rounded-lg border border-(--qs-border) bg-black/30 px-3 py-2 text-sm text-(--qs-text)"
              value={sampleText}
              onChange={(event) => setSampleText(event.target.value)}
            />
          </label>

          <button
            type="button"
            className={cn("qs-btn qs-btn--ghost qs-btn--sm mt-3 gap-1.5", busy && "opacity-60")}
            disabled={busy}
            onClick={() => void evaluateSample()}
          >
            {busy ? (
              <Loader2Icon className="size-4 animate-spin" aria-hidden />
            ) : (
              <SparklesIcon className="size-4" aria-hidden />
            )}
            Evaluate with rubric
          </button>

          {result ? (
            <div className="mt-4 rounded-lg border border-(--qs-border) bg-black/25 p-3 text-sm">
              <div className="flex flex-wrap gap-2">
                <V4Badge tone={result.is_valid ? "ok" : "warn"}>
                  {result.is_valid ? "pass" : "needs work"}
                </V4Badge>
                {typeof result.confidence === "number" ? (
                  <V4Badge tone="info">{(result.confidence * 100).toFixed(0)}% confidence</V4Badge>
                ) : null}
              </div>
              {result.feedback ? <p className="mt-2 text-(--qs-text)">{result.feedback}</p> : null}
            </div>
          ) : null}
        </>
      )}
    </V4Card>
  );
}
