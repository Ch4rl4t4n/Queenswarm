"use client";

import { ChevronDown, ChevronUp, Loader2, Rocket, Sparkles } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";

interface CampaignStep {
  id: string;
  label: string;
  status: "done" | "ready" | "pending" | "blocked";
  detail: string;
  link: string | null;
}

interface BrandPack {
  id: string;
  label: string;
  source: string;
  detail: string;
  ready: boolean;
}

interface CampaignDraft {
  brand_pack_id: string | null;
  channel: string;
  title: string;
  body: string;
  cta: string;
  hashtags: string[];
  media_url: string | null;
}

interface CampaignRubric {
  template_id: string;
  template_name: string;
  score: number | null;
  pass_threshold: number;
  passed: boolean;
  feedback: string;
}

interface CampaignSnapshot {
  enabled: boolean;
  progress_pct: number;
  steps: CampaignStep[];
  brand_packs: BrandPack[];
  draft: CampaignDraft;
  rubric: CampaignRubric;
  deliverable_id: string | null;
  simulate_ok: boolean | null;
  simulate_message: string;
  links: Record<string, string>;
}

interface RubricRunResponse {
  passed: boolean;
  score: number;
  message: string;
}

interface SubmitResponse {
  ok: boolean;
  deliverable_id: string;
  simulate_ok: boolean;
  simulate_message: string;
  publish_queue_href: string;
  social_publish_href: string;
  message: string;
}

const CHANNELS = ["instagram", "facebook", "twitter", "linkedin", "tiktok", "newsletter", "blog"] as const;

function stepTone(status: CampaignStep["status"]): "ok" | "warn" | "info" | "err" {
  if (status === "done") return "ok";
  if (status === "blocked") return "err";
  if (status === "ready") return "warn";
  return "info";
}

