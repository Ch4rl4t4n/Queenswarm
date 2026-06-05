"use client";

import { DownloadIcon, Loader2Icon, SparklesIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  type FactoryLlmReadiness,
} from "@/components/apps-tools/factory-llm-readiness-banner";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { HarnessEvalResult } from "@/lib/hive-types";
import { downloadTextFile } from "@/lib/skill-export-utils";

function eur(cents: number): string {
  return `€${(cents / 100).toFixed(2)}`;
}

function criticCostHint(model: string): string {
  const lowered = model.toLowerCase();
  if (lowered.includes("nemotron") || lowered.includes("openrouter")) {
    return "~€0,02 navyše (OpenRouter)";
  }
  if (lowered.includes("grok")) {
    return "~€0,08 navyše (Grok)";
  }
  if (lowered.includes("gpt-4o-mini")) {
    return "~€0,03 navyše (OpenAI)";
  }
  return "~€0,05 navyše";
}

function criticModelLabel(model: string, llm: FactoryLlmReadiness | null): string {
  const match = llm?.available_models?.find((row) => row.value === model);
  return match?.label ?? model;
}

interface HarnessEvalPanelProps {
  llm?: FactoryLlmReadiness | null;
}

export function HarnessEvalPanel({ llm: llmProp }: HarnessEvalPanelProps): JSX.Element {
  const [title, setTitle] = useState("My workflow");
  const [markdown, setMarkdown] = useState("");
  const [runLlmCritic, setRunLlmCritic] = useState(false);
  const [llm, setLlm] = useState<FactoryLlmReadiness | null>(llmProp ?? null);
  const [criticModel, setCriticModel] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<HarnessEvalResult | null>(null);

  useEffect(() => {
    if (llmProp) {
      setLlm(llmProp);
    }
  }, [llmProp]);

  useEffect(() => {
    if (llmProp || llm) {
      return;
    }
    void hiveGet<FactoryLlmReadiness>("factory-readiness/llm")
      .then((data) => setLlm(data))
      .catch(() => {
        /* optional — heuristic eval still works */
      });
  }, [llm, llmProp]);

  useEffect(() => {
    if (!llm?.primary_model) {
      return;
    }
    setCriticModel((prev) => prev || llm.primary_model);
  }, [llm?.primary_model]);

  const modelOptions = useMemo(() => {
    if (llm?.available_models?.length) {
      return llm.available_models.map((row) => ({
        value: row.value,
        label: row.configured ? row.label : `${row.label} (key missing)`,
        disabled: !row.configured,
      }));
    }
    if (llm?.primary_model) {
      return [{ value: llm.primary_model, label: llm.primary_model }];
    }
    return [];
  }, [llm]);

  const selectedCriticConfigured = useMemo(() => {
    if (!criticModel) {
      return false;
    }
    const match = llm?.available_models?.find((row) => row.value === criticModel);
    return match?.configured ?? Boolean(llm?.chain_usable);
  }, [criticModel, llm]);

  const runEval = async (): Promise<void> => {
    if (markdown.trim().length < 40) {
      toast.error("Workflow must be at least 40 characters.");
      return;
    }
    if (runLlmCritic && !selectedCriticConfigured) {
      toast.error("Vyber nakonfigurovaný LLM critic — dopln kľúč v Settings → AI · LLM keys.");
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      const data = await hivePostJson<HarnessEvalResult>("harness-products/eval", {
        title: title.trim() || "Submitted workflow",
        workflow_markdown: markdown,
        run_llm_critic: runLlmCritic,
        critic_model: runLlmCritic && criticModel ? criticModel : undefined,
      });
      setResult(data);
      toast.success(data.passed ? "Eval PASS" : "Eval completed — see issues");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Eval failed.");
    } finally {
      setBusy(false);
    }
  };

  const downloadReport = (): void => {
    if (!result?.eval_report_md) return;
    const slug = title.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-") || "eval-report";
    downloadTextFile(`${slug}-EVAL_REPORT.md`, result.eval_report_md);
  };

  return (
    <V4Card className="mt-4">
      <V4CardHeader
        title="Eval-as-a-Service"
        description="Vlož SKILL/workflow markdown — dostaneš EVAL_REPORT (PASS/FAIL). Predaj rovnakú službu na Gumroad (~€29)."
      />
      <div className="space-y-3 px-4 pb-4">
        <label className="block text-sm">
          <span className="text-(--qs-text-3)">Title</span>
          <input
            type="text"
            className="qs-input mt-1 w-full max-w-md"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
          />
        </label>
        <label className="block text-sm">
          <span className="text-(--qs-text-3)">Workflow / SKILL.md</span>
          <textarea
            className="qs-input mt-1 min-h-[140px] w-full font-mono text-xs"
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            placeholder={"---\nname: my-skill\ndescription: ...\n---\n\n# Title\n\nWhen to use: ...\n\n1. Step one\n2. Step two"}
          />
        </label>
        <div className="space-y-2 max-w-md">
          <label className="flex items-center justify-between gap-3 text-sm">
            <span>LLM critic ({criticCostHint(criticModel || llm?.primary_model || "grok")})</span>
            <HiveSwitch checked={runLlmCritic} onCheckedChange={setRunLlmCritic} />
          </label>
          {runLlmCritic ? (
            <div className="space-y-1">
              <span className="text-xs text-(--qs-text-3)">Critic model</span>
              <QsSelect
                value={criticModel}
                onValueChange={setCriticModel}
                options={modelOptions}
                disabled={modelOptions.length === 0}
                aria-label="Eval LLM critic model"
                className="w-full"
              />
              {criticModel ? (
                <p className="text-[10px] text-(--qs-text-4)">
                  {criticModelLabel(criticModel, llm)}
                  {!selectedCriticConfigured ? " — API key missing for this provider" : null}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm gap-1"
          disabled={busy || (runLlmCritic && !selectedCriticConfigured)}
          onClick={() => void runEval()}
        >
          {busy ? <Loader2Icon className="size-3.5 animate-spin" aria-hidden /> : <SparklesIcon className="size-3.5" aria-hidden />}
          Run eval
        </button>

        {result ? (
          <div className="rounded-xl border border-(--qs-border-2) bg-(--qs-surface-2)/40 px-3 py-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <V4Badge tone={result.passed ? "ok" : "warn"}>{result.passed ? "PASS" : "FAIL"}</V4Badge>
              <span className="text-xs text-(--qs-text-3)">
                tier {result.tier} · score {Math.round(result.score * 100)}%
              </span>
              <span className="text-xs font-mono text-pollen">Gumroad hint {eur(result.recommended_gumroad_price_eur_cents)}</span>
            </div>
            {result.issues.length > 0 ? (
              <ul className="mt-2 list-inside list-disc text-[11px] text-(--qs-text-4)">
                {result.issues.slice(0, 8).map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            ) : null}
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm mt-3 gap-1" onClick={downloadReport}>
              <DownloadIcon className="size-3.5" aria-hidden />
              Download EVAL_REPORT.md
            </button>
          </div>
        ) : null}
      </div>
    </V4Card>
  );
}
