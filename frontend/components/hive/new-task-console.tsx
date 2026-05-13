"use client";

import Link from "next/link";
import { ChevronLeftIcon, PlayIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveApiError, hivePostJson } from "@/lib/api";
import type {
  OperatorIntakeResponse,
  PreviewDecompositionResponse,
  PreviewWorkflowStep,
  RecipeMatchBrief,
} from "@/lib/hive-types";
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

function roleUi(agentRole: string): { label: string; hexClass: string; badgeClass: string } {
  const r = agentRole.toLowerCase();
  if (r === "scraper") {
    return {
      label: "Scout",
      hexClass: "border-cyan/70 bg-cyan/[0.08] text-cyan shadow-[0_0_14px_rgb(0_255_255/0.25)]",
      badgeClass: "border-cyan/45 text-cyan",
    };
  }
  if (r === "evaluator") {
    return {
      label: "Eval",
      hexClass: "border-pollen/75 bg-pollen/[0.06] text-pollen shadow-[0_0_14px_rgb(255_184_0/0.22)]",
      badgeClass: "border-pollen/50 text-pollen",
    };
  }
  if (r === "simulator") {
    return {
      label: "Sim",
      hexClass: "border-alert/65 bg-alert/[0.06] text-alert shadow-[0_0_14px_rgb(255_0_170/0.22)]",
      badgeClass: "border-alert/50 text-alert",
    };
  }
  return {
    label: "Action",
    hexClass: "border-success/65 bg-success/[0.06] text-success shadow-[0_0_14px_rgb(0_255_136/0.2)]",
    badgeClass: "border-success/50 text-success",
  };
}