export function CampaignLaunchWizardPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<CampaignSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(true);
  const [saving, setSaving] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [lastSubmit, setLastSubmit] = useState<SubmitResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<CampaignSnapshot>("solo-operator/campaign-launch-wizard");
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

  const saveDraft = useCallback(async () => {
    if (!snapshot) return;
    setSaving(true);
    try {
      const data = await hivePatchJson<CampaignSnapshot>("solo-operator/campaign-launch-wizard/draft", {
        brand_pack_id: snapshot.draft.brand_pack_id,
        channel: snapshot.draft.channel,
        title: snapshot.draft.title,
        body: snapshot.draft.body,
        cta: snapshot.draft.cta,
        hashtags: snapshot.draft.hashtags,
        media_url: snapshot.draft.media_url,
      });
      setSnapshot(data);
      toast.success("Draft saved");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Save failed";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  }, [snapshot]);

  const runRubric = useCallback(async () => {
    setScoring(true);
    try {
      const result = await hivePostJson<RubricRunResponse>("solo-operator/campaign-launch-wizard/rubric", {});
      toast[result.passed ? "success" : "error"](result.message);
      await load();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Rubric failed";
      toast.error(msg);
    } finally {
      setScoring(false);
    }
  }, [load]);

  const submit = useCallback(async () => {
    setSubmitting(true);
    try {
      const result = await hivePostJson<SubmitResponse>("solo-operator/campaign-launch-wizard/submit", {});
      setLastSubmit(result);
      toast[result.ok ? "success" : "error"](result.message);
      await load();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Submit failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }, [load]);

  const updateDraft = useCallback((patch: Partial<CampaignDraft>) => {
    setSnapshot((prev) =>
      prev
        ? {
            ...prev,
            draft: { ...prev.draft, ...patch },
          }
        : prev,
    );
  }, []);

  if (loading) {
    return (
      <V4Card className="mb-4 flex items-center gap-2 p-4 text-sm text-white/60">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading campaign launch wizard…
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <V4Card className="mb-4 max-lg:mb-3 border-pollen/30" id="campaign-launch-wizard">
      <V4CardHeader
        kicker="NP6 · Campaign launch"
        title="Campaign launch wizard"
        description="Brand pack → draft copy → rubric ≥75% → simulate publish."
        actions={
          <div className="flex items-center gap-2">
            <V4Badge tone="info">{snapshot.progress_pct}%</V4Badge>
            <HiveRefreshButton busy={loading} onClick={() => void load()} />
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm inline-flex items-center gap-1"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
            >
              {open ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
              {open ? "Collapse" : "Expand"}
            </button>
          </div>
        }
      />
      {open ? (
        <div className="space-y-4 px-4 pb-4">
          <ol className="grid gap-2 sm:grid-cols-2">
            {snapshot.steps.map((step) => (
              <li
                key={step.id}
                className="rounded border border-white/10 bg-white/[0.03] p-3 text-sm"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-white">{step.label}</span>
                  <V4Badge tone={stepTone(step.status)}>{step.status}</V4Badge>
                </div>
                <p className="mt-1 text-white/60">{step.detail}</p>
                {step.link ? (
                  <Link href={step.link} className="mt-1 inline-block text-xs text-[#00FFFF] hover:underline">
                    Open →
                  </Link>
                ) : null}
              </li>
            ))}
          </ol>

          <div className="grid gap-3 md:grid-cols-2">
            <label className="block text-sm">
              <span className="text-white/60">Brand pack</span>
              <select
                className="qs-input mt-1 w-full"
                value={snapshot.draft.brand_pack_id ?? ""}
                onChange={(e) => updateDraft({ brand_pack_id: e.target.value || null })}
              >
                <option value="">Select brand pack…</option>
                {snapshot.brand_packs.map((pack) => (
                  <option key={pack.id} value={pack.id} disabled={!pack.ready}>
                    {pack.label}
                    {!pack.ready ? " (not ready)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="text-white/60">Channel</span>
              <select
                className="qs-input mt-1 w-full"
                value={snapshot.draft.channel}
                onChange={(e) => updateDraft({ channel: e.target.value })}
              >
                {CHANNELS.map((ch) => (
                  <option key={ch} value={ch}>
                    {ch}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="block text-sm">
            <span className="text-white/60">Title</span>
            <input
              className="qs-input mt-1 w-full"
              value={snapshot.draft.title}
              onChange={(e) => updateDraft({ title: e.target.value })}
              placeholder="Summer launch carousel"
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Body</span>
            <textarea
              className="qs-input mt-1 min-h-[96px] w-full font-mono text-sm"
              value={snapshot.draft.body}
              onChange={(e) => updateDraft({ body: e.target.value })}
              placeholder="Primary message — simulate-first, no fabricated stats."
            />
          </label>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="block text-sm">
              <span className="text-white/60">CTA</span>
              <input
                className="qs-input mt-1 w-full"
                value={snapshot.draft.cta}
                onChange={(e) => updateDraft({ cta: e.target.value })}
                placeholder="Start free trial"
              />
            </label>
            <label className="block text-sm">
              <span className="text-white/60">Hashtags (comma-separated)</span>
              <input
                className="qs-input mt-1 w-full"
                value={snapshot.draft.hashtags.join(", ")}
                onChange={(e) =>
                  updateDraft({
                    hashtags: e.target.value
                      .split(",")
                      .map((tag) => tag.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="Queenswarm, SimulateFirst"
              />
            </label>
          </div>

          {snapshot.rubric.score != null ? (
            <p className="text-sm text-white/70">
              Rubric: {snapshot.rubric.template_name}{" "}
              <span className={snapshot.rubric.passed ? "text-[#00FF88]" : "text-[#FF3366]"}>
                {(snapshot.rubric.score * 100).toFixed(0)}%
              </span>{" "}
              (min {(snapshot.rubric.pass_threshold * 100).toFixed(0)}%)
              {snapshot.rubric.feedback ? ` — ${snapshot.rubric.feedback.slice(0, 120)}` : null}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <button type="button" className="qs-btn qs-btn--ghost" disabled={saving} onClick={() => void saveDraft()}>
              {saving ? <Loader2 className="size-4 animate-spin" /> : null}
              Save draft
            </button>
            <button type="button" className="qs-btn qs-btn--ghost" disabled={scoring} onClick={() => void runRubric()}>
              {scoring ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
              Run rubric
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--primary"
              disabled={submitting}
              onClick={() => void submit()}
            >
              {submitting ? <Loader2 className="size-4 animate-spin" /> : <Rocket className="size-4" />}
              Launch (simulate)
            </button>
          </div>

          {lastSubmit ? (
            <p className="text-sm text-[#00FF88]">
              Pack {lastSubmit.deliverable_id.slice(0, 8)}… —{" "}
              <Link href={lastSubmit.publish_queue_href} className="underline">
                publish queue
              </Link>
              {" · "}
              <Link href={lastSubmit.social_publish_href} className="underline">
                social publish
              </Link>
              {lastSubmit.simulate_ok ? " · simulate OK" : lastSubmit.simulate_message ? ` · ${lastSubmit.simulate_message}` : null}
            </p>
          ) : null}
        </div>
      ) : (
        <p className="px-4 pb-4 text-sm text-white/60">
          4 steps: brand pack · draft · rubric · simulate — {snapshot.progress_pct}% complete
        </p>
      )}
    </V4Card>
  );
}
