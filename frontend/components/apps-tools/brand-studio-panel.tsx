"use client";

import { Loader2, Palette, Sparkles } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";

interface BrandStudioSnapshot {
  enabled: boolean;
  simulate_only: boolean;
  brand_ready: boolean;
  brand_char_count: number;
  brand_usage_pct: number;
  sections_filled: number;
  operator_hint: string;
  links: Record<string, string>;
}

interface RubricDimension {
  id: string;
  label: string;
  weight: number;
  score: number;
  weighted_score: number;
}

interface RubricPreview {
  enabled: boolean;
  template_id: string;
  template_name: string;
  overall_score: number;
  pass_threshold: number;
  passed: boolean;
  dimensions: RubricDimension[];
  feedback: string;
  operator_hint: string;
  brand_compliance?: {
    passed?: boolean;
    overall_score?: number;
    pass_threshold?: number;
  } | null;
}

interface RubricPreviewResponse {
  brand_ready: boolean;
  rubric: RubricPreview;
  operator_hint: string;
}

const SAMPLE_BODY =
  "Ship verified outcomes first — your audience trusts proof over hype.\n\nCTA: Start a simulate-first session in Queenswarm today.";

export function BrandStudioPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<BrandStudioSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("Verify-first launch");
  const [body, setBody] = useState(SAMPLE_BODY);
  const [cta, setCta] = useState("Try simulate-first");
  const [preview, setPreview] = useState<RubricPreviewResponse | null>(null);
  const [scoring, setScoring] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<BrandStudioSnapshot>("operator/brand-studio");
      setSnapshot(data);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Brand studio unavailable");
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const runPreview = useCallback(async () => {
    if (body.trim().length < 20) {
      toast.error("Body must be at least 20 characters.");
      return;
    }
    setScoring(true);
    try {
      const data = await hivePostJson<RubricPreviewResponse>("operator/brand-studio/rubric-preview", {
        title,
        body,
        cta,
        hashtags: ["Queenswarm", "AgentOS"],
      });
      setPreview(data);
      toast.success(data.rubric.passed ? "Rubric pass (simulate-only)" : "Below threshold — revise copy");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Rubric preview failed");
    } finally {
      setScoring(false);
    }
  }, [body, cta, title]);

  if (loading && !snapshot) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading Brand studio…
      </div>
    );
  }

  if (!snapshot?.enabled) {
    return (
      <V4Card data-testid="brand-studio-panel">
        <V4CardHeader title="Brand studio" description="Brand studio rubric preview is disabled." />
      </V4Card>
    );
  }

  return (
    <V4Card
      className="border-pollen/30 shadow-[0_0_20px_rgba(255,184,0,0.08)]"
      data-testid="brand-studio-panel"
    >
      <V4CardHeader
        leadingIcon={Palette}
        leadingIconTone="default"
        kicker="Simulate-only"
        title="Brand studio · rubric preview"
        description={snapshot.operator_hint}
        actions={
          <div className="flex flex-wrap gap-2">
            <HiveRefreshButton onClick={() => void reload()} />
            <Link href={snapshot.links.brand_pack ?? "/knowledge#memory"} className="qs-btn qs-btn--ghost qs-btn--sm">
              Brain Pack Brand
            </Link>
          </div>
        }
      />

      <div className="flex flex-wrap gap-2 px-4 pb-3">
        <V4Badge tone={snapshot.brand_ready ? "ok" : "warn"}>
          {snapshot.brand_ready ? "Brand pack ready" : "Brand pack incomplete"}
        </V4Badge>
        <V4Badge tone="info">{snapshot.sections_filled} sections filled</V4Badge>
        <V4Badge tone="purple">{snapshot.brand_usage_pct}% Brain Pack</V4Badge>
        <V4Badge tone="gold">No live publish</V4Badge>
      </div>

      <div className="space-y-3 px-4 pb-4">
        <label className="block space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-(--qs-text-3)">Title</span>
          <input
            className="qs-input w-full"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            data-testid="brand-studio-title"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-(--qs-text-3)">Body</span>
          <textarea
            className="qs-input min-h-[8rem] w-full font-mono text-sm"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            data-testid="brand-studio-body"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-(--qs-text-3)">CTA</span>
          <input
            className="qs-input w-full"
            value={cta}
            onChange={(e) => setCta(e.target.value)}
            data-testid="brand-studio-cta"
          />
        </label>
        <button
          type="button"
          className="qs-btn qs-btn--primary inline-flex gap-2"
          disabled={scoring}
          onClick={() => void runPreview()}
          data-testid="brand-studio-simulate-rubric"
        >
          {scoring ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Sparkles className="size-4" aria-hidden />}
          Simulate rubric
        </button>
      </div>

      {preview?.rubric?.enabled ? (
        <div
          className="mx-4 mb-4 rounded-lg border border-cyan-500/25 bg-cyan-500/5 p-3"
          data-testid="brand-studio-rubric-preview"
        >
          <p className="text-[11px] font-semibold uppercase tracking-wide text-cyan-300">NP2 creative rubric</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <V4Badge tone={preview.rubric.passed ? "ok" : "warn"}>
              {(preview.rubric.overall_score * 100).toFixed(0)}% overall
            </V4Badge>
            <V4Badge tone="info">Pass ≥ {(preview.rubric.pass_threshold * 100).toFixed(0)}%</V4Badge>
            {preview.rubric.template_name ? <V4Badge tone="gold">{preview.rubric.template_name}</V4Badge> : null}
          </div>
          {(preview.rubric.dimensions ?? []).length > 0 ? (
            <ul className="mt-3 space-y-1 text-xs text-(--qs-text-2)">
              {preview.rubric.dimensions.map((row) => (
                <li key={row.id} className="flex flex-wrap items-center justify-between gap-2">
                  <span>{row.label}</span>
                  <span className="font-mono text-cyan-300">
                    {(row.score * 100).toFixed(0)}% · w{(row.weight * 100).toFixed(0)}%
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
          {preview.rubric.brand_compliance ? (
            <div className="mt-3 border-t border-cyan-500/20 pt-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-pollen">Brand compliance</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <V4Badge tone={preview.rubric.brand_compliance.passed ? "ok" : "warn"}>
                  {typeof preview.rubric.brand_compliance.overall_score === "number"
                    ? `${(preview.rubric.brand_compliance.overall_score * 100).toFixed(0)}%`
                    : "—"}
                </V4Badge>
              </div>
            </div>
          ) : null}
          {preview.operator_hint ? <p className="mt-2 text-xs text-(--qs-text-3)">{preview.operator_hint}</p> : null}
        </div>
      ) : null}
    </V4Card>
  );
}
