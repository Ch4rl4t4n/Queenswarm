"use client";

import Link from "next/link";
import { DownloadIcon, GitBranchIcon, Loader2Icon, PlayIcon, RefreshCwIcon, RocketIcon, SparklesIcon, StoreIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { useSkillFactoryNav } from "@/components/apps-tools/skill-factory-nav-context";
import {
  FactoryQueueSloPanel,
  type FactoryQueueSlo,
} from "@/components/apps-tools/factory-queue-slo-panel";
import {
  FactoryLlmReadinessBanner,
  factoryBuildDisabled,
  type FactoryLlmReadiness,
} from "@/components/apps-tools/factory-llm-readiness-banner";
import {
  FactoryLibrarySkillCard,
  type InlineEvalResult,
} from "@/components/apps-tools/factory-library-skill-card";
import {
  FactoryQueueTaskCard,
  isStuckFactoryBuild,
} from "@/components/apps-tools/factory-queue-task-card";
import { HarnessEvalPanel } from "@/components/apps-tools/harness-eval-panel";
import { HarnessProductLinesPanel } from "@/components/apps-tools/harness-product-lines-panel";
import { AgentSessionReportDialog } from "@/components/hive/agent-session-report-dialog";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { SkillFactoryManualPanel } from "@/components/apps-tools/skill-factory-manual-panel";
import { SkillFactoryRevenueFunnelPanel } from "@/components/apps-tools/skill-factory-revenue-funnel-panel";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, V4Card, V4CardHeader, V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import { usePlatform } from "@/components/hive/platform-context";
import {
  LIBRARY_SIEVE_LABELS,
  type LibrarySieveVerdict,
} from "@/lib/sellable-issue-labels";
import {
  navigateSkillFactoryTab,
  resolveSkillFactoryTab,
  type SkillFactoryTab,
} from "@/lib/apps-tools-routes";
import { cn } from "@/lib/utils";
import { useRouteHash } from "@/lib/hooks/use-route-hash";
import { useRouteHashScroll } from "@/lib/hooks/use-route-hash-scroll";
import { downloadSkillExportBundle, downloadTextFile } from "@/lib/skill-export-utils";
import type { FactoryProductPreset, HarnessEvalResult, LaunchPrepareResult, SkillExportResponse } from "@/lib/hive-types";

interface SkillFactoryPolicy {
  enabled: boolean;
  niche_seeds: string[];
  auto_build_enabled: boolean;
  auto_build_min_score: number;
  auto_queue_drain_enabled?: boolean;
  auto_rebuild_failed_forges?: boolean;
  auto_approve_passing_forges?: boolean;
  max_concurrent_builds?: number;
  drain_batch_per_tick?: number;
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
  supervisor_session_error?: string | null;
  forge_suggestion_id: string | null;
  forge_review_status?: string | null;
  forge_quality_passed?: boolean | null;
  forge_critic_approved?: boolean | null;
  forge_issues?: string[];
  progress_phase?: string;
  progress_label?: string;
  progress_detail?: string | null;
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
  factory_disposition: string | null;
  factory_attempt_count: number;
  factory_disposition_note: string | null;
  library_verdict: string | null;
  library_verdict_reason: string | null;
  library_verdict_action: string | null;
  purge_eligible?: boolean;
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

interface SkillFactoryOpportunityCounts {
  pending: number;
  queued: number;
  building: number;
  awaiting_forge: number;
  failed: number;
  completed: number;
  dismissed: number;
  total: number;
  actionable: number;
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
  failed_count?: number;
  actionable_count?: number;
  opportunity_counts?: SkillFactoryOpportunityCounts | null;
  opportunities_truncated?: boolean;
  research_keys_configured: boolean;
  external_intel_enabled: boolean;
  apify_connector_ready: boolean;
  monid_connector_ready: boolean;
  github_pr_export_ready: boolean;
  gumroad_listing_ready: boolean;
  gumroad_publish_ready: boolean;
  commercial_launch_enabled?: boolean;
  library_duplicates_hidden?: number;
  library_purge_eligible?: number;
  llm: FactoryLlmReadiness | null;
  queue_slo?: FactoryQueueSlo | null;
}

function scorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

function priceEur(cents: number): string {
  return `€${(cents / 100).toFixed(2)}`;
}

const LIBRARY_PREVIEW_LIMIT = 5;

function isLibrarySmartRebuildEligible(row: TenantSkillRow): boolean {
  return (
    (row.sellable_tier === "rejected" || row.sellable_tier === "draft")
    && row.factory_disposition !== "retired"
  );
}

export function SkillFactoryPageClient(): JSX.Element {
  const routeHash = useRouteHash();
  useRouteHashScroll();
  const { personalOsMode } = usePlatform();
  const { setQueueBadge } = useSkillFactoryNav();
  const tab = useMemo(
    () => resolveSkillFactoryTab({ hash: routeHash, personalOsMode }),
    [personalOsMode, routeHash],
  );
  const [snapshot, setSnapshot] = useState<SkillFactorySnapshot | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [researchBusy, setResearchBusy] = useState(false);
  const [policyDraft, setPolicyDraft] = useState<SkillFactoryPolicy | null>(null);
  const [nicheInput, setNicheInput] = useState("");
  const [verticalSeeds, setVerticalSeeds] = useState<string[]>(FALLBACK_STARTER_PRESETS);
  const [starterSeeds, setStarterSeeds] = useState<string[]>(FALLBACK_STARTER_PRESETS);
  const [productPresets, setProductPresets] = useState<FactoryProductPreset[]>([]);
  const [sessionReportId, setSessionReportId] = useState<string | null>(null);
  const [librarySieve, setLibrarySieve] = useState<LibrarySieveVerdict>("all");
  const [libraryQuery, setLibraryQuery] = useState("");
  const [showAllLibrary, setShowAllLibrary] = useState(false);
  const [inlineEvalBySkill, setInlineEvalBySkill] = useState<Record<string, InlineEvalResult>>({});
  const [evalReportCache, setEvalReportCache] = useState<Record<string, string>>({});
  const [libraryRebuildQueued, setLibraryRebuildQueued] = useState<Set<string>>(() => new Set());

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

  const refreshSnapshotQuiet = useCallback(async () => {
    try {
      const data = await hiveGet<SkillFactorySnapshot>("skill-factory/snapshot");
      setSnapshot(data);
      setPolicyDraft(data.policy);
    } catch {
      /* queue poll — ignore transient errors */
    }
  }, []);

  const refreshAfterQueueAction = useCallback(async (): Promise<void> => {
    await refreshSnapshotQuiet();
  }, [refreshSnapshotQuiet]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setShowAllLibrary(false);
  }, [libraryQuery, librarySieve, snapshot?.library?.length]);

  useEffect(() => {
    void hiveGet<{ vertical: string[]; starter: string[]; product_presets?: FactoryProductPreset[] }>(
      "skill-factory/vertical-seeds",
    )
      .then((data) => {
        if (data.vertical?.length) setVerticalSeeds(data.vertical);
        if (data.starter?.length) setStarterSeeds(data.starter);
        if (data.product_presets?.length) setProductPresets(data.product_presets);
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
    const visibleQueue = snapshot.opportunities.filter((row) =>
      ["queued", "building", "awaiting_forge", "failed"].includes(row.status),
    ).length;
    const dbActionable =
      snapshot.opportunity_counts?.actionable
      ?? snapshot.actionable_count
      ?? snapshot.queue_count + snapshot.building_count + (snapshot.failed_count ?? 0);
    const count = Math.max(dbActionable, visibleQueue);
    setQueueBadge(count > 0 ? count : undefined);
  }, [setQueueBadge, snapshot]);

  const drainQueue = useCallback(async (): Promise<void> => {
    try {
      const res = await hivePostJson<{
        approved: number;
        rebuilt: number;
        started: number;
        skipped_cap: number;
        errors?: string[];
      }>("skill-factory/queue/drain", {});
      const moved = (res.approved ?? 0) + (res.rebuilt ?? 0) + (res.started ?? 0);
      if (moved > 0) {
        await refreshAfterQueueAction();
      }
      if ((res.errors?.length ?? 0) > 0) {
        toast.warning(`Queue drain: ${res.errors?.[0] ?? "blocked"}`, {
          description:
            res.errors?.length && res.errors.length > 1
              ? `${res.errors.length} items blocked — check Settings → throughput`
              : undefined,
        });
      }
      if ((res.skipped_cap ?? 0) > 0 && moved === 0) {
        toast.info("Weekly build cap reached — raise max_builds_per_week in Settings.");
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Queue drain failed.");
    }
  }, [refreshAfterQueueAction]);

  useEffect(() => {
    if (tab !== "queue") {
      return;
    }
    void drainQueue();
    const hasStuckForge = (snapshot?.opportunities ?? []).some(
      (row) => row.status === "awaiting_forge" && row.forge_quality_passed === false,
    );
    const pollMs = snapshot?.building_count ? 8_000 : hasStuckForge ? 20_000 : 45_000;
    const timer = window.setInterval(() => {
      void drainQueue();
      void refreshSnapshotQuiet();
    }, pollMs);
    return () => window.clearInterval(timer);
  }, [tab, snapshot?.building_count, drainQueue, refreshSnapshotQuiet]);

  const researchRows = useMemo(
    () => (snapshot?.opportunities ?? []).filter((row) => row.status === "pending"),
    [snapshot?.opportunities],
  );
  const queueRows = useMemo(() => {
    const statusRank: Record<string, number> = {
      building: 0,
      awaiting_forge: 1,
      failed: 2,
      queued: 3,
    };
    return (snapshot?.opportunities ?? [])
      .filter((row) => ["queued", "building", "awaiting_forge", "failed"].includes(row.status))
      .sort((a, b) => {
        const rank = (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9);
        if (rank !== 0) return rank;
        return (b.composite_score ?? 0) - (a.composite_score ?? 0);
      });
  }, [snapshot?.opportunities]);
  const doneRows = useMemo(
    () => (snapshot?.opportunities ?? []).filter((row) => row.status === "completed"),
    [snapshot?.opportunities],
  );

  const librarySieveCounts = useMemo(() => {
    const counts: Record<LibrarySieveVerdict, number> = {
      all: snapshot?.library?.length ?? 0,
      launch: 0,
      worth_retry: 0,
      deprioritize: 0,
      retire: 0,
    };
    for (const row of snapshot?.library ?? []) {
      const v = row.library_verdict as Exclude<LibrarySieveVerdict, "all"> | null;
      if (v && v in counts) {
        counts[v] += 1;
      }
    }
    return counts;
  }, [snapshot?.library]);

  const filteredLibraryRows = useMemo(() => {
    const rows = snapshot?.library ?? [];
    if (librarySieve === "all") {
      return rows;
    }
    return rows.filter((row) => row.library_verdict === librarySieve);
  }, [snapshot?.library, librarySieve]);

  const searchedLibraryRows = useMemo(() => {
    const q = libraryQuery.trim().toLowerCase();
    if (!q) {
      return filteredLibraryRows;
    }
    return filteredLibraryRows.filter((row) => {
      const haystack = [
        row.title,
        row.slug,
        row.description,
        row.library_verdict ?? "",
        row.library_verdict_reason ?? "",
        ...row.sellable_issues,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [filteredLibraryRows, libraryQuery]);

  const visibleLibraryRows = useMemo(() => {
    if (showAllLibrary) {
      return searchedLibraryRows;
    }
    return searchedLibraryRows.slice(0, LIBRARY_PREVIEW_LIMIT);
  }, [searchedLibraryRows, showAllLibrary]);

  const hiddenLibraryCount = Math.max(0, searchedLibraryRows.length - LIBRARY_PREVIEW_LIMIT);

  const libraryRebuildEligible = useMemo(
    () => (snapshot?.library ?? []).filter(isLibrarySmartRebuildEligible),
    [snapshot?.library],
  );

  const sellableLibraryCount = useMemo(
    () => (snapshot?.library ?? []).filter((row) => row.sellable_tier === "sellable").length,
    [snapshot?.library],
  );

  const runResearch = async (): Promise<void> => {
    setResearchBusy(true);
    try {
      const res = await hivePostJson<{
        created: number;
        builds_started: number;
        active_opportunities?: number;
        failed_count?: number;
        pending_count?: number;
        queued_count?: number;
        building_count?: number;
      }>("skill-factory/research/run", {});
      if (res.created === 0) {
        const active = res.active_opportunities ?? snapshot?.actionable_count ?? queueRows.length;
        const failed = res.failed_count ?? snapshot?.failed_count ?? 0;
        toast.info("No new niches — seeds already covered.", {
          description:
            failed > 0
              ? `${active} actionable (${failed} failed) — open Queue tab: Rebuild or Clear failed.`
              : active > 0
                ? `${active} already in pipeline — manage inline on Queue tab.`
                : "Add niche seeds in Settings or wait for weekly cron.",
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
      await refreshAfterQueueAction();
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
      await refreshAfterQueueAction();
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
      toast.success("Skill approved — check Library tab to export harness pack.");
      await refreshAfterQueueAction();
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

  const smartRebuildSkill = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      const res = await hivePostJson<{
        session_id: string;
        opportunity_id: string;
        attempt_count: number;
        fix_lines: string[];
      }>(`skill-factory/skills/${id}/smart-rebuild`, {});
      setLibraryRebuildQueued((prev) => new Set(prev).add(id));
      toast.success("Smart rebuild queued.", {
        description: `Attempt ${res.attempt_count} — stay in Library; open Queue when you want progress.`,
      });
      await refreshSnapshotQuiet();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Smart rebuild failed.");
    } finally {
      setBusyId(null);
    }
  };

  const removeLibrarySkill = async (id: string, title: string): Promise<void> => {
    const ok = window.confirm(
      `Remove "${title}" from library?\n\nReviewed — no launch value. You can still rebuild the niche from Research if needed.`,
    );
    if (!ok) return;
    setBusyId(id);
    try {
      await hivePostJson(`skill-factory/skills/${id}/archive`, {});
      toast.success("Removed from library.");
      await refreshSnapshotQuiet();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Remove failed.");
    } finally {
      setBusyId(null);
    }
  };

  const purgeReviewedLibrary = async (): Promise<void> => {
    const targets = searchedLibraryRows.filter((row) => row.purge_eligible);
    if (targets.length === 0) {
      toast.message("No reviewed skills eligible for removal in this view.");
      return;
    }
    const ok = window.confirm(
      `Remove ${targets.length} reviewed skill${targets.length === 1 ? "" : "s"} from library?\n\nOnly retire/deprioritize verdicts — launch-ready skills stay.`,
    );
    if (!ok) return;
    setBusyId("library-purge-reviewed");
    try {
      const res = await hivePostJson<{ archived: number; skipped: number }>(
        "skill-factory/library/purge-reviewed",
        { skill_ids: targets.map((row) => row.id) },
      );
      if (res.archived > 0) {
        toast.success(`Removed ${res.archived} skill${res.archived === 1 ? "" : "s"} from library.`, {
          description: res.skipped > 0 ? `${res.skipped} skipped (worth retry / launch).` : undefined,
        });
      } else {
        toast.message("Nothing removed — run eval or set disposition first.");
      }
      await refreshSnapshotQuiet();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Bulk remove failed.");
    } finally {
      setBusyId(null);
    }
  };

  const archiveLibraryDuplicates = async (): Promise<void> => {
    setBusyId("library-archive-dupes");
    try {
      const res = await hivePostJson<{ archived: number }>("skill-factory/library/archive-duplicates", {});
      if (res.archived > 0) {
        toast.success(`Archived ${res.archived} older duplicate${res.archived === 1 ? "" : "s"}.`, {
          description: "Library now shows one row per niche (newest version).",
        });
      } else {
        toast.message("No duplicate niche versions to archive.");
      }
      await refreshSnapshotQuiet();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Archive duplicates failed.");
    } finally {
      setBusyId(null);
    }
  };

  const smartRebuildAllLibrary = async (): Promise<void> => {
    const targets = libraryRebuildEligible;
    if (targets.length === 0) {
      toast.message("No rejected/draft skills eligible for Smart rebuild.");
      return;
    }
    setBusyId("library-rebuild-all");
    let started = 0;
    let failed = 0;
    const queued = new Set(libraryRebuildQueued);
    for (const row of targets) {
      try {
        await hivePostJson(`skill-factory/skills/${row.id}/smart-rebuild`, {});
        queued.add(row.id);
        started += 1;
      } catch {
        failed += 1;
      }
    }
    setLibraryRebuildQueued(queued);
    await refreshSnapshotQuiet();
    if (started > 0) {
      toast.success(`Smart rebuild: ${started} queued${failed > 0 ? ` · ${failed} failed (cap/retired)` : ""}.`, {
        description: "You stay in Library — factory runs appear in Queue tab.",
      });
    } else {
      toast.error(failed > 0 ? "No rebuilds started — check weekly cap or retired niches." : "Nothing to rebuild.");
    }
    setBusyId(null);
  };

  const setSkillDisposition = async (
    id: string,
    disposition: "worth_retry" | "deprioritized" | "retired",
    label: string,
  ): Promise<void> => {
    setBusyId(id);
    try {
      await hivePutJson(`skill-factory/skills/${id}/disposition`, { disposition });
      toast.success(label);
      await refreshSnapshotQuiet();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Disposition failed.");
    } finally {
      setBusyId(null);
    }
  };

  const evalSkill = async (id: string, title: string): Promise<void> => {
    setBusyId(id);
    try {
      const result = await hivePostJson<HarnessEvalResult>(`skill-factory/skills/${id}/eval`, {});
      setInlineEvalBySkill((prev) => ({
        ...prev,
        [id]: {
          passed: result.passed,
          tier: result.tier,
          score: result.score,
          issues: result.issues,
          evaluated_at: new Date().toISOString(),
        },
      }));
      setEvalReportCache((prev) => ({ ...prev, [id]: result.eval_report_md }));
      toast.success(result.passed ? "Eval PASS — keep in launch queue" : "Eval FAIL — see card verdict", {
        description: result.passed
          ? "Export harness pack when ready."
          : "Retire or Smart rebuild based on sieve banner on card.",
      });
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Eval failed.");
    } finally {
      setBusyId(null);
    }
  };

  const downloadEvalReport = async (id: string, title: string): Promise<void> => {
    let md = evalReportCache[id];
    if (!md) {
      const result = await hivePostJson<HarnessEvalResult>(`skill-factory/skills/${id}/eval`, {});
      md = result.eval_report_md;
      setEvalReportCache((prev) => ({ ...prev, [id]: md }));
      setInlineEvalBySkill((prev) => ({
        ...prev,
        [id]: {
          passed: result.passed,
          tier: result.tier,
          score: result.score,
          issues: result.issues,
          evaluated_at: new Date().toISOString(),
        },
      }));
    }
    downloadTextFile(`${title.slice(0, 40).replace(/[^a-z0-9]+/gi, "-")}-EVAL_REPORT.md`, md);
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

  const rejectForge = async (opportunityId: string, suggestionId: string): Promise<void> => {
    setBusyId(opportunityId);
    try {
      await hivePostJson(`skill-factory/opportunities/${opportunityId}/reject-forge`, {});
      toast.success("Forge rejected.");
      await refreshAfterQueueAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Reject failed.");
    } finally {
      setBusyId(null);
    }
  };

  const rebuildOpportunity = async (opportunityId: string): Promise<void> => {
    setBusyId(opportunityId);
    try {
      const res = await hivePostJson<{ session_id: string; status: string; opportunity_id: string }>(
        `skill-factory/opportunities/${opportunityId}/rebuild`,
        {},
      );
      if (res.status === "building" && res.session_id) {
        toast.success("Rebuild started.", { description: `Session ${res.session_id.slice(0, 8)}… · status building` });
      } else {
        toast.warning(`Rebuild finished with status: ${res.status || "unknown"}`, {
          description: res.session_id ? `Session ${res.session_id.slice(0, 8)}…` : "No new session id returned.",
        });
      }
      await refreshAfterQueueAction();
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Rebuild failed.";
      toast.error(msg, {
        description: msg.includes("weekly_build_cap")
          ? "Raise max_builds_per_week in Settings or wait — rebuilds should bypass cap after this deploy."
          : msg.includes("LLM") || msg.includes("smoke")
            ? "Run Factory LLM smoke test in the banner above."
            : undefined,
      });
    } finally {
      setBusyId(null);
    }
  };

  const runQueueTask = async (opportunityId: string): Promise<void> => {
    const row = (snapshot?.opportunities ?? []).find((item) => item.id === opportunityId);
    if (!row) return;
    if (row.status === "queued") {
      await buildOpportunity(opportunityId);
      return;
    }
    await rebuildOpportunity(opportunityId);
  };

  const stopQueueSession = async (opportunityId: string, sessionId: string): Promise<void> => {
    setBusyId(opportunityId);
    try {
      await hivePostJson(`agents/sessions/${sessionId}/control`, { action: "stop" });
      toast.success("Build stopped.");
      await refreshAfterQueueAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Stop failed.");
    } finally {
      setBusyId(null);
    }
  };

  const factoryLlmShortLabel = useMemo(() => {
    const llm = snapshot?.llm;
    if (!llm?.primary_model) return undefined;
    const match = llm.available_models?.find((row) => row.value === llm.primary_model);
    if (match?.label) {
      const short = match.label.split("(")[0]?.trim();
      return short ? short.slice(0, 28) : match.label.slice(0, 28);
    }
    return llm.primary_model.split("/").pop()?.slice(0, 24);
  }, [snapshot?.llm]);

  const rebuildableRows = useMemo(
    () =>
      (snapshot?.opportunities ?? []).filter(
        (row) =>
          row.status === "failed"
          || isStuckFactoryBuild(row)
          || (row.status === "awaiting_forge"
            && (row.forge_quality_passed === false || row.forge_critic_approved === false)),
      ),
    [snapshot?.opportunities],
  );

  const rebuildAllFailed = async (): Promise<void> => {
    if (rebuildableRows.length === 0) return;
    setBusyId("rebuild-failed");
    try {
      const res = await hivePostJson<{ approved: number; rebuilt: number; started: number }>(
        "skill-factory/queue/drain",
        {},
      );
      const moved = (res.rebuilt ?? 0) + (res.started ?? 0) + (res.approved ?? 0);
      toast.success(
        moved > 0
          ? `Queue drain: ${res.rebuilt ?? 0} rebuilt · ${res.started ?? 0} started · ${res.approved ?? 0} approved`
          : "Drain ran — waiting for build slots or weekly cap.",
      );
      await refreshAfterQueueAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Rebuild failed.");
    } finally {
      setBusyId(null);
    }
  };

  const dismissAllFailed = async (): Promise<void> => {
    const failedIds = queueRows.filter((row) => row.status === "failed").map((row) => row.id);
    if (failedIds.length === 0) return;
    setBusyId("dismiss-failed");
    try {
      for (const id of failedIds) {
        await hivePostJson(`skill-factory/opportunities/${id}/dismiss`, {});
      }
      toast.success(`Cleared ${failedIds.length} failed build${failedIds.length === 1 ? "" : "s"}.`);
      await refreshAfterQueueAction();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Dismiss failed.");
    } finally {
      setBusyId(null);
    }
  };

  const rejectAllFailedForges = async (): Promise<void> => {
    setBusyId("reject-failed");
    try {
      const res = await hivePostJson<{ rejected: number }>("skill-factory/queue/reject-failed-forges", {});
      toast.success(`Rejected ${res.rejected} failed forge(s).`);
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Bulk reject failed.");
    } finally {
      setBusyId(null);
    }
  };

  const applyProductPreset = async (presetId: string): Promise<void> => {
    setBusyId(`preset-${presetId}`);
    try {
      const res = await hivePostJson<{ policy: SkillFactoryPolicy; niche_seeds: string[] }>(
        `skill-factory/product-presets/${presetId}/apply`,
        {},
      );
      setPolicyDraft(res.policy);
      toast.success("Preset applied.", { description: `${res.niche_seeds.length} niche seeds loaded.` });
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Preset apply failed.");
    } finally {
      setBusyId(null);
    }
  };

  const exportSkill = async (id: string): Promise<void> => {
    setBusyId(id);
    try {
      const bundle = await hivePostJson<SkillExportResponse>(`skill-factory/skills/${id}/export`, {});
      await downloadSkillExportBundle(bundle);
      toast.success("Harness pack downloaded.");
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
  const commercialLaunchEnabled = snapshot?.commercial_launch_enabled ?? !personalOsMode;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-(--qs-text)">Skill Factory</p>
          <p className="mt-0.5 text-xs text-(--qs-text-3)">
            {commercialLaunchEnabled
              ? "Research → build → export Verified Niche Harness packs (SKILL + HARNESS + EVAL + TOOLS). Sell on Gumroad — not in-app."
              : "Research → build → export verified harness packs for your personal agent OS — no Gumroad launch lane."}
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
          {tab === "guide" ? (
            <div className="space-y-4">
              {commercialLaunchEnabled ? (
                <SkillFactoryRevenueFunnelPanel
                  launchReadiness={snapshot.launch_readiness}
                  libraryCount={(snapshot.library ?? []).length}
                  buildingCount={snapshot.building_count}
                  launchQueueCount={(snapshot.launch_queue ?? []).length}
                  nearMiss={snapshot.launch_near_miss ?? []}
                  onSmartRebuild={(id) => void smartRebuildSkill(id)}
                  busyId={busyId}
                />
              ) : null}
              <SkillFactoryManualPanel personalOsLite={!commercialLaunchEnabled} />
            </div>
          ) : null}

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
              <div className="mt-3 flex flex-wrap items-center gap-2">
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
                {snapshot.opportunity_counts ? (
                  <>
                    <V4Badge tone={snapshot.opportunity_counts.failed > 0 ? "warn" : "info"}>
                      {snapshot.opportunity_counts.actionable} in pipeline
                    </V4Badge>
                    {snapshot.opportunity_counts.failed > 0 ? (
                      <V4Badge tone="warn">{snapshot.opportunity_counts.failed} failed</V4Badge>
                    ) : null}
                    {snapshot.opportunity_counts.building > 0 ? (
                      <V4Badge tone="info">{snapshot.opportunity_counts.building} building</V4Badge>
                    ) : null}
                  </>
                ) : null}
                {(snapshot.actionable_count ?? 0) > 0 ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => navigateSkillFactoryTab("queue")}
                  >
                    Open Queue ({snapshot.actionable_count})
                  </button>
                ) : null}
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
                  <div className="space-y-2 text-xs text-(--qs-text-4)">
                    {snapshot.opportunity_counts && snapshot.opportunity_counts.actionable > 0 ? (
                      <p>
                        Pipeline: {snapshot.opportunity_counts.pending} pending ·{" "}
                        {snapshot.opportunity_counts.queued} queued · {snapshot.opportunity_counts.building} building ·{" "}
                        {snapshot.opportunity_counts.awaiting_forge} forge ·{" "}
                        <span className="text-error">{snapshot.opportunity_counts.failed} failed</span>
                        {snapshot.opportunities_truncated ? " (list truncated — use Queue tab)" : null}
                      </p>
                    ) : (
                      <p>No pending opportunities — run research or add niche seeds in Settings.</p>
                    )}
                    {(snapshot.failed_count ?? 0) > 0 ? (
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        onClick={() => navigateSkillFactoryTab("queue")}
                      >
                        Manage {snapshot.failed_count} failed on Queue →
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </ul>
            </V4Card>
            </>
          ) : null}

          {tab === "queue" ? (
            <>
            <FactoryQueueSloPanel slo={snapshot.queue_slo} />
            <V4Card className="mt-4" id="factory-queue">
              <V4CardHeader
                title="Build queue"
                description={
                  snapshot.opportunity_counts
                    ? `${snapshot.opportunity_counts.actionable} actionable · ${snapshot.opportunity_counts.failed} failed · ${snapshot.opportunity_counts.building} building · max ${policyDraft?.max_concurrent_builds ?? 5} parallel`
                    : "Queued runs — real phase labels, no fake %. Tune throughput in Settings."
                }
                hint={sectionHintNode("skillFactoryQueue")}
                actions={
                  <div className="flex flex-wrap items-center gap-2">
                    {rebuildableRows.length > 0 ? (
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                        disabled={busyId === "rebuild-failed" || factoryBuildDisabled(snapshot?.llm)}
                        onClick={() => void rebuildAllFailed()}
                      >
                        <RefreshCwIcon className="size-3.5" aria-hidden />
                        Rebuild forges ({rebuildableRows.length})
                      </button>
                    ) : null}
                    {queueRows.some((r) => r.status === "failed") ? (
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        disabled={busyId === "dismiss-failed"}
                        onClick={() => void dismissAllFailed()}
                      >
                        Clear failed
                      </button>
                    ) : null}
                    {queueRows.some((r) => r.status === "awaiting_forge" && r.forge_quality_passed === false) ? (
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        disabled={busyId === "reject-failed"}
                        onClick={() => void rejectAllFailedForges()}
                      >
                        Reject all failed forges
                      </button>
                    ) : null}
                  </div>
                }
              />
              <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
                Factory runs
                <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                  ({queueRows.length} shown
                  {snapshot.opportunity_counts
                    ? ` · ${snapshot.opportunity_counts.actionable} actionable in DB`
                    : null}
                  )
                </span>
              </p>
              <div className="v4-sessions-list-scroll hive-scrollbar mt-2">
                {queueRows.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-(--qs-border) bg-black/20 px-4 py-6 text-center">
                    <p className="text-sm text-(--qs-text-2)">Queue empty — run Research or Rebuild failed tasks.</p>
                  </div>
                ) : (
                  queueRows.map((row) => (
                    <FactoryQueueTaskCard
                      key={row.id}
                      row={row}
                      busyId={busyId}
                      buildDisabled={factoryBuildDisabled(snapshot?.llm)}
                      factoryLlmLabel={factoryLlmShortLabel}
                      onRun={(id) => void runQueueTask(id)}
                      onStop={(id, sessionId) => void stopQueueSession(id, sessionId)}
                      onRebuild={(id) => void rebuildOpportunity(id)}
                      onDismiss={(id) => void dismissOpportunity(id)}
                      onApproveForge={(suggestionId, id) => void approveForge(suggestionId, id)}
                      onRejectForge={(id, suggestionId) => void rejectForge(id, suggestionId)}
                      onSync={() => void refreshAfterQueueAction()}
                      onOpenReport={(sessionId) => setSessionReportId(sessionId)}
                    />
                  ))
                )}
              </div>
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
            </>
          ) : null}

          {tab === "library" ? (
            <V4Card id="skill-factory-library" className="mt-4 scroll-mt-28">
              <V4CardHeader
                title="Tenant skill library"
                description="Same row pattern as Forager — ID, verdict badges, sellable progress, inline actions. Sieve + eval + export unchanged."
                hint={sectionHintNode("skillFactoryLibrary")}
              />
              <div className="mt-3 flex flex-col gap-3 px-1 md:flex-row md:items-stretch">
                <input
                  className="qs-input min-w-0 flex-1"
                  placeholder="Filter skills by title / slug / verdict / issues…"
                  value={libraryQuery}
                  onChange={(event) => setLibraryQuery(event.target.value)}
                />
                <QsSelect
                  className="w-full min-w-0 md:w-52 md:shrink-0"
                  value={librarySieve}
                  onValueChange={(next) => setLibrarySieve(next as LibrarySieveVerdict)}
                  options={([
                    "all",
                    "launch",
                    "worth_retry",
                    "deprioritize",
                    "retire",
                  ] as const).map((key) => ({
                    value: key,
                    label:
                      key === "all"
                        ? `all verdicts (${librarySieveCounts.all})`
                        : `${LIBRARY_SIEVE_LABELS[key]} (${librarySieveCounts[key]})`,
                  }))}
                />
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 px-1">
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                  disabled={busyId !== null || libraryRebuildEligible.length === 0}
                  onClick={() => void smartRebuildAllLibrary()}
                >
                  {busyId === "library-rebuild-all" ? (
                    <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                  ) : (
                    <RefreshCwIcon className="size-3.5" aria-hidden />
                  )}
                  Smart rebuild all ({libraryRebuildEligible.length})
                </button>
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                  onClick={() => navigateSkillFactoryTab("queue")}
                >
                  Open Queue →
                </button>
              </div>
              {!commercialLaunchEnabled ? (
                <div
                  id="export-batch"
                  className="scroll-mt-28 mt-4 rounded-xl border border-pollen/35 bg-pollen/5 px-4 py-4"
                  data-testid="skill-factory-export-batch"
                >
                  <p className="text-sm font-semibold text-(--qs-text)">Export verified batch</p>
                  <p className="mt-1 text-xs text-(--qs-text-3)">
                    Personal OS lite — prepare up to 3 sellable SKILL.md bundles (Launch tab hidden; same as
                    {" "}
                    <code className="font-mono text-[10px]">launch/prepare</code>
                    ).
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                      disabled={busyId === "launch-prepare" || sellableLibraryCount === 0}
                      onClick={() => void prepareLaunchBatch()}
                    >
                      {busyId === "launch-prepare" ? (
                        <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                      ) : (
                        <DownloadIcon className="size-3.5" aria-hidden />
                      )}
                      Export verified batch ({Math.min(3, sellableLibraryCount) || 0})
                    </button>
                    {sellableLibraryCount === 0 ? (
                      <span className="text-xs text-(--qs-text-4)">No sellable skills yet — approve quality forges first.</span>
                    ) : null}
                  </div>
                </div>
              ) : null}
              <div
                id="export-channels"
                className="scroll-mt-28 mt-4 rounded-xl border border-cyan/30 bg-cyan/5 px-4 py-4"
                data-testid="skill-factory-export-channels"
              >
                <p className="text-sm font-semibold text-(--qs-text)">Export channels · Gumroad lane</p>
                <p className="mt-1 text-xs text-(--qs-text-3)">
                  Personal OS keeps Launch tab hidden — use manual tarball upload or enable Gumroad API when selling.
                </p>
                <ul className="mt-3 space-y-2 text-xs text-(--qs-text-2)">
                  <li className="flex flex-wrap items-center gap-2">
                    <V4Badge tone="ok">Manual bundle</V4Badge>
                    <span>
                      <code className="font-mono text-[10px]">exports/gumroad-upload/*.tar.gz</code>
                      {" · "}
                      <code className="font-mono text-[10px]">LAUNCH_CHECKLIST.md</code>
                    </span>
                  </li>
                  <li className="flex flex-wrap items-center gap-2">
                    <V4Badge tone={snapshot.github_pr_export_ready ? "ok" : "warn"}>
                      GitHub PR
                    </V4Badge>
                    <span>
                      {snapshot.github_pr_export_ready
                        ? "Auto PR export ready from Library rows."
                        : "Connect github_rest + SKILL_FACTORY_GITHUB_PR_ENABLED for auto PR."}
                    </span>
                  </li>
                  <li className="flex flex-wrap items-center gap-2">
                    <V4Badge tone={snapshot.gumroad_listing_ready ? "ok" : "warn"}>
                      Gumroad API
                    </V4Badge>
                    <span>
                      {snapshot.gumroad_listing_ready
                        ? "Draft API ready — enable commercial host or operator script with token."
                        : "Manual upload lane — or set SKILL_FACTORY_GUMROAD_LISTING_ENABLED + Gumroad token."}
                    </span>
                  </li>
                </ul>
                {snapshot.launch_readiness?.exports_on_disk_hint ? (
                  <p className="mt-2 font-mono text-[10px] text-(--qs-text-4)">
                    Server bundles: {snapshot.launch_readiness.exports_on_disk_hint}
                  </p>
                ) : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                    disabled={busyId === "launch-prepare" || sellableLibraryCount === 0}
                    onClick={() => void prepareLaunchBatch()}
                  >
                    <DownloadIcon className="size-3.5" aria-hidden />
                    Refresh launch batch
                  </button>
                  <Link href="/integrations?tab=connectors" className="qs-btn qs-btn--ghost qs-btn--sm">
                    Gumroad connector
                  </Link>
                </div>
              </div>
              <div className="mt-4 px-1">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
                    Library
                    {searchedLibraryRows.length > 0 ? (
                      <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                        ({searchedLibraryRows.length})
                      </span>
                    ) : null}
                  </p>
                </div>
                <div className="v4-sessions-list-scroll hive-scrollbar">
                  {(snapshot.library ?? []).length === 0 ? (
                    <div className="rounded-xl border border-dashed border-(--qs-border) bg-black/20 px-4 py-6 text-center">
                      <p className="text-sm text-(--qs-text-2)">
                        No tenant skills yet — approve a completed build in Queue, then export here.
                      </p>
                    </div>
                  ) : searchedLibraryRows.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-(--qs-border) bg-black/20 px-4 py-6 text-center">
                      <p className="text-sm text-(--qs-text-2)">
                        No skills match this filter.
                      </p>
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm mt-3"
                        onClick={() => {
                          setLibraryQuery("");
                          setLibrarySieve("all");
                        }}
                      >
                        Reset filters
                      </button>
                    </div>
                  ) : (
                    visibleLibraryRows.map((row) => (
                      <FactoryLibrarySkillCard
                        key={row.id}
                        row={row}
                        busyId={busyId}
                        githubPrReady={snapshot.github_pr_export_ready}
                        gumroadListingReady={commercialLaunchEnabled && snapshot.gumroad_listing_ready}
                        gumroadPublishReady={commercialLaunchEnabled && snapshot.gumroad_publish_ready}
                        inlineEval={inlineEvalBySkill[row.id] ?? null}
                        rebuildQueued={libraryRebuildQueued.has(row.id)}
                        onSmartRebuild={(id) => void smartRebuildSkill(id)}
                        onDeprioritize={(id) => void setSkillDisposition(id, "deprioritized", "Niche deprioritized — lower research priority.")}
                        onRetire={(id) => void setSkillDisposition(id, "retired", "Niche retired — excluded from research.")}
                        onRemove={(id, title) => void removeLibrarySkill(id, title)}
                        onEval={(id, title) => void evalSkill(id, title)}
                        onDownloadEvalReport={(id, title) => void downloadEvalReport(id, title)}
                        onExport={(id) => void exportSkill(id)}
                        onGithubPr={(id) => void pushGithubPr(id)}
                        onGumroadDraft={
                          commercialLaunchEnabled ? (id) => void createGumroadDraft(id) : undefined
                        }
                        onGumroadPublish={
                          commercialLaunchEnabled
                            ? (id) => void publishGumroadListing(id, !row.gumroad_product_id)
                            : undefined
                        }
                      />
                    ))
                  )}
                </div>
                {hiddenLibraryCount > 0 && !showAllLibrary ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
                    disabled={busyId !== null}
                    onClick={() => setShowAllLibrary(true)}
                  >
                    Show all ({searchedLibraryRows.length})
                  </button>
                ) : null}
                {showAllLibrary && searchedLibraryRows.length > LIBRARY_PREVIEW_LIMIT ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
                    onClick={() => setShowAllLibrary(false)}
                  >
                    Show less
                  </button>
                ) : null}
                {(snapshot.library_purge_eligible ?? 0) > 0 ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--danger mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
                    disabled={busyId !== null}
                    onClick={() => void purgeReviewedLibrary()}
                  >
                    {busyId === "library-purge-reviewed"
                      ? "Removing…"
                      : libraryQuery.trim() || librarySieve !== "all"
                        ? `Delete reviewed in filter (${searchedLibraryRows.filter((row) => row.purge_eligible).length})`
                        : `Delete reviewed (${snapshot.library_purge_eligible})`}
                  </button>
                ) : null}
                {(snapshot.library_duplicates_hidden ?? 0) > 0 ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
                    disabled={busyId !== null}
                    onClick={() => void archiveLibraryDuplicates()}
                  >
                    {busyId === "library-archive-dupes"
                      ? "Archiving…"
                      : `Archive ${snapshot.library_duplicates_hidden} duplicate${(snapshot.library_duplicates_hidden ?? 0) === 1 ? "" : "s"}`}
                  </button>
                ) : null}
              </div>
            </V4Card>
          ) : null}

          {commercialLaunchEnabled && tab === "launch" ? (
            <>
            <SkillFactoryRevenueFunnelPanel
              launchReadiness={snapshot.launch_readiness}
              libraryCount={(snapshot.library ?? []).length}
              buildingCount={snapshot.building_count}
              launchQueueCount={(snapshot.launch_queue ?? []).length}
              nearMiss={snapshot.launch_near_miss ?? []}
              onSmartRebuild={(id) => void smartRebuildSkill(id)}
              busyId={busyId}
            />
            <HarnessProductLinesPanel />
            <HarnessEvalPanel llm={snapshot?.llm ?? null} />
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
                        <p className="mt-1 font-mono text-[10px] text-pollen">{row.slug} · harness pack</p>
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
                        Harness pack
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
                                <p className="mt-1 text-[10px] text-(--qs-text-4)">
                                  fix: {row.sellable_issues.slice(0, 2).join(", ")}
                                </p>
                              ) : null}
                              <button
                                type="button"
                                className="mt-2 qs-btn qs-btn--primary qs-btn--sm gap-1"
                                disabled={busyId === row.id}
                                onClick={() => void smartRebuildSkill(row.id)}
                              >
                                <RefreshCwIcon className="size-3.5" aria-hidden />
                                Smart rebuild
                              </button>
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
              <V4CardHeader
                title="Queue throughput"
                description="Parallel factory builds and auto-drain batch size (Nemotron/OpenRouter free tier can run higher)."
              />
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Auto-drain queue (rebuild failed forges)</span>
                <HiveSwitch
                  checked={policyDraft.auto_queue_drain_enabled ?? true}
                  onCheckedChange={(v) => setPolicyDraft({ ...policyDraft, auto_queue_drain_enabled: v })}
                />
              </label>
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>Auto-rebuild quality/critic failures</span>
                <HiveSwitch
                  checked={policyDraft.auto_rebuild_failed_forges ?? true}
                  onCheckedChange={(v) => setPolicyDraft({ ...policyDraft, auto_rebuild_failed_forges: v })}
                />
              </label>
              <label className="block text-sm">
                <span className="text-(--qs-text-3)">Max parallel builds</span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  className="qs-input mt-1 w-full max-w-xs"
                  value={policyDraft.max_concurrent_builds ?? 5}
                  onChange={(e) =>
                    setPolicyDraft({
                      ...policyDraft,
                      max_concurrent_builds: Number.parseInt(e.target.value, 10) || 5,
                    })
                  }
                />
              </label>
              <label className="block text-sm">
                <span className="text-(--qs-text-3)">Drain batch per tick (rebuilds/approvals per 2 min)</span>
                <input
                  type="number"
                  min={1}
                  max={15}
                  className="qs-input mt-1 w-full max-w-xs"
                  value={policyDraft.drain_batch_per_tick ?? 5}
                  onChange={(e) =>
                    setPolicyDraft({
                      ...policyDraft,
                      drain_batch_per_tick: Number.parseInt(e.target.value, 10) || 5,
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
                <span className="text-(--qs-text-3)">Revenue presets (analysis → seeds)</span>
                <p className="mt-1 max-w-xl text-xs text-(--qs-text-4)">
                  One click loads Pigford solo-founder or Middleton local-biz bundle seeds, then run Research →
                  Queue builds. Cursor handles implementation; Grok Control Plane for governed deploys.
                </p>
                <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                  {productPresets.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm text-left"
                      disabled={busyId === `preset-${preset.id}`}
                      onClick={() => void applyProductPreset(preset.id)}
                    >
                      {busyId === `preset-${preset.id}` ? (
                        <Loader2Icon className="size-3.5 animate-spin" aria-hidden />
                      ) : null}
                      {preset.title} · €{(preset.gumroad_price_eur_cents_recommended / 100).toFixed(0)}
                    </button>
                  ))}
                </div>
              </label>
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
      <AgentSessionReportDialog
        sessionId={sessionReportId}
        open={sessionReportId !== null}
        onOpenChange={(open) => {
          if (!open) setSessionReportId(null);
        }}
      />
    </div>
  );
}
