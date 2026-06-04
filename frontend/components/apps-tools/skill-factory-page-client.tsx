"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { DownloadIcon, GitBranchIcon, Loader2Icon, PlayIcon, RefreshCwIcon, RocketIcon, SparklesIcon, StoreIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { useSkillFactoryNav } from "@/components/apps-tools/skill-factory-nav-context";
import {
  FactoryLlmReadinessBanner,
  factoryBuildDisabled,
  type FactoryLlmReadiness,
} from "@/components/apps-tools/factory-llm-readiness-banner";
import { HarnessEvalPanel } from "@/components/apps-tools/harness-eval-panel";
import { HarnessProductLinesPanel } from "@/components/apps-tools/harness-product-lines-panel";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { SkillFactoryManualPanel } from "@/components/apps-tools/skill-factory-manual-panel";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { V4Badge, V4Card, V4CardHeader, V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import {
  navigateSkillFactoryTab,
  resolveSkillFactoryTab,
  type SkillFactoryTab,
} from "@/lib/apps-tools-routes";
import { useRouteHash } from "@/lib/hooks/use-route-hash";
import { downloadSkillExportBundle, downloadTextFile } from "@/lib/skill-export-utils";
import { supervisorSessionAgentsHref, skillFactoryForgeHref } from "@/lib/supervisor-session";
import type { HarnessEvalResult, LaunchPrepareResult, SkillExportResponse } from "@/lib/hive-types";

interface SkillFactoryPolicy {
  enabled: boolean;
  niche_seeds: string[];
  auto_build_enabled: boolean;
  auto_build_min_score: number;
  max_builds_per_week: number;
  research_cron_enabled: boolean;
  apify_deep_scrape_enabled: boolean;
  monid_listing_signals_enabled: boolean;
  monid_listing_preview_on_approve: boolean;
  monid_listing_video_preview_on_approve: boolean;
}

interface SkillOpportunityRow {
  id: string;
  niche: string;
  title: string;
  rationale: string;
  demand_score: number;
  competition_score: number;
  buildability_score: number;
  composite_score: number;
  suggested_price_eur_cents: number;
  status: string;
  supervisor_session_id: string | null;
  supervisor_session_status: string | null;
  forge_suggestion_id: string | null;
  forge_review_status?: string | null;
  tenant_skill_id: string | null;
}

const FALLBACK_STARTER_PRESETS: string[] = [
  "Cursor IDE agent skill packs for SaaS teams",
  "n8n automation templates for agencies",
  "SEO content pipeline with simulate-first guardrails",
  "competitor monitoring skill for B2B founders",
  "newsletter growth loop with verified outcomes",
  "Gumroad-ready AI workflow listing packs",
  "lead research + outreach simulate-first",
  "social content calendar with brand guardrails",
];

function opportunityStatusLabel(row: SkillOpportunityRow): string {
  if (row.status === "building") return "Building…";
  if (row.status === "awaiting_forge" && row.forge_review_status === "approved") {
    return row.tenant_skill_id ? "In Library — export or publish" : "Forge approved — syncing to Library";
  }
  if (row.status === "awaiting_forge" && row.forge_review_status === "pending") {
    return "Session done — approve forge";
  }
  if (row.status === "awaiting_forge") return "Session done — open report";
  if (row.status === "queued") return "Queued";
  if (row.status === "failed") return "Build failed";
  if (row.status === "completed") return "Completed";
  return row.status;
}

interface TenantSkillRow {
  id: string;
  slug: string;
  title: string;
  description: string;
  source: string;
  verified_at: string | null;
  github_exported_at: string | null;
  gumroad_product_id: string | null;
  gumroad_product_url: string | null;
  gumroad_published: boolean | null;
  sellable_tier: string;
  sellable_score: number;
  sellable_issues: string[];
  recommended_for_launch: boolean;
  keywords: string[];
}

interface LaunchReadiness {
  sellable_count: number;
  draft_count: number;
  rejected_count: number;
  gumroad_token_configured: boolean;
  gumroad_manual_ready: boolean;
  github_pat_configured: boolean;
  hero_niches_confirmed: boolean;
  exports_on_disk_hint: string;
}

interface SkillFactorySnapshot {
  policy: SkillFactoryPolicy;
  opportunities: SkillOpportunityRow[];
  library: TenantSkillRow[];
  launch_queue: TenantSkillRow[];
  launch_near_miss: TenantSkillRow[];
  launch_readiness: LaunchReadiness | null;
  queue_count: number;
  building_count: number;
  research_keys_configured: boolean;
  external_intel_enabled: boolean;
  apify_connector_ready: boolean;
  monid_connector_ready: boolean;
  github_pr_export_ready: boolean;
  gumroad_listing_ready: boolean;
  gumroad_publish_ready: boolean;
  llm: FactoryLlmReadiness | null;
}

function scorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function priceEur(cents: number): string {
  return `€${(cents / 100).toFixed(2)}`;
}

export function SkillFactoryPageClient(): JSX.Element {
  const router = useRouter();
  const routeHash = useRouteHash();
  const { setQueueBadge } = useSkillFactoryNav();
  const tab = useMemo(() => resolveSkillFactoryTab({ hash: routeHash }), [routeHash]);
  const [snapshot, setSnapshot] = useState<SkillFactorySnapshot | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [researchBusy, setResearchBusy] = useState(false);
  const [policyDraft, setPolicyDraft] = useState<SkillFactoryPolicy | null>(null);
  const [nicheInput, setNicheInput] = useState("");
  const [verticalSeeds, setVerticalSeeds] = useState<string[]>(FALLBACK_STARTER_PRESETS);
  const [starterSeeds, setStarterSeeds] = useState<string[]>(FALLBACK_STARTER_PRESETS);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await hiveGet<SkillFactorySnapshot>("skill-factory/snapshot");
      setSnapshot(data);
      setPolicyDraft(data.policy);
    } catch (e) {
      const message = e instanceof HiveApiError ? e.message : "Skill Factory unavailable.";
      setLoadError(message);
      toast.error(message);
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void hiveGet<{ vertical: string[]; starter: string[] }>("skill-factory/vertical-seeds")
      .then((data) => {
        if (data.vertical?.length) setVerticalSeeds(data.vertical);
        if (data.starter?.length) setStarterSeeds(data.starter);
      })
      .catch(() => {
        /* fallback presets */
      });
  }, []);

  useEffect(() => {
    if (!routeHash && typeof window !== "undefined") {
      navigateSkillFactoryTab("research");
    }
  }, [routeHash]);

  useEffect(() => {
    if (!snapshot) {
      setQueueBadge(undefined);
      return;
    }
    const count = snapshot.queue_count + snapshot.building_count;
    setQueueBadge(count > 0 ? count : undefined);
  }, [setQueueBadge, snapshot]);

  const researchRows = useMemo(
    () => (snapshot?.opportunities ?? []).filter((row) => row.status === "pending"),
    [snapshot?.opportunities],
  );
  const queueRows = useMemo(
    () =>
      (snapshot?.opportunities ?? []).filter((row) =>
        ["queued", "building", "awaiting_forge", "failed"].includes(row.status),
      ),
    [snapshot?.opportunities],
  );
  const doneRows = useMemo(
    () => (snapshot?.opportunities ?? []).filter((row) => row.status === "completed"),
    [snapshot?.opportunities],
  );

  const runResearch = async (): Promise<void> => {
    setResearchBusy(true);
    try {
      const res = await hivePostJson<{
        created: number;
        builds_started: number;
        active_opportunities?: number;
      }>("skill-factory/research/run", {});
      if (res.created === 0) {
        const active = res.active_opportunities ?? queueRows.length + researchRows.length;
        toast.info("No new niches found.", {
          description:
            active > 0
              ? `${active} opportunities already in queue or building. Refresh Queue or open Sessions to review completed runs.`
              : "All configured niches were already scanned. Add niche seeds in Settings or wait for weekly cron.",
        });
      } else {
        toast.success(`Research done — ${res.created} new, ${res.builds_started} builds started.`);
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Research failed.");
    } finally {
      setResearchBusy(false);
    }
  };

  const buildOpportunity = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      const res = await hivePostJson<{ session_id: string }>(`skill-factory/opportunities/${id}/build`, {});
      toast.success("Factory build started.", { description: `Session ${res.session_id.slice(0, 8)}…` });
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Build failed.");
    } finally {
      setBusyId(null);
    }
  };

  const dismissOpportunity = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      await hivePostJson(`skill-factory/opportunities/${id}/dismiss`, {});
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Dismiss failed.");
    } finally {
      setBusyId(null);
    }
  };

  const approveForge = async (suggestionId: string, opportunityId: string): Promise<void> => {
    setBusyId(opportunityId);
    try {
      await hivePostJson(`agents/suggestions/${encodeURIComponent(suggestionId)}/review`, {
        decision: "approve",
      });
      toast.success("Skill approved — check Library tab to export GitHub pack.");
      await load();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Approve failed.";
      toast.error(msg, {
        description: msg.includes("quality_gate") || msg.includes("fallback")
          ? "Reject forge — session needs critic APPROVE + valid SKILL.md (not fallback draft)."
          : undefined,
      });
    } finally {
      setBusyId(null);
    }
  };

  const evalSkill = async (id: string, title: string): Promise<void> => {
    setBusyId(id);
    try {
      const result = await hivePostJson<HarnessEvalResult>(`skill-factory/skills/${id}/eval`, {});
      downloadTextFile(`${title.slice(0, 40).replace(/[^a-z0-9]+/gi, "-")}-EVAL_REPORT.md`, result.eval_report_md);
      toast.success(result.passed ? "Eval PASS — report downloaded" : "Eval FAIL — see report", {
        description: result.issues.slice(0, 3).join(", ") || undefined,
      });
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Eval failed.");
    } finally {
      setBusyId(null);
    }
  };

  const prepareLaunchBatch = async (): Promise<void> => {
    setBusyId("launch-prepare");
    try {
      const result = await hivePostJson<LaunchPrepareResult>("skill-factory/launch/prepare", { limit: 3 });
      if (result.exported_count > 0) {
        toast.success(`Prepared ${result.exported_count} launch pack(s).`, { description: result.message });
        downloadTextFile("LAUNCH_CHECKLIST.md", result.checklist_md);
        for (const row of result.exports) {
          await exportSkill(row.skill_id);
        }
      } else {
        toast.info(result.message, {
          description: `${result.tier_counts.draft ?? 0} drafts · ${result.tier_counts.rejected ?? 0} rejected — approve quality forges only.`,
        });
        downloadTextFile("LAUNCH_CHECKLIST.md", result.checklist_md);
      }
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Launch prepare failed.");
    } finally {
      setBusyId(null);
    }
  };

  const exportSkill = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      const bundle = await hivePostJson<SkillExportResponse>(`skill-factory/skills/${id}/export`, {});
      await downloadSkillExportBundle(bundle);
      toast.success("GitHub pack downloaded.");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Export failed.");
    } finally {
      setBusyId(null);
    }
  };

  const pushGithubPr = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      const res = await hivePostJson<{ branch: string; pr: { status: string } }>(
        `skill-factory/skills/${id}/export/github-pr`,
        {},
      );
      toast.success("GitHub PR opened.", {
        description: `Branch ${res.branch} — review and merge manually.`,
      });
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "GitHub PR failed.");
    } finally {
      setBusyId(null);
    }
  };

  const createGumroadDraft = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      const res = await hivePostJson<{ product_url: string | null; edit_url: string }>(
        `skill-factory/skills/${id}/export/gumroad-draft`,
        {},
      );
      toast.success("Gumroad draft created.", {
        description: res.product_url ?? "Open Gumroad products to finish listing.",
      });
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Gumroad draft failed.");
    } finally {
      setBusyId(null);
    }
  };

  const publishGumroadListing = async (id: string, createIfMissing: boolean): Promise<void> => {
    setBusyId(id);
    try {
      const res = await hivePostJson<{ short_url: string; published: boolean }>(
        `skill-factory/skills/${id}/export/gumroad-publish`,
        { create_if_missing: createIfMissing },
      );
      toast.success("Gumroad listing published.", {
        description: res.short_url || "Product is live on Gumroad.",
      });
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Gumroad publish failed.");
    } finally {
      setBusyId(null);
    }
  };

  const savePolicy = async (): Promise<void> => {
    if (!policyDraft) return;
    setBusyId("policy");
    try {
      const saved = await hivePutJson<SkillFactoryPolicy>("skill-factory/policy", policyDraft);
      setPolicyDraft(saved);
      setSnapshot((prev) => (prev ? { ...prev, policy: saved } : prev));
      toast.success("Policy saved.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Save failed.");
    } finally {
      setBusyId(null);
    }
  };

  const buildBlocked = factoryBuildDisabled(snapshot?.llm);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-(--qs-text)">Skill Factory</p>
          <p className="mt-0.5 text-xs text-(--qs-text-3)">
            Research → build → export Verified Niche Harness packs (SKILL + HARNESS + EVAL + TOOLS). Sell on Gumroad — not in-app.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/manual#skill-factory" className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5">
            Manual
          </Link>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-2" onClick={() => void load()}>
            <RefreshCwIcon className="size-4" aria-hidden />
            Refresh
          </button>
          <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm">
            Sessions
          </Link>
          <Link href="/settings/llm-keys" className="qs-btn qs-btn--ghost qs-btn--sm">
            LLM keys
          </Link>
        </div>
      </div>

      {loading ? (
        <p className="mt-6 flex items-center gap-2 text-sm text-(--qs-muted)">
          <Loader2Icon className="size-4 animate-spin" aria-hidden />
          Loading Skill Factory…
        </p>
      ) : !snapshot ? (
        <V4Card className="mt-4">
          <p className="text-sm text-(--qs-text-3)">
            {loadError ?? "Skill Factory is disabled or unavailable."}
          </p>
          {loadError ? (
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm mt-3" onClick={() => void load()}>
              Retry
            </button>
          ) : null}
        </V4Card>
      ) : (
        <>
          {tab === "guide" ? <SkillFactoryManualPanel /> : null}

          {tab === "research" ? (
            <>
            <FactoryLlmReadinessBanner
              llm={snapshot.llm}
              onSmoked={(next) => setSnapshot((prev) => (prev ? { ...prev, llm: next } : prev))}
            />
            <V4Card className="mt-4">
              <V4CardHeader
                kicker="Research lane"
                title="Market opportunities"
                description="HiveMind + forager RSS + live web (Tavily/Serper) → ranked skills. Weekly cron Mon."
                hint={sectionHintNode("skillFactoryResearch")}
              />
              {!snapshot.research_keys_configured && snapshot.external_intel_enabled ? (
                <p className="mt-2 text-xs text-(--qs-text-3)">
                  Tip: add Tavily or Serper in{" "}
                  <Link href="/settings/api-keys#research-keys" className="text-cyan underline">
                    Settings → API keys
                  </Link>{" "}
                  for live Gumroad/GitHub market signals.
                </p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm gap-2"
                  disabled={researchBusy}
                  onClick={() => void runResearch()}
                >
                  {researchBusy ? (
                    <Loader2Icon className="size-4 animate-spin" aria-hidden />
                  ) : (
                    <SparklesIcon className="size-4" aria-hidden />
                  )}
                  Run research now
                </button>
                <V4Badge tone="info">{researchRows.length} pending</V4Badge>
              </div>
              <ul className="mt-4 space-y-2">
                {researchRows.map((row) => (
                  <li
                    key={row.id}
                    className="rounded-xl border border-white/10 bg-black/25 px-3 py-3 text-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-(--qs-text)">{row.title}</p>
                        <p className="mt-1 text-xs text-(--qs-text-3)">{row.rationale}</p>
                        <div className="mt-2 flex flex-wrap gap-1">
                          <V4Chip>Demand {scorePct(row.demand_score)}</V4Chip>
                          <V4Chip>Competition {scorePct(row.competition_score)}</V4Chip>
                          <V4Chip>Build {scorePct(row.buildability_score)}</V4Chip>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        <V4Chip>{scorePct(row.composite_score)}</V4Chip>
                        <V4Chip>{priceEur(row.suggested_price_eur_cents)}</V4Chip>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                        disabled={busyId === row.id || buildBlocked}
                        title={buildBlocked ? snapshot.llm?.recommended_action : undefined}
                        onClick={() => void buildOpportunity(row.id)}
                      >
                        <PlayIcon className="size-3.5" aria-hidden />
                        Build skill
                      </button>
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        disabled={busyId === row.id}
                        onClick={() => void dismissOpportunity(row.id)}
                      >
                        <XIcon className="size-3.5" aria-hidden />
                        Dismiss
                      </button>
                    </div>
                  </li>
                ))}
                {researchRows.length === 0 ? (
                  <p className="text-xs text-(--qs-text-4)">
                    {queueRows.length > 0
                      ? `${queueRows.length} in queue — nothing pending. Open Queue or Sessions to review builds.`
                      : "No pending opportunities — run research."}
                  </p>
                ) : null}
              </ul>
            </V4Card>
            </>
          ) : null}

          {tab === "queue" ? (
            <V4Card className="mt-4">
              <V4CardHeader
                title="Build queue"
                description="Queued and in-progress factory runs."
                hint={sectionHintNode("skillFactoryQueue")}
              />
              <ul className="mt-4 space-y-2">
                {queueRows.map((row) => (
                  <li key={row.id} className="rounded-xl border border-cyan/25 bg-cyan/5 px-3 py-3 text-sm">
                    <p className="font-medium">{row.title}</p>
                    <p className="mt-1 text-xs text-(--qs-text-3)">Status: {opportunityStatusLabel(row)}</p>
                    {row.status === "awaiting_forge" ? (
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {row.tenant_skill_id ? (
                          <button
                            type="button"
                            className="qs-btn qs-btn--primary qs-btn--sm"
                            onClick={() => navigateSkillFactoryTab("library")}
                          >
                            Open Library
                          </button>
                        ) : row.forge_suggestion_id ? (
                          <button
                            type="button"
                            className="qs-btn qs-btn--primary qs-btn--sm"
                            disabled={busyId === row.id}
                            onClick={() => void approveForge(row.forge_suggestion_id!, row.id)}
                          >
                            Approve skill
                          </button>
                        ) : row.forge_review_status === "approved" ? (
                          <button
                            type="button"
                            className="qs-btn qs-btn--primary qs-btn--sm"
                            disabled={busyId === row.id}
                            onClick={() => void load()}
                          >
                            Sync to Library
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="qs-btn qs-btn--primary qs-btn--sm"
                            onClick={() => router.push(skillFactoryForgeHref())}
                          >
                            Open forge lane
                          </button>
                        )}
                        {row.forge_suggestion_id ? (
                          <button
                            type="button"
                            className="text-xs text-pollen underline"
                            onClick={() => router.push(skillFactoryForgeHref())}
                          >
                            Review in Integrations →
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                    {row.supervisor_session_id ? (
                      <Link
                        href={supervisorSessionAgentsHref(row.supervisor_session_id)}
                        className="mt-2 inline-block text-xs text-cyan underline"
                      >
                        Open session report → {row.supervisor_session_id.slice(0, 8)}…
                      </Link>
                    ) : null}
                  </li>
                ))}
                {queueRows.length === 0 ? (
                  <p className="text-xs text-(--qs-text-4)">Queue empty.</p>
                ) : null}
              </ul>
              {doneRows.length > 0 ? (
                <p className="mt-4 text-xs text-(--qs-text-3)">
                  {doneRows.length} factory run{doneRows.length === 1 ? "" : "s"} completed
                  {" · "}
                  {(snapshot.library ?? []).length} skill{(snapshot.library ?? []).length === 1 ? "" : "s"} in Library
                  {" — "}
                  each run should map to one library row; open Library to export.
                </p>
              ) : null}
            </V4Card>
          ) : null}

          {tab === "library" ? (
            <V4Card className="mt-4">
              <V4CardHeader
                title="Tenant skill library"
                description={`${(snapshot.library ?? []).length} active skill${(snapshot.library ?? []).length === 1 ? "" : "s"} — each verified skill is available to all swarm sessions via SkillLibrary.`}
                hint={sectionHintNode("skillFactoryLibrary")}
              />
              <ul className="mt-4 space-y-2">
                {(snapshot.library ?? []).map((row) => (
                  <li key={row.id} className="rounded-xl border border-pollen/25 bg-pollen/5 px-3 py-3 text-sm">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">{row.title}</p>
                        <p className="mt-1 font-mono text-[10px] text-pollen">{row.slug}</p>
                        {row.description ? (
                          <p className="mt-1 text-xs text-(--qs-text-3)">{row.description.slice(0, 200)}</p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <V4Badge tone={row.sellable_tier === "sellable" ? "ok" : row.sellable_tier === "draft" ? "info" : "warn"}>
                          {row.sellable_tier} · {scorePct(row.sellable_score)}
                        </V4Badge>
                        <V4Badge tone={row.github_exported_at ? "ok" : "info"}>
                          {row.github_exported_at ? "exported" : "ready"}
                        </V4Badge>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                        disabled={busyId === row.id}
                        onClick={() => void evalSkill(row.id, row.title)}
                      >
                        <SparklesIcon className="size-3.5" aria-hidden />
                        Run eval
                      </button>
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                        disabled={busyId === row.id}
                        onClick={() => void exportSkill(row.id)}
                      >
                        <DownloadIcon className="size-3.5" aria-hidden />
                        Download GitHub pack
                      </button>
                      {snapshot.github_pr_export_ready ? (
                        <button
                          type="button"
                          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                          disabled={busyId === row.id}
                          onClick={() => void pushGithubPr(row.id)}
                        >
                          <GitBranchIcon className="size-3.5" aria-hidden />
                          Push GitHub PR
                        </button>
                      ) : null}
                      {snapshot.gumroad_listing_ready ? (
                        <button
                          type="button"
                          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                          disabled={busyId === row.id}
                          onClick={() => void createGumroadDraft(row.id)}
                        >
                          <StoreIcon className="size-3.5" aria-hidden />
                          Gumroad draft
                        </button>
                      ) : null}
                      {snapshot.gumroad_publish_ready ? (
                        <button
                          type="button"
                          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                          disabled={busyId === row.id || row.gumroad_published === true}
                          onClick={() =>
                            void publishGumroadListing(row.id, !row.gumroad_product_id)
                          }
                        >
                          <RocketIcon className="size-3.5" aria-hidden />
                          {row.gumroad_published ? "Published" : row.gumroad_product_id ? "Gumroad publish" : "Gumroad publish (draft+live)"}
                        </button>
                      ) : null}
                      {row.gumroad_product_url ? (
                        <a
                          href={row.gumroad_product_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                        >
                          <StoreIcon className="size-3.5" aria-hidden />
                          Open Gumroad
                        </a>
                      ) : null}
                    </div>
                  </li>
                ))}
                {snapshot.library.length === 0 ? (
                  <p className="text-xs text-(--qs-text-4)">
                    No tenant skills yet — approve a completed build with{" "}
                    <strong className="text-(--qs-text-2)">Approve skill</strong> in the Queue tab, then export here.
                  </p>
                ) : null}
              </ul>
            </V4Card>
          ) : null}

          {tab === "launch" ? (
            <>
            <HarnessProductLinesPanel />
            <HarnessEvalPanel />
            <V4Card className="mt-4">
              <V4CardHeader
                title="Launch queue"
                description="Hero products ready for Gumroad — manual upload works without API token or your own website."
                hint={sectionHintNode("skillFactoryLaunch")}
              />
              {snapshot.launch_readiness ? (
                <ul className="mt-3 space-y-2 text-xs text-(--qs-text-3)">
                  <li className="flex flex-wrap items-center gap-2">
                    <V4Badge tone={snapshot.launch_readiness.sellable_count >= 3 ? "ok" : "info"}>
                      {snapshot.launch_readiness.sellable_count} sellable
                    </V4Badge>
                    <span>{snapshot.launch_readiness.draft_count} drafts · {snapshot.launch_readiness.rejected_count} rejected</span>
                  </li>
                  <li>
                    Gumroad token (optional API drafts):{" "}
                    {snapshot.launch_readiness.gumroad_token_configured ? (
                      <span className="text-success">configured</span>
                    ) : (
                      <span>
                        not set —{" "}
                        <Link href="/apps-tools/skill-factory#guide" className="text-cyan underline">
                          Guide tab + GUMROAD_SETUP_SK.md
                        </Link>
                      </span>
                    )}
                  </li>
                  <li>
                    GitHub PAT (optional teaser repos):{" "}
                    {snapshot.launch_readiness.github_pat_configured ? (
                      <span className="text-success">ready</span>
                    ) : (
                      <span className="text-(--qs-text-4)">optional — connect in Integrations</span>
                    )}
                  </li>
                  <li>
                    Hero niches (Settings seeds):{" "}
                    {snapshot.launch_readiness.hero_niches_confirmed ? (
                      <span className="text-success">3+ configured</span>
                    ) : (
                      <button
                        type="button"
                        className="text-cyan underline"
                        onClick={() => navigateSkillFactoryTab("settings")}
                      >
                        add niche seeds
                      </button>
                    )}
                  </li>
                  <li className="font-mono text-[10px] text-(--qs-text-4)">
                    Server bundles: {snapshot.launch_readiness.exports_on_disk_hint}
                  </li>
                </ul>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-2 px-4 pb-4">
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                  disabled={busyId === "launch-prepare"}
                  onClick={() => void prepareLaunchBatch()}
                >
                  {busyId === "launch-prepare" ? (
                    <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                  ) : (
                    <RocketIcon className="size-3.5" aria-hidden />
                  )}
                  Prepare launch batch
                </button>
              </div>
              <ul className="mt-2 space-y-2">
                {(snapshot.launch_queue ?? []).map((row) => (
                  <li key={row.id} className="rounded-xl border border-success/30 bg-success/5 px-3 py-3 text-sm">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">{row.title}</p>
                        <p className="mt-1 font-mono text-[10px] text-pollen">{row.slug}.tar.gz</p>
                        {row.sellable_issues.length > 0 ? (
                          <p className="mt-1 text-[10px] text-(--qs-text-4)">
                            Notes: {row.sellable_issues.join(", ")}
                          </p>
                        ) : null}
                      </div>
                      <V4Badge tone="ok">launch · {scorePct(row.sellable_score)}</V4Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                        disabled={busyId === row.id}
                        onClick={() => void exportSkill(row.id)}
                      >
                        <DownloadIcon className="size-3.5" aria-hidden />
                        Download pack
                      </button>
                      {snapshot.gumroad_listing_ready ? (
                        <button
                          type="button"
                          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                          disabled={busyId === row.id}
                          onClick={() => void createGumroadDraft(row.id)}
                        >
                          <StoreIcon className="size-3.5" aria-hidden />
                          API draft
                        </button>
                      ) : (
                        <a
                          href="https://gumroad.com/products/new"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                        >
                          <StoreIcon className="size-3.5" aria-hidden />
                          Manual Gumroad upload
                        </a>
                      )}
                    </div>
                  </li>
                ))}
                {(snapshot.launch_queue ?? []).length === 0 ? (
                  <div className="space-y-3 text-xs text-(--qs-text-4)">
                    <p>
                      No sellable skills yet — most factory drafts need critic APPROVE + valid SKILL.md.
                      {snapshot.building_count > 0 ? (
                        <span className="text-cyan"> {snapshot.building_count} builds in progress…</span>
                      ) : null}
                    </p>
                    {(snapshot.launch_near_miss ?? []).length > 0 ? (
                      <div>
                        <p className="font-medium text-(--qs-text-3)">Closest to launch (draft tier)</p>
                        <ul className="mt-2 space-y-2">
                          {(snapshot.launch_near_miss ?? []).map((row) => (
                            <li key={row.id} className="rounded-lg border border-(--qs-border-2) px-3 py-2">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="font-medium text-(--qs-text-2)">{row.title}</span>
                                <V4Badge tone="info">{scorePct(row.sellable_score)}</V4Badge>
                              </div>
                              {row.sellable_issues.length > 0 ? (
                                <p className="mt-1 font-mono text-[10px]">fix: {row.sellable_issues.join(", ")}</p>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                        <button
                          type="button"
                          className="mt-2 text-cyan underline"
                          onClick={() => navigateSkillFactoryTab("library")}
                        >
                          Open Library → rebuild or approve forge
                        </button>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </ul>
            </V4Card>
            </>
          ) : null}

          {tab === "settings" && policyDraft ? (
            <V4Card className="mt-4 space-y-4">
              <V4CardHeader
                title="Automation"
                description="Minimal operator input — research cron + optional auto-build."
                hint={sectionHintNode("skillFactorySettings")}
              />
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Factory enabled</span>
                <HiveSwitch checked={policyDraft.enabled} onCheckedChange={(v) => setPolicyDraft({ ...policyDraft, enabled: v })} />
              </label>
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Weekly research cron (Mon)</span>
                <HiveSwitch
                  checked={policyDraft.research_cron_enabled}
                  onCheckedChange={(v) => setPolicyDraft({ ...policyDraft, research_cron_enabled: v })}
                />
              </label>
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Auto-build when score ≥ threshold</span>
                <HiveSwitch
                  checked={policyDraft.auto_build_enabled}
                  onCheckedChange={(v) => setPolicyDraft({ ...policyDraft, auto_build_enabled: v })}
                />
              </label>
              <label className="block text-sm">
                <span className="text-(--qs-text-3)">Auto-build min score (0–1)</span>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  className="qs-input mt-1 w-full max-w-xs"
                  value={policyDraft.auto_build_min_score}
                  onChange={(e) =>
                    setPolicyDraft({
                      ...policyDraft,
                      auto_build_min_score: Number.parseFloat(e.target.value) || 0.72,
                    })
                  }
                />
              </label>
              <label className="block text-sm">
                <span className="text-(--qs-text-3)">Max builds per week</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  className="qs-input mt-1 w-full max-w-xs"
                  value={policyDraft.max_builds_per_week}
                  onChange={(e) =>
                    setPolicyDraft({
                      ...policyDraft,
                      max_builds_per_week: Number.parseInt(e.target.value, 10) || 10,
                    })
                  }
                />
                <p className="mt-1 max-w-md text-xs text-(--qs-text-4)">
                  Quality guardrail — target 3–5 sellable harness launches per month, not volume drafts.
                  Verified skills load into tenant SkillLibrary for every swarm session.
                </p>
              </label>
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Apify deep scrape (uses credits — max 1/run)</span>
                <HiveSwitch
                  checked={policyDraft.apify_deep_scrape_enabled}
                  disabled={!snapshot.apify_connector_ready}
                  onCheckedChange={(v) => setPolicyDraft({ ...policyDraft, apify_deep_scrape_enabled: v })}
                />
              </label>
              {!snapshot.apify_connector_ready ? (
                <p className="text-xs text-(--qs-text-4)">
                  Connect Apify in{" "}
                  <Link href="/integrations?tab=hub" className="text-cyan underline">
                    Integrations → Hub
                  </Link>{" "}
                  (slug <code className="font-mono text-[10px]">apify_store</code>) to enable Gumroad/GitHub scrape.
                </p>
              ) : policyDraft.apify_deep_scrape_enabled ? (
                <p className="text-xs text-(--qs-text-3)">
                  Deep scrape runs Google Search via Apify on the first new niche each research run.
                </p>
              ) : null}
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Monid listing signals (discover — pay per call)</span>
                <HiveSwitch
                  checked={policyDraft.monid_listing_signals_enabled}
                  disabled={!snapshot.monid_connector_ready}
                  onCheckedChange={(v) => setPolicyDraft({ ...policyDraft, monid_listing_signals_enabled: v })}
                />
              </label>
              {!snapshot.monid_connector_ready ? (
                <p className="text-xs text-(--qs-text-4)">
                  Connect Monid in{" "}
                  <Link href="/integrations?tab=hub" className="text-cyan underline">
                    Integrations → Hub
                  </Link>{" "}
                  (slug <code className="font-mono text-[10px]">monid_mcp</code>) for Gumroad/TikTok listing endpoint hints.
                </p>
              ) : policyDraft.monid_listing_signals_enabled ? (
                <p className="text-xs text-(--qs-text-3)">
                  Monid discover finds marketplace/listing endpoints — max 1 call per research run. Factory LISTING.md
                  will include video preview notes when relevant.
                </p>
              ) : null}
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Monid listing preview on approve</span>
                <HiveSwitch
                  checked={policyDraft.monid_listing_preview_on_approve}
                  disabled={!snapshot.monid_connector_ready}
                  onCheckedChange={(v) =>
                    setPolicyDraft({ ...policyDraft, monid_listing_preview_on_approve: v })
                  }
                />
              </label>
              {policyDraft.monid_listing_preview_on_approve && snapshot.monid_connector_ready ? (
                <p className="text-xs text-(--qs-text-3)">
                  On Approve skill, Monid discover enriches Gumroad hook in LISTING.md export (1 call per approve).
                </p>
              ) : null}
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Monid video preview on approve (run — pay per call)</span>
                <HiveSwitch
                  checked={policyDraft.monid_listing_video_preview_on_approve}
                  disabled={!snapshot.monid_connector_ready || !policyDraft.monid_listing_preview_on_approve}
                  onCheckedChange={(v) =>
                    setPolicyDraft({ ...policyDraft, monid_listing_video_preview_on_approve: v })
                  }
                />
              </label>
              {policyDraft.monid_listing_video_preview_on_approve && snapshot.monid_connector_ready ? (
                <p className="text-xs text-(--qs-text-3)">
                  Generates a 15s Gumroad teaser URL via Monid run — stored in LISTING.md export. Requires Execution
                  Studio + server flag <code className="font-mono text-[10px]">SKILL_FACTORY_MONID_VIDEO_PREVIEW_ENABLED</code>.
                </p>
              ) : null}
              <label className="block text-sm">
                <span className="text-(--qs-text-3)">Niche seeds (max 12)</span>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() =>
                      setPolicyDraft({
                        ...policyDraft,
                        niche_seeds: starterSeeds.slice(0, 8),
                      })
                    }
                  >
                    Apply vertical starter
                  </button>
                </div>
                <div className="mt-1 flex flex-wrap gap-2">
                  {verticalSeeds.slice(0, 6).map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--xs"
                      onClick={() =>
                        setPolicyDraft({
                          ...policyDraft,
                          niche_seeds: [...new Set([...policyDraft.niche_seeds, preset])].slice(0, 12),
                        })
                      }
                    >
                      + {preset.slice(0, 36)}…
                    </button>
                  ))}
                </div>
                <div className="mt-1 flex flex-wrap gap-2">
                  <input
                    className="qs-input min-w-[12rem] flex-1"
                    placeholder="e.g. newsletter growth automation"
                    value={nicheInput}
                    onChange={(e) => setNicheInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key !== "Enter") return;
                      e.preventDefault();
                      const next = nicheInput.trim();
                      if (!next) return;
                      setPolicyDraft({
                        ...policyDraft,
                        niche_seeds: [...policyDraft.niche_seeds, next].slice(0, 12),
                      });
                      setNicheInput("");
                    }}
                  />
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => {
                      const next = nicheInput.trim();
                      if (!next) return;
                      setPolicyDraft({
                        ...policyDraft,
                        niche_seeds: [...policyDraft.niche_seeds, next].slice(0, 12),
                      });
                      setNicheInput("");
                    }}
                  >
                    Add
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {policyDraft.niche_seeds.map((seed) => (
                    <button
                      key={seed}
                      type="button"
                      className="inline-flex items-center gap-1"
                      onClick={() =>
                        setPolicyDraft({
                          ...policyDraft,
                          niche_seeds: policyDraft.niche_seeds.filter((item) => item !== seed),
                        })
                      }
                      title="Remove seed"
                    >
                      <V4Chip>
                        {seed}
                        <XIcon className="ml-1 size-3 opacity-60" aria-hidden />
                      </V4Chip>
                    </button>
                  ))}
                </div>
              </label>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm"
                disabled={busyId === "policy"}
                onClick={() => void savePolicy()}
              >
                Save policy
              </button>
            </V4Card>
          ) : null}
        </>
      )}
    </div>
  );
}
