"use client";

import { Loader2Icon, Play, Sparkles } from "lucide-react";
import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { QsSelect } from "@/components/ui/qs-select";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { RecipeSemanticHitRow } from "@/components/hive/recipe-cosine-match-panel";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { AgentRow, RecipeMatchConfigPayload, RecipeSemanticHit } from "@/lib/hive-types";
import { DEFAULT_RECIPE_MATCH_CONFIG, formatSimilarityPct } from "@/lib/recipe-match-utils";
import { cn } from "@/lib/utils";

const AGENT_ROLES = [
  "scraper",
  "evaluator",
  "simulator",
  "reporter",
  "trader",
  "marketer",
  "blog_writer",
  "social_poster",
  "learner",
  "recipe_keeper",
] as const;

const AGENT_ROLE_OPTIONS = AGENT_ROLES.map((role) => ({ value: role, label: role }));

interface ExemplarBrief {
  agent_id: string;
  name: string;
  role: string;
  performance_score: number;
  pollen_points: number;
}

interface LearningConsoleProps {
  readonly showHeader?: boolean;
  readonly variant?: "default" | "v4";
}

/** Pollen · imitation · reflections — backed by ``/api/v1/learning/*``. */
export function LearningConsole({ showHeader = true, variant = "default" }: LearningConsoleProps): JSX.Element {
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [role, setRole] = useState<string>("evaluator");
  const [exemplars, setExemplars] = useState<ExemplarBrief[]>([]);
  const [busy, setBusy] = useState(false);

  const [recipeQuery, setRecipeQuery] = useState("");
  const [recipeHits, setRecipeHits] = useState<RecipeSemanticHit[]>([]);
  const [matchConfig, setMatchConfig] = useState<RecipeMatchConfigPayload>(DEFAULT_RECIPE_MATCH_CONFIG);

  const [reflectAgent, setReflectAgent] = useState("");
  const [reflectInsight, setReflectInsight] = useState("");

  const [poolUsd, setPoolUsd] = useState("120");
  const [rewardAgent, setRewardAgent] = useState("");
  const [rewardSignal, setRewardSignal] = useState("0.82");

  const [copier, setCopier] = useState("");
  const [exemplar, setExemplar] = useState("");

  useEffect(() => {
    let cancelled = false;
    void hiveGet<AgentRow[]>("agents?limit=120")
      .then((rows) => {
        if (!cancelled) setAgents(rows);
      })
      .catch(() => null);
    return () => {
      cancelled = true;
    };
  }, []);

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

  const loadExemplars = useCallback(async () => {
    setBusy(true);
    try {
      const rows = await hiveGet<ExemplarBrief[]>(`learning/imitation/exemplars?role=${encodeURIComponent(role)}`);
      setExemplars(rows);
      toast.success(`${rows.length} exemplars`);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Exemplar query failed.");
    } finally {
      setBusy(false);
    }
  }, [role]);

  const searchRecipes = useCallback(async () => {
    const q = recipeQuery.trim();
    if (!q) {
      toast.message("Enter a search cue.");
      return;
    }
    setBusy(true);
    try {
      const hits = await hiveGet<RecipeSemanticHit[]>(`recipes/search?q=${encodeURIComponent(q)}&limit=16`);
      setRecipeHits(hits);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Semantic search failed.");
    } finally {
      setBusy(false);
    }
  }, [recipeQuery]);

  async function submitReflection(ev: FormEvent): Promise<void> {
    ev.preventDefault();
    if (!reflectAgent || !reflectInsight.trim()) {
      toast.error("Agent + insight required.");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson("learning/reflection", {
        agent_id: reflectAgent,
        insight: reflectInsight.trim(),
        task_id: null,
        pollen_earned: 0,
      });
      toast.success("Reflection logged.");
      setReflectInsight("");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Reflection failed.");
    } finally {
      setBusy(false);
    }
  }

  async function allocatePollen(ev: FormEvent): Promise<void> {
    ev.preventDefault();
    if (!rewardAgent) {
      toast.error("Pick an agent.");
      return;
    }
    const pool = Number(poolUsd);
    const sig = Number(rewardSignal);
    if (!Number.isFinite(pool) || pool <= 0 || !Number.isFinite(sig)) {
      toast.error("Invalid pool or signal.");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson("learning/rewards/allocate", {
        pool,
        task_id: null,
        signals: [{ agent_id: rewardAgent, signal: sig }],
        reason: "dashboard allocation sandbox",
        blend_performance: true,
      });
      toast.success("Pollen allocated.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Allocation rejected.");
    } finally {
      setBusy(false);
    }
  }

  async function recordImitation(ev: FormEvent): Promise<void> {
    ev.preventDefault();
    if (!copier || !exemplar) {
      toast.error("Copier + exemplar agents required.");
      return;
    }
    setBusy(true);
    try {
      await hivePostJson("learning/imitation/copy", {
        copier_agent_id: copier,
        exemplar_agent_id: exemplar,
        recipe_id: null,
      });
      toast.success("Imitation edge recorded.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Imitation insert failed.");
    } finally {
      setBusy(false);
    }
  }

  const runReflectionPass = useCallback(async () => {
    setBusy(true);
    try {
      await hivePostJson("dreaming/run-now", {});
      toast.success("Reflection pass queued — dream cycle will consolidate learning logs.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Reflection pass failed.");
    } finally {
      setBusy(false);
    }
  }, []);

  const agentSelectOptions = useMemo(
    () => agents.map((agent) => ({ value: agent.id, label: `${agent.name} · ${agent.role}` })),
    [agents],
  );

  const isV4 = variant === "v4";

  if (isV4) {
    return (
      <div className="flex flex-col gap-8">
        <div className="v4-learning-lane">
          <Sparkles className="h-4 w-4 shrink-0 text-(--qs-amber)" aria-hidden />
          <div>
            <p className="v4-label-kicker">Learning + rewards lane</p>
            <p className="text-xs text-(--qs-text-3)">
              Pollen allocation, imitation, and semantic recipe recall in one operator surface.
            </p>
          </div>
        </div>

        <div className="v4-cols-2">
          <section className="v4-learning-panel">
            <h3 className="text-base font-semibold text-(--qs-text)">Imitation exemplars</h3>
            <p className="mt-1 text-xs text-(--qs-text-3)">Top pollen performers per role · excludes offline bees automatically server-side.</p>
            <div className="v4-learning-inline-actions mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
              <QsSelect value={role} onValueChange={setRole} className="min-h-11 w-full min-w-0 flex-1 rounded-(--qs-radius-sm) sm:min-w-[140px]" options={AGENT_ROLE_OPTIONS} />
              <button type="button" disabled={busy} className="qs-btn qs-btn--ghost qs-btn--sm w-full sm:w-auto" onClick={() => void loadExemplars()}>
                {busy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : null}
                Load
              </button>
            </div>
            <ul className="mt-4 space-y-2">
              {exemplars.map((row) => (
                <li key={row.agent_id} className="flex flex-wrap items-center justify-between gap-2 rounded-(--qs-radius-sm) border border-(--qs-border) bg-white/[0.04] px-3 py-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-(--qs-text)">{row.name}</p>
                    <p className="text-xs text-(--qs-text-3)">{row.role}</p>
                  </div>
                  <div className="flex gap-3 text-xs tabular-nums">
                    <span className="text-(--qs-cyan)">pollen {Math.round(row.pollen_points)}</span>
                    <span className="text-(--qs-amber)">perf {row.performance_score.toFixed(2)}</span>
                  </div>
                </li>
              ))}
            </ul>
            {!exemplars.length ? <p className="mt-3 text-xs text-(--qs-text-3)">No exemplars loaded yet.</p> : null}
          </section>

          <section className="v4-learning-panel">
            <h3 className="text-base font-semibold text-(--qs-text)">Semantic recipe recall</h3>
            <p className="mt-1 text-xs text-(--qs-text-3)">
              GET /recipes/search · auto-match when hybrid score ≥ {formatSimilarityPct(matchConfig.match_threshold)}
            </p>
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <input
                value={recipeQuery}
                onChange={(e) => setRecipeQuery(e.target.value)}
                placeholder="Describe the workflow you need…"
                className="qs-input min-h-11 w-full flex-1 rounded-(--qs-radius-sm)"
              />
              <button type="button" disabled={busy} className="qs-btn qs-btn--ghost qs-btn--sm w-full sm:w-auto" onClick={() => void searchRecipes()}>
                Search
              </button>
            </div>
            <ul className="mt-4 space-y-2">
              {recipeHits.map((hit) => (
                <RecipeSemanticHitRow key={hit.chroma_document_id} hit={hit} config={matchConfig} />
              ))}
            </ul>
            {!recipeHits.length ? <p className="mt-3 text-xs text-(--qs-text-3)">No semantic hits yet.</p> : null}
          </section>
        </div>

        <div className="v4-cols-3">
          <form onSubmit={(e) => void submitReflection(e)} className="v4-learning-panel">
            <h3 className="text-base font-semibold text-(--qs-text)">Reflection</h3>
            <label className="mt-4 block">
              <span className="v4-field-label">Agent</span>
              <QsSelect value={reflectAgent} onValueChange={setReflectAgent} placeholder="Select…" className="min-h-11 w-full rounded-(--qs-radius-sm)" options={agentSelectOptions} />
            </label>
            <label className="mt-3 block">
              <span className="v4-field-label">Insight</span>
              <textarea required value={reflectInsight} onChange={(e) => setReflectInsight(e.target.value)} rows={4} className="qs-input w-full rounded-(--qs-radius-sm)" />
            </label>
            <button type="submit" disabled={busy} className="qs-btn qs-btn--ghost qs-btn--sm mt-4 w-full text-(--qs-green)">
              Log reflection
            </button>
          </form>

          <form onSubmit={(e) => void allocatePollen(e)} className="v4-learning-panel">
            <h3 className="text-base font-semibold text-(--qs-text)">Pollen allocate</h3>
            <label className="mt-4 block">
              <span className="v4-field-label">Pollen pool</span>
              <input value={poolUsd} onChange={(e) => setPoolUsd(e.target.value)} type="number" step="0.1" className="qs-input min-h-11 w-full rounded-(--qs-radius-sm) font-mono" />
            </label>
            <label className="mt-3 block">
              <span className="v4-field-label">Agent</span>
              <QsSelect value={rewardAgent} onValueChange={setRewardAgent} placeholder="Select…" className="min-h-11 w-full rounded-(--qs-radius-sm)" options={agentSelectOptions} />
            </label>
            <label className="mt-3 block">
              <span className="v4-field-label">Signal</span>
              <input value={rewardSignal} onChange={(e) => setRewardSignal(e.target.value)} className="qs-input min-h-11 w-full rounded-(--qs-radius-sm) font-mono" />
            </label>
            <button type="submit" disabled={busy} className="qs-btn qs-btn--primary qs-btn--sm mt-4 w-full">
              Allocate Maynard-Cross
            </button>
          </form>

          <form onSubmit={(e) => void recordImitation(e)} className="v4-learning-panel">
            <h3 className="text-base font-semibold text-(--qs-text)">Imitation edge</h3>
            <label className="mt-4 block">
              <span className="v4-field-label">Copier</span>
              <QsSelect value={copier} onValueChange={setCopier} placeholder="Select…" className="min-h-11 w-full rounded-(--qs-radius-sm)" options={agentSelectOptions} />
            </label>
            <label className="mt-3 block">
              <span className="v4-field-label">Exemplar</span>
              <QsSelect value={exemplar} onValueChange={setExemplar} placeholder="Select…" className="min-h-11 w-full rounded-(--qs-radius-sm)" options={agentSelectOptions} />
            </label>
            <button type="submit" disabled={busy} className="qs-btn qs-btn--ghost qs-btn--sm mt-4 w-full">
              Record imitation
            </button>
          </form>
        </div>

        <V4Card glow>
          <V4CardHeader
            as="h3"
            title="Learning console"
            description="LearningLog reflections per agent-task cycle. Pollen rewards via Maynard-Cross + performance blend."
            actions={
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
                disabled={busy}
                onClick={() => void runReflectionPass()}
              >
                <Play className="h-3.5 w-3.5" aria-hidden />
                Run reflection pass
              </button>
            }
          />
          <p className="text-sm text-(--qs-text-3)">Reflection feed appears here after agents log insights through the hive learning loop.</p>
        </V4Card>
      </div>
    );
  }

  return (
    <main
      className={cn(
        "flex w-full flex-col gap-8 text-zinc-200",
        showHeader ? "mx-auto max-w-6xl px-4 py-10" : "px-0 py-0",
      )}
    >
      {showHeader ? (
        <header className="space-y-3">
          <p className="font-[family-name:var(--font-poppins)] text-xs uppercase tracking-[0.42em] text-cyan">Phase 2.6 · Learning engine</p>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-pollen/35 bg-black/70 text-pollen">
                <Sparkles className="h-5 w-5" aria-hidden />
              </div>
              <div>
                <h1 className="font-[family-name:var(--font-poppins)] text-3xl font-bold text-pollen md:text-[2rem]">Hive learning lane</h1>
                <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-400">
                  Mobile-first panels · desktop sees two-column grids. Calls mirror Maynard-Cross rewards + imitation telemetry already running in the API.
                </p>
              </div>
            </div>
          </div>
        </header>
      ) : (
        <div className="flex items-center gap-3 rounded-2xl border border-pollen/20 bg-black/30 px-3 py-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-pollen/35 bg-black/60 text-pollen">
            <Sparkles className="h-4 w-4" aria-hidden />
          </div>
          <div>
            <p className="font-[family-name:var(--font-poppins)] text-xs uppercase tracking-[0.24em] text-cyan">Learning + rewards lane</p>
            <p className="font-[family-name:var(--font-poppins)] text-xs text-zinc-400">
              Pollen allocation, imitation, and semantic recipe recall in one operator surface.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-[26px] border border-[#1c2045] bg-black/72 p-5 md:p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#EEEEFF]">Imitation exemplars</h2>
              <p className="font-[family-name:var(--font-poppins)] text-xs text-zinc-500">Top pollen performers per role · excludes offline bees automatically server-side.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <QsSelect
                value={role}
                onValueChange={setRole}
                className="min-h-[44px] flex-1 sm:flex-none"
                options={AGENT_ROLE_OPTIONS}
              />
              <button
                type="button"
                disabled={busy}
                onClick={() => void loadExemplars()}
                className="inline-flex min-h-[44px] items-center gap-2 rounded-xl border border-pollen/50 px-4 py-2 font-[family-name:var(--font-poppins)] text-xs font-semibold text-pollen hover:bg-pollen/10 disabled:opacity-40 touch-manipulation"
              >
                {busy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : null}
                Load
              </button>
            </div>
          </div>
          <ul className="mt-5 space-y-3 font-[family-name:var(--font-poppins)] text-sm">
            {exemplars.map((row) => (
              <li key={row.agent_id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#252a55] bg-black/80 px-3 py-2">
                <div className="min-w-0">
                  <p className="truncate font-semibold text-[#fafafa]">{row.name}</p>
                  <p className="text-xs text-zinc-500">{row.role}</p>
                </div>
                <div className="flex gap-3 text-xs tabular-nums text-cyan">
                  <span>pollen {Math.round(row.pollen_points)}</span>
                  <span className="text-pollen">perf {row.performance_score.toFixed(2)}</span>
                </div>
              </li>
            ))}
          </ul>
          {!exemplars.length ? <p className="mt-4 text-xs text-zinc-500">No exemplars loaded yet.</p> : null}
        </section>

        <section className="rounded-[26px] border border-[#1c2045] bg-black/72 p-5 md:p-6">
          <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#EEEEFF]">Semantic recipe recall</h2>
          <p className="font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
            GET /recipes/search · auto-match when hybrid score ≥ {formatSimilarityPct(matchConfig.match_threshold)}
          </p>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            <input
              value={recipeQuery}
              onChange={(e) => setRecipeQuery(e.target.value)}
              placeholder="Describe the workflow you need…"
              className="min-h-[44px] flex-1 rounded-xl border border-[#1e2348] bg-black/76 px-3 py-2 font-[family-name:var(--font-poppins)] text-sm"
            />
            <button
              type="button"
              disabled={busy}
              onClick={() => void searchRecipes()}
              className="min-h-[44px] rounded-xl border border-data/45 px-5 py-2 font-[family-name:var(--font-poppins)] text-sm font-semibold text-cyan hover:bg-cyan/10 disabled:opacity-40 touch-manipulation"
            >
              Search
            </button>
          </div>
          <ul className="mt-4 space-y-3">
            {recipeHits.map((hit) => (
              <RecipeSemanticHitRow key={hit.chroma_document_id} hit={hit} config={matchConfig} />
            ))}
          </ul>
          {!recipeHits.length ? <p className="mt-3 text-xs text-zinc-500">No semantic hits yet.</p> : null}
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <form onSubmit={(e) => void submitReflection(e)} className="rounded-[26px] border border-[#1c2045] bg-black/72 p-5 md:p-6">
          <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#EEEEFF]">Reflection</h2>
          <label className="mt-4 flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs text-[#BEBED6]">
            Agent
            <QsSelect value={reflectAgent} onValueChange={setReflectAgent} placeholder="Select…" className="min-h-[44px]" options={agentSelectOptions} />
          </label>
          <label className="mt-3 flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs text-[#BEBED6]">
            Insight
            <textarea
              required
              value={reflectInsight}
              onChange={(e) => setReflectInsight(e.target.value)}
              rows={4}
              className="rounded-xl border border-[#1e2348] bg-black/76 px-3 py-2 font-[family-name:var(--font-poppins)] text-sm"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="mt-4 w-full min-h-[44px] rounded-2xl border border-[#00FF88]/40 px-4 py-3 font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#00FF88] hover:bg-[#00FF88]/10 disabled:opacity-40 touch-manipulation"
          >
            Log reflection
          </button>
        </form>

        <form onSubmit={(e) => void allocatePollen(e)} className="rounded-[26px] border border-[#1c2045] bg-black/72 p-5 md:p-6">
          <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#EEEEFF]">Pollen allocate</h2>
          <label className="mt-4 flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs text-[#BEBED6]">
            Pollen pool
            <input value={poolUsd} onChange={(e) => setPoolUsd(e.target.value)} type="number" step="0.1" className="min-h-[44px] rounded-xl border border-[#1e2348] bg-black/76 px-3 py-2 font-mono text-sm" />
          </label>
          <label className="mt-3 flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs text-[#BEBED6]">
            Agent
            <QsSelect value={rewardAgent} onValueChange={setRewardAgent} placeholder="Select…" className="min-h-[44px]" options={agentSelectOptions} />
          </label>
          <label className="mt-3 flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs text-[#BEBED6]">
            Signal
            <input value={rewardSignal} onChange={(e) => setRewardSignal(e.target.value)} className="min-h-[44px] rounded-xl border border-[#1e2348] bg-black/76 px-3 py-2 font-mono text-sm" />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="mt-4 w-full min-h-[44px] rounded-2xl border border-pollen/60 px-4 py-3 font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen hover:bg-pollen/10 disabled:opacity-40 touch-manipulation"
          >
            Allocate Maynard-Cross
          </button>
        </form>

        <form onSubmit={(e) => void recordImitation(e)} className="rounded-[26px] border border-[#1c2045] bg-black/72 p-5 md:p-6">
          <h2 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#EEEEFF]">Imitation edge</h2>
          <label className="mt-4 flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs text-[#BEBED6]">
            Copier
            <QsSelect value={copier} onValueChange={setCopier} placeholder="Select…" className="min-h-[44px]" options={agentSelectOptions} />
          </label>
          <label className="mt-3 flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-xs text-[#BEBED6]">
            Exemplar
            <QsSelect value={exemplar} onValueChange={setExemplar} placeholder="Select…" className="min-h-[44px]" options={agentSelectOptions} />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="mt-4 w-full min-h-[44px] rounded-2xl border border-magenta/40 px-4 py-3 font-[family-name:var(--font-poppins)] text-sm font-semibold text-magenta hover:bg-magenta/10 disabled:opacity-40 touch-manipulation"
          >
            Record imitation
          </button>
        </form>
      </div>
    </main>
  );
}
