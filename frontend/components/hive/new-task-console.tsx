"use client";

import Link from "next/link";
import { ChevronLeftIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type {
  OperatorIntakeResponse,
  PreviewDecompositionResponse,
  PreviewWorkflowStep,
  RecipeMatchBrief,
  RecipeMatchConfigPayload,
} from "@/lib/hive-types";
import { taskPrefillForWizardTemplate } from "@/lib/prd-kanban-flow";
import {
  DEFAULT_RECIPE_MATCH_CONFIG,
  formatSimilarityPct,
  isRecipeMatchEligible,
} from "@/lib/recipe-match-utils";
import { HexNumberBadge, LANE_HEX_STROKE } from "@/components/hive/hex-metric-tile";
import { InfoHint } from "@/components/hive/info-hint";
import { V4Card, V4CardHeader, V4Chip, V4PageCanvas } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

const TARGET_LANES = ["scout", "eval", "sim", "action"] as const;
type TargetLane = (typeof TARGET_LANES)[number];

type PriorityLevel = "low" | "normal" | "high";

function intakeTitle(text: string): string {
  const line = text.trim().split("\n")[0] ?? "";
  const t = line.slice(0, 500);
  if (t.length >= 3) {
    return t;
  }
  return "Hive task";
}

function priorityValue(level: PriorityLevel): number {
  if (level === "low") {
    return 3;
  }
  if (level === "high") {
    return 8;
  }
  return 5;
}

function laneTaskType(lane: TargetLane): string {
  const m: Record<TargetLane, string> = {
    scout: "scrape",
    eval: "evaluate",
    sim: "simulate",
    action: "report",
  };
  return m[lane];
}

function roleUi(agentRole: string): { label: string; badgeStroke: string; badgeClass: string } {
  const r = agentRole.toLowerCase();
  if (r === "scraper") {
    return {
      label: "Scout",
      badgeStroke: LANE_HEX_STROKE.scout,
      badgeClass: "border-data/45 text-cyan",
    };
  }
  if (r === "evaluator") {
    return {
      label: "Eval",
      badgeStroke: LANE_HEX_STROKE.eval,
      badgeClass: "border-pollen/50 text-pollen",
    };
  }
  if (r === "simulator") {
    return {
      label: "Sim",
      badgeStroke: LANE_HEX_STROKE.sim,
      badgeClass: "border-alert/50 text-alert",
    };
  }
  return {
    label: "Action",
    badgeStroke: LANE_HEX_STROKE.action,
    badgeClass: "border-success/50 text-success",
  };
}

function laneUi(lane: TargetLane): { label: string; badgeClass: string } {
  const all: Record<TargetLane, { label: string; badgeClass: string }> = {
    scout: { label: "Scout", badgeClass: "border-data/45 text-cyan" },
    eval: { label: "Eval", badgeClass: "border-pollen/50 text-pollen" },
    sim: { label: "Sim", badgeClass: "border-alert/50 text-alert" },
    action: { label: "Action", badgeClass: "border-success/50 text-success" },
  };
  return all[lane];
}

function lanePillActive(lane: TargetLane): string {
  const map: Record<TargetLane, string> = {
    scout: "qs-pill--active-cyan",
    eval: "qs-pill--active-amber",
    sim: "qs-pill--active-magenta",
    action: "qs-pill--active-green",
  };
  return map[lane];
}

function priorityPillActive(p: PriorityLevel): string {
  if (p === "low") return "qs-pill--active-cyan";
  if (p === "normal") return "qs-pill--active-green";
  return "qs-pill--active-amber";
}

function previewConnectorFromRole(prevRole: string, dashedTail: boolean): string {
  if (dashedTail) {
    return "mx-0.5 h-px min-w-[1.25rem] shrink-0 border-t border-dotted border-zinc-600 opacity-80";
  }
  const r = prevRole.toLowerCase();
  if (r === "scraper") {
    return "mx-0.5 h-1 min-w-[1.25rem] shrink-0 rounded-full bg-gradient-to-r from-cyan/90 to-cyan/10";
  }
  if (r === "evaluator") {
    return "mx-0.5 h-1 min-w-[1.25rem] shrink-0 rounded-full bg-gradient-to-r from-pollen/90 to-pollen/15";
  }
  if (r === "simulator") {
    return "mx-0.5 h-1 min-w-[1.25rem] shrink-0 rounded-full bg-gradient-to-r from-alert/90 to-alert/15";
  }
  return "mx-0.5 h-1 min-w-[1.25rem] shrink-0 rounded-full bg-gradient-to-r from-success/90 to-success/15";
}

function PreviewDagStrip({ steps }: { steps: PreviewWorkflowStep[] }) {
  if (steps.length === 0) {
    return null;
  }
  return (
    <div className="mt-6 overflow-x-auto pb-1">
      <p className="qs-meta-label text-(--qs-text-3)">DAG · step preview</p>
      <div className="mt-3 flex min-w-min items-center px-0.5">
        {steps.map((step, i) => {
          const ui = roleUi(step.agent_role);
          const prev = i > 0 ? steps[i - 1] : null;
          const dashedTail = i > 0 && i === steps.length - 1;
          return (
            <Fragment key={`${step.step_order}-${step.agent_role}`}>
              {prev ? <div className={previewConnectorFromRole(prev.agent_role, dashedTail)} aria-hidden /> : null}
              <div className="flex flex-col items-center gap-1.5 px-0.5">
                <HexNumberBadge
                  value={step.step_order}
                  strokeColor={ui.badgeStroke}
                  glowColor={ui.badgeStroke}
                  sizePx={48}
                />
                <span className="qs-chip max-w-[4rem] text-center uppercase text-(--qs-text-3)">
                  {ui.label}
                </span>
              </div>
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}

export function NewTaskConsole() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const wizardTemplate = searchParams.get("template");
  const linkedSwarmId = searchParams.get("swarm_id");
  const [taskText, setTaskText] = useState(
    "Generate a weekly ACKIE crypto digest with sentiment, fact-checks, and trade recommendation.",
  );
  const [targetLane, setTargetLane] = useState<TargetLane>("action");
  const [priority, setPriority] = useState<PriorityLevel>("high");
  const [enrichRecipes, setEnrichRecipes] = useState(true);

  const [preview, setPreview] = useState<PreviewDecompositionResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const [submitBusy, setSubmitBusy] = useState(false);
  const [saveBusy, setSaveBusy] = useState(false);
  const [matchConfig, setMatchConfig] = useState<RecipeMatchConfigPayload>(DEFAULT_RECIPE_MATCH_CONFIG);

  useEffect(() => {
    let cancelled = false;
    void hiveGet<RecipeMatchConfigPayload>("recipes/match-config")
      .then((cfg) => {
        if (!cancelled) setMatchConfig(cfg);
      })
      .catch(() => null);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!wizardTemplate) {
      return;
    }
    const prefill = taskPrefillForWizardTemplate(wizardTemplate);
    if (prefill) {
      setTaskText(prefill);
      setTargetLane("action");
      setPriority("normal");
    }
  }, [wizardTemplate]);

  const runPreview = useCallback(async () => {
    const text = taskText.trim();
    if (text.length < 8) {
      setPreview(null);
      return;
    }
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const body = await hivePostJson<PreviewDecompositionResponse>("operator/preview-decomposition", {
        task_text: text,
        matching_recipe_id: null,
        enrich_from_chroma_recipes: enrichRecipes,
        max_steps: 7,
      });
      setPreview(body);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Preview failed";
      setPreviewError(msg);
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  }, [taskText, enrichRecipes]);

  useEffect(() => {
    const text = taskText.trim();
    if (text.length < 8) {
      setPreview(null);
      setPreviewError(null);
      return;
    }
    const h = window.setTimeout(() => {
      void runPreview();
    }, 850);
    return () => window.clearTimeout(h);
  }, [taskText, enrichRecipes, runPreview]);

  const recipeMatch: RecipeMatchBrief | null = preview?.recipe_match ?? null;
  const displaySteps: PreviewWorkflowStep[] = preview?.steps ?? [];

  async function onSubmit(): Promise<void> {
    const text = taskText.trim();
    if (text.length < 8) {
      toast.error("Task description must be at least 8 characters.");
      return;
    }
    setSubmitBusy(true);
    try {
      const res = await hivePostJson<OperatorIntakeResponse>("operator/intake-task", {
        title: intakeTitle(text),
        task_text: text,
        task_type: laneTaskType(targetLane),
        priority: priorityValue(priority),
        swarm_id: linkedSwarmId && linkedSwarmId.length >= 8 ? linkedSwarmId : null,
        target_lane: targetLane,
        matching_recipe_id: recipeMatch?.postgres_recipe_id ?? null,
        enrich_from_chroma_recipes: enrichRecipes,
        max_steps: 7,
        start_execution: true,
        defer_to_worker: true,
        execution_payload: {},
      });
      toast.success(
        res.kanban_slice_count != null
          ? `Task queued (${res.execution}) · ${res.kanban_slice_count} Kanban slice(s).`
          : `Task queued (${res.execution}).`,
      );
      router.push("/");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Submit failed";
      toast.error(msg);
    } finally {
      setSubmitBusy(false);
    }
  }

  async function onSaveRecipe(): Promise<void> {
    if (!preview || displaySteps.length < 3) {
      toast.error("Generate a step preview first (at least 3 steps).");
      return;
    }
    const text = taskText.trim();
    const slug = intakeTitle(text)
      .slice(0, 80)
      .replace(/[^\w\s-]+/g, "")
      .trim()
      .replace(/\s+/g, "_");
    const name = `recipe_${slug || "untitled"}_${Date.now().toString(36)}`.slice(0, 200);
    setSaveBusy(true);
    try {
      await hivePostJson<{ recipe_id: string }>("operator/recipes/draft", {
        name,
        description: preview.decomposition_rationale.slice(0, 4000),
        topic_tags: [targetLane, "dashboard"],
        task_text: text,
        steps: displaySteps.map((s) => ({
          step_order: s.step_order,
          description: s.description,
          agent_role: s.agent_role,
          guardrails: s.guardrails,
          evaluation_criteria: s.evaluation_criteria,
        })),
        mark_verified: false,
      });
      toast.success("Recipe saved to catalog.");
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 403) {
        toast.error("Saving recipes requires admin scope (dash:recipe_write).");
      } else {
        const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Save failed";
        toast.error(msg);
      }
    } finally {
      setSaveBusy(false);
    }
  }

  return (
    <V4PageCanvas className="v4-new-task-shell max-w-3xl">
      <div className="mb-2 flex items-center gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-(--qs-text)">New task</h1>
        <InfoHint
          title="New task"
          description="Operator intake form: provide a brief and the hive decomposes it into executable lane steps."
          options={["Auto decomposition preview", "Recipe matching", "Submit to execution queue"]}
        />
      </div>
      <p className="mb-4 max-w-xl text-sm text-(--qs-text-3)">
        Describe what you need. The auto workflow breaker splits the brief into atomic steps.
      </p>
      {wizardTemplate === "product-ship" ? (
        <p className="mb-8 max-w-xl rounded-lg border border-cyan/30 bg-cyan/5 px-3 py-2 text-xs text-(--qs-text-2)">
          Product Ship flow: edit the PRD below → submit → Auto Workflow Breaker creates workflow steps → Kanban vertical
          slices land on <Link href="/tasks" className="text-cyan underline">Tasks</Link>.
        </p>
      ) : (
        <div className="mb-8" />
      )}

      <V4Card>
        <V4CardHeader as="h2" title="Task brief" description="Min 8 characters — preview refreshes automatically." />
        <div className="flex items-center gap-2">
          <p className="v4-label-kicker">Task description</p>
          <InfoHint
            title="Task description"
            description="The more specific the brief, the better the decomposition and final outcome."
            options={["Include goal + constraints", "Min 8 characters for preview", "Prefer measurable expected output"]}
          />
        </div>
        <textarea
          value={taskText}
          onChange={(e) => setTaskText(e.target.value)}
          rows={6}
          className="v4-textarea mt-3 min-h-[140px]"
          placeholder="What should the hive run?"
        />

        <div className="mt-5 flex flex-col gap-5 border-t border-(--qs-border) pt-5">
          <div>
            <div className="flex items-center gap-2">
              <p className="v4-label-kicker">Target swarm lane</p>
              <InfoHint
                title="Target swarm lane"
                description="Sets the primary execution lane that gets priority for processing."
                options={["Scout=research", "Eval=analysis", "Sim=validation", "Action=final delivery"]}
              />
            </div>
            <div className="v4-chip-scroll mt-2">
              {TARGET_LANES.map((lane) => {
                const { label } = laneUi(lane);
                return (
                  <V4Chip key={lane} active={targetLane === lane} onClick={() => setTargetLane(lane)}>
                    {label}
                  </V4Chip>
                );
              })}
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <p className="v4-label-kicker">Priority</p>
                <InfoHint
                  title="Priority"
                  description="Maps to a numeric value used by scheduling queues and orchestration."
                  options={["Low=3", "Normal=5", "High=8"]}
                />
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(
                  [
                    ["low", "Low"],
                    ["normal", "Normal"],
                    ["high", "High"],
                  ] as const
                ).map(([key, label]) => (
                  <V4Chip key={key} active={priority === key} onClick={() => setPriority(key)}>
                    {label}
                  </V4Chip>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-2 sm:mt-auto sm:items-start">
              <V4Chip active={enrichRecipes} onClick={() => setEnrichRecipes((v) => !v)} className="w-fit">
                {enrichRecipes ? "✓ " : ""}Chroma · recipe library
              </V4Chip>
              <InfoHint
                title="Recipe library enrichment"
                description="Enables retrieval of similar verified recipe workflows from Chroma."
                options={["Can improve consistency", "May increase planning latency", "Works best with detailed task text"]}
              />
            </div>
          </div>

          {recipeMatch ? (
            <div
              className={cn(
                "flex items-center gap-2 rounded-xl border px-3 py-2",
                isRecipeMatchEligible(recipeMatch.similarity, matchConfig.match_threshold)
                  ? "border-success/35 bg-success/[0.05]"
                  : "border-pollen/35 bg-pollen/[0.05]",
              )}
            >
              <span
                className={isRecipeMatchEligible(recipeMatch.similarity, matchConfig.match_threshold) ? "text-success" : "text-pollen"}
                aria-hidden
              >
                {isRecipeMatchEligible(recipeMatch.similarity, matchConfig.match_threshold) ? "✓" : "~"}
              </span>
              <span className="text-[11px] text-(--qs-text-2)">
                {recipeMatch.name} · {formatSimilarityPct(recipeMatch.similarity)}
                {isRecipeMatchEligible(recipeMatch.similarity, matchConfig.match_threshold)
                  ? " · auto-match"
                  : ` · below ${formatSimilarityPct(matchConfig.match_threshold)} gate`}
              </span>
            </div>
          ) : previewLoading ? (
            <p className="text-xs text-(--qs-text-3)">Matching recipe…</p>
          ) : enrichRecipes ? (
            <p className="text-xs text-(--qs-text-3)">
              No recipe match above {formatSimilarityPct(matchConfig.match_threshold)} imitation gate.
            </p>
          ) : null}
        </div>
      </V4Card>

      <V4Card className="mt-8">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-(--qs-text)">Decomposition preview</h2>
            <InfoHint
              title="Decomposition preview"
              description="Preview of workflow steps proposed by the breaker before submission."
              options={["Validates guardrails", "Shows step count + roles", "Lets you save as recipe"]}
            />
          </div>
          <p className="text-xs text-(--qs-text-3)">
            {previewLoading ? "LLM working…" : "LLM"}
            {displaySteps.length > 0 ? ` · ${displaySteps.length} steps` : previewError ? " · error" : ""}
          </p>
        </div>
        {previewError ? (
          <div className="mt-4 rounded-xl border border-(--qs-border) bg-white/[0.02] p-4">
            <div className="mb-2.5 flex items-center gap-2.5">
              <span className="text-xl" aria-hidden>
                ⚠️
              </span>
              <div className="text-sm font-semibold text-pollen">LLM Preview Unavailable</div>
            </div>
            <div className="mb-3 text-[13px] leading-relaxed text-(--qs-text-2)">
              {previewError.includes("403") ||
              previewError.toLowerCase().includes("credit") ||
              previewError.toLowerCase().includes("license")
                ? "Grok API has no credits. Using Claude as fallback — task will still work."
                : previewError.includes("404") || previewError.toLowerCase().includes("not found")
                  ? "Check Settings → LLM keys and update the model name."
                  : "Preview failed. The task will still be processed when submitted."}
            </div>
            <div className="flex flex-wrap gap-2.5">
              {(previewError.includes("403") || previewError.toLowerCase().includes("credit")) && (
                <a href="https://console.x.ai" target="_blank" rel="noreferrer" className="qs-btn qs-btn--primary qs-btn--sm">
                  Add Grok credits →
                </a>
              )}
              <Link href="/settings/llm-keys" className="qs-btn qs-btn--ghost qs-btn--sm">
                Settings → LLM keys
              </Link>
            </div>
            <p className="mt-2.5 font-mono text-[11px] text-(--qs-text-3)">You can still submit the task — Claude fallback will handle it.</p>
            {previewError.includes("LiteLLM router exhausted") ||
            previewError.includes("credentials for configured models") ||
            previewError.includes("OPENAI_API_KEY") ? (
              <p className="mt-3 text-xs text-(--qs-text-3)">
                If every provider failed, inspect{" "}
                <Link href="/settings/llm-keys" className="font-semibold text-(--qs-cyan) underline-offset-2 hover:text-pollen">
                  LLM keys
                </Link>{" "}
                or WORKFLOW_BREAKER_* in the backend environment.
              </p>
            ) : null}
          </div>
        ) : null}

        <PreviewDagStrip steps={displaySteps} />

        <ul className="mt-6 space-y-4">
          {displaySteps.length === 0 && !previewLoading ? (
            <li className="v4-dream-empty py-8">Enter at least 8 characters — the preview refreshes automatically.</li>
          ) : null}
          {previewLoading && displaySteps.length === 0 ? (
            <li className="rounded-xl border border-(--qs-border) bg-white/[0.02] px-4 py-8 text-center text-sm text-(--qs-text-3)">Loading steps…</li>
          ) : null}
          {displaySteps.map((step) => {
            const ui = roleUi(step.agent_role);
            return (
              <li
                key={`${step.step_order}-${step.description.slice(0, 24)}`}
                className="flex gap-4 rounded-xl border border-(--qs-border) bg-white/[0.02] px-3 py-3 md:px-4"
              >
                <HexNumberBadge
                  value={step.step_order}
                  strokeColor={ui.badgeStroke}
                  glowColor={ui.badgeStroke}
                  sizePx={48}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-(--qs-text)">{step.description}</p>
                  <p className="mt-1 text-xs text-(--qs-text-3)">{step.guardrail_summary}</p>
                </div>
                <span
                  className={cn(
                    "hidden h-fit shrink-0 rounded-full qs-chip uppercase tracking-wide border px-2 py-0.5 sm:inline-flex",
                    ui.badgeClass,
                  )}
                >
                  {ui.label}
                </span>
              </li>
            );
          })}
        </ul>

        <div className="v4-new-task-actions mt-8 flex flex-col items-start gap-4 border-t border-(--qs-border) pt-6 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className="qs-btn qs-btn--ghost shrink-0 gap-1.5">
            <ChevronLeftIcon className="h-4 w-4 shrink-0" aria-hidden />
            Back
          </Link>
          <div className="flex w-full flex-wrap gap-3 sm:w-auto sm:justify-end">
            <button
              type="button"
              disabled={saveBusy || displaySteps.length < 3}
              onClick={() => void onSaveRecipe()}
              className="qs-btn qs-btn--secondary disabled:opacity-40"
            >
              {saveBusy ? "Saving…" : "Save as recipe"}
            </button>
            <InfoHint
              title="Save as recipe"
              description="Saves the current decomposition draft into the recipe catalog for future matching."
              options={["Requires preview with >=3 steps", "Saved as non-verified draft", "Reusable in future tasks"]}
            />
            <button
              type="button"
              disabled={submitBusy || taskText.trim().length < 8}
              onClick={() => void onSubmit()}
              className="qs-btn qs-btn--primary disabled:opacity-40"
            >
              {submitBusy ? "Submitting…" : "Submit"}
            </button>
            <InfoHint
              title="Submit task"
              description="Sends the task to intake pipeline, starts execution, and redirects back to dashboard."
              options={["Queues orchestration", "Uses selected lane/priority", "Includes matched recipe id if available"]}
            />
          </div>
        </div>
      </V4Card>
    </V4PageCanvas>
  );
}