function laneUi(lane: TargetLane): { label: string; badgeClass: string } {
  const all: Record<TargetLane, { label: string; badgeClass: string }> = {
    scout: { label: "Scout", badgeClass: "border-cyan/45 text-cyan" },
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

function HexStepIcon({ n, className }: { n: number; className: string }) {
  return (
    <div
      className={cn(
        "hive-hex-clip-flat flex h-11 w-10 shrink-0 items-center justify-center border-[6px] font-[family-name:var(--font-poppins)] text-sm font-bold tabular-nums",
        className,
      )}
    >
      {n}
    </div>
  );
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
      <p className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] font-semibold uppercase tracking-[0.16em] text-zinc-600">
        DAG · náhľad krokov
      </p>
      <div className="mt-3 flex min-w-min items-center px-0.5">
        {steps.map((step, i) => {
          const ui = roleUi(step.agent_role);
          const prev = i > 0 ? steps[i - 1] : null;
          const dashedTail = i > 0 && i === steps.length - 1;
          return (
            <Fragment key={`${step.step_order}-${step.agent_role}`}>
              {prev ? <div className={previewConnectorFromRole(prev.agent_role, dashedTail)} aria-hidden /> : null}
              <div className="flex flex-col items-center gap-1.5 px-0.5">
                <HexStepIcon n={step.step_order} className={ui.hexClass} />
                <span className="max-w-[4rem] text-center font-[family-name:var(--font-jetbrains-mono)] text-[9px] font-semibold uppercase tracking-wide text-zinc-500">
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
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Náhľad zlyhal";
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
      toast.error("Popis úlohy musí mať aspoň 8 znakov.");
      return;
    }
    setSubmitBusy(true);
    try {
      const res = await hivePostJson<OperatorIntakeResponse>("operator/intake-task", {
        title: intakeTitle(text),
        task_text: text,
        task_type: laneTaskType(targetLane),
        priority: priorityValue(priority),
        swarm_id: null,
        target_lane: targetLane,
        matching_recipe_id: recipeMatch?.postgres_recipe_id ?? null,
        enrich_from_chroma_recipes: enrichRecipes,
        max_steps: 7,
        start_execution: true,
        defer_to_worker: true,
        execution_payload: {},
      });
      toast.success(`Úloha zaradená (${res.execution}).`);
      router.push("/");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Odoslanie zlyhalo";
      toast.error(msg);
    } finally {
      setSubmitBusy(false);
    }
  }

  async function onSaveRecipe(): Promise<void> {
    if (!preview || displaySteps.length < 3) {
      toast.error("Najprv vygeneruj náhľad krokov (aspoň 3).");
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
      toast.success("Recept uložený do katalógu.");
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 403) {
        toast.error("Ukladanie receptov je len pre administrátora (scope dash:recipe_write).");
      } else {
        const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Uloženie zlyhalo";
        toast.error(msg);
      }
    } finally {
      setSaveBusy(false);
    }
  }

  const estUsd = preview?.decomposition_cost_usd;
  const estSec = preview?.estimated_duration_sec;
  const estMin =
    estSec != null && estSec > 0
      ? Math.max(1, Math.round(estSec / 60))
      : displaySteps.length > 0
        ? Math.max(1, Math.round(displaySteps.length * 0.65))
        : null;

  return (
    <div className="mx-auto w-full max-w-3xl pb-24">
      <div className="mb-8 flex flex-col gap-4">
        <Link href="/" className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5 px-4">
          <ChevronLeftIcon className="h-4 w-4" aria-hidden />
          Späť
        </Link>
        <div>
          <h1 className="font-[family-name:var(--font-poppins)] text-3xl font-bold tracking-tight text-[#fafafa]">Nový task</h1>
          <p className="mt-2 max-w-xl font-[family-name:var(--font-inter)] text-sm text-zinc-500">
            Popíš, čo potrebuješ. Auto-workflow breaker rozloží zadanie na atomické kroky.
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-white/[0.08] bg-[#0f0f16]/95 p-6 shadow-[0_0_40px_rgb(0_0_0/0.35)] md:p-8">
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">Popis úlohy</p>
        <textarea
          value={taskText}
          onChange={(e) => setTaskText(e.target.value)}
          rows={6}
          className="mt-3 w-full resize-y rounded-xl border-[2px] border-cyan/20 bg-black/55 px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] outline-none focus:border-pollen/40"
          placeholder="Čo má úľ vykonať?"
        />

        <div className="mt-5 flex flex-col gap-5 border-t border-white/10 pt-5">
          <div>
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Cieľový swarm</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {TARGET_LANES.map((lane) => {
                const { label } = laneUi(lane);
                const active = targetLane === lane;
                return (
                  <button
                    key={lane}
                    type="button"
                    onClick={() => setTargetLane(lane)}
                    className={cn("qs-pill uppercase tracking-wide", active && lanePillActive(lane))}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Priorita</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(
                  [
                    ["low", "nízka"],
                    ["normal", "normálna"],
                    ["high", "vysoká"],
                  ] as const
                ).map(([key, label]) => {
                  const active = priority === key;
                  return (
                    <button key={key} type="button" onClick={() => setPriority(key)} className={cn("qs-pill", active && priorityPillActive(key))}>
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col gap-2 sm:mt-auto sm:items-end">
              <button
                type="button"
                onClick={() => setEnrichRecipes((v) => !v)}
                className={cn("qs-pill", enrichRecipes && "qs-pill--active-cyan")}
              >
                {enrichRecipes ? "✓ " : ""}Chroma · knižnica receptov
              </button>
            </div>
          </div>

          {recipeMatch ? (
            <div className="flex items-center gap-2 rounded-xl border border-success/35 bg-success/[0.05] px-3 py-2">
              <span className="text-success" aria-hidden>
                ✓
              </span>
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-300">
                {recipeMatch.name} · {recipeMatch.similarity.toFixed(2)}
              </span>
            </div>
          ) : previewLoading ? (
            <p className="font-[family-name:var(--font-inter)] text-xs text-zinc-600">Hľadám zhodu receptu…</p>
          ) : enrichRecipes ? (
            <p className="font-[family-name:var(--font-inter)] text-xs text-zinc-600">Žiadna zhoda nad prahom knižnice.</p>
          ) : null}
        </div>
      </div>

      <div className="mt-8 rounded-2xl border border-white/[0.08] bg-[#0c0c14]/95 p-6 shadow-[0_0_36px_rgb(0_255_255/0.06)] md:p-8">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">Náhľad dekompozície</h2>
          <p className="font-[family-name:var(--font-inter)] text-xs text-zinc-500">
            {previewLoading ? "LLM pracuje…" : "LLM"}
            {displaySteps.length > 0 ? ` · ${displaySteps.length} krokov` : previewError ? " · chyba" : ""}
          </p>
        </div>
        {previewError ? (
          <div className="mt-4 rounded-xl border border-pollen/20 bg-[#0f0f1a] p-4 md:p-[18px]">
            <div className="mb-2.5 flex items-center gap-2.5">
              <span className="text-xl" aria-hidden>
                ⚠️
              </span>
              <div className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen">LLM Preview Unavailable</div>
            </div>
            <div className="mb-3 font-[family-name:var(--font-inter)] text-[13px] leading-relaxed text-[#9898b8]">
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
            <p className="mt-2.5 font-mono text-[11px] text-[#5a5a7a]">You can still submit the task — Claude fallback will handle it.</p>
            {previewError.includes("LiteLLM router exhausted") ||
            previewError.includes("credentials for configured models") ||
            previewError.includes("OPENAI_API_KEY") ? (
              <p className="mt-3 font-[family-name:var(--font-inter)] text-xs text-zinc-500">
                If every provider failed, inspect{" "}
                <Link href="/settings/llm-keys" className="font-semibold text-cyan underline-offset-2 hover:text-pollen">
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
            <li className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-zinc-600">
              Zadaj aspoň 8 znakov — náhľad sa dobije automaticky.
            </li>
          ) : null}
          {previewLoading && displaySteps.length === 0 ? (
            <li className="rounded-xl border border-cyan/15 bg-black/30 px-4 py-8 text-center text-sm text-zinc-500">Načítavam kroky…</li>
          ) : null}
          {displaySteps.map((step) => {
            const ui = roleUi(step.agent_role);
            return (
              <li
                key={`${step.step_order}-${step.description.slice(0, 24)}`}
                className="flex gap-4 rounded-xl border border-white/[0.06] bg-black/35 px-3 py-3 md:px-4"
              >
                <HexStepIcon n={step.step_order} className={ui.hexClass} />
                <div className="min-w-0 flex-1">
                  <p className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">{step.description}</p>
                  <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">{step.guardrail_summary}</p>
                </div>
                <span
                  className={cn(
                    "hidden h-fit shrink-0 rounded-full border px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-wide sm:inline-flex",
                    ui.badgeClass,
                  )}
                >
                  {ui.label}
                </span>
              </li>
            );
          })}
        </ul>

        <div className="mt-8 flex flex-col gap-4 border-t border-white/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-[family-name:var(--font-inter)] text-xs text-zinc-500">
            Odhadované náklady · {estUsd != null ? `$${estUsd.toFixed(2)}` : "—"}
            {estMin != null ? ` · ~${estMin} min` : ""}
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={saveBusy || displaySteps.length < 3}
              onClick={() => void onSaveRecipe()}
              className="qs-btn qs-btn--secondary disabled:opacity-40"
            >
              {saveBusy ? "Ukladám…" : "Uložiť ako recept"}
            </button>
            <button
              type="button"
              disabled={submitBusy || taskText.trim().length < 8}
              onClick={() => void onSubmit()}
              className="qs-btn qs-btn--primary gap-2 disabled:opacity-40"
            >
              <PlayIcon className="h-4 w-4" aria-hidden />
              {submitBusy ? "Odosielam…" : "▶ Odoslať"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
