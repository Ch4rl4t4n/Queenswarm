"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowRight,
  Briefcase,
  Copy,
  FlaskConical,
  Gauge,
  Lightbulb,
  Link2,
  Loader2,
  MessageSquare,
  Play,
  Rocket,
  Terminal,
  Users,
  Waypoints,
} from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { FirstRunSetupBanner } from "@/components/hive/first-run-setup-banner";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { usePlatform } from "@/components/hive/platform-context";
import { HiveSectionSubnav } from "@/components/hive/hive-section-subnav";
import { HiveSubnavContent } from "@/components/hive/hive-subnav-stack";
import { HiveSubsectionHeader } from "@/components/hive/hive-subsection-header";
import { InlineSectionHintKey } from "@/components/hive/inline-section-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { hivePageShellErrorFirst } from "@/lib/hive-page-error";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { readCockpitCoreCache, writeCockpitCoreCache } from "@/lib/cockpit-cache";
import { type CockpitHintKey } from "@/lib/cockpit-section-hints";
import { executionStudioSectionHref } from "@/lib/integrations-routes";
import {
  cockpitSectionFromHash,
  cockpitSectionHref,
  resolveCockpitSection,
  type CockpitSection,
} from "@/lib/cockpit-routes";
import { useRouteScopedPollOptions } from "@/lib/hooks/use-route-scoped-poll";
import {
  cockpitNavSections,
  visibleCockpitSections,
} from "@/lib/operator-canonical-ui";
const GrokControlPlanePanel = dynamic(
  () => import("@/components/hive/grok-control-plane-panel").then((mod) => ({ default: mod.GrokControlPlanePanel })),
  { loading: () => <HivePanelSectionSkeleton label="Loading Grok control plane" /> },
);

const SoloOperatorFourLanesPanel = dynamic(
  () =>
    import("@/components/hive/solo-operator-four-lanes-panel").then((mod) => ({
      default: mod.SoloOperatorFourLanesPanel,
    })),
  { loading: () => <HivePanelSectionSkeleton label="Loading four lanes" /> },
);

const InnovationLabPanel = dynamic(
  () => import("@/components/hive/innovation-lab-panel").then((mod) => ({ default: mod.InnovationLabPanel })),
  { loading: () => <HivePanelSectionSkeleton label="Loading innovation lab" /> },
);

const BusinessOperatorPanel = dynamic(
  () =>
    import("@/components/hive/business-operator-panel").then((mod) => ({
      default: mod.BusinessOperatorPanel,
    })),
  { loading: () => <HivePanelSectionSkeleton label="Loading business brief" minHeightClass="min-h-[8rem]" /> },
);

interface CockpitAction {
  id: string;
  label: string;
  detail: string;
  priority: "high" | "medium" | "low";
  href: string | null;
  action: string | null;
}

interface SwarmFleetItem {
  routine_id: string;
  name: string;
  active: boolean;
  schedule_kind: string;
  autopilot: boolean;
  immune_status: "healthy" | "watch" | "quarantine";
}

interface OperatorCockpitSnapshot {
  enabled: boolean;
  generated_at: string;
  now_actions: CockpitAction[];
  swarm_fleet: SwarmFleetItem[];
  trio: { lanes_bound?: number; bound_lane_count?: number };
  oracle_warnings: Array<{ id: string; severity: string; message: string; fix_href?: string }>;
  feature_modules: Array<{ id: string; label: string; status: string; summary: string; enabled: boolean }>;
  innovation_lab: { enabled: boolean; pending_count: number };
  zero_ui?: {
    enabled: boolean;
    telegram_configured: boolean;
    webhook_secret_configured: boolean;
    webhook_url: string | null;
    commands: string[];
  };
  trust_autopilot?: {
    enabled: boolean;
    lanes: Record<string, string>;
  };
  intent_crystallizer?: {
    enabled: boolean;
    min_chars: number;
    templates: Array<{ id: string; label: string; href: string }>;
  };
  proof_of_hive?: {
    enabled: boolean;
    count: number;
    receipts: Array<{
      token: string;
      share_url: string;
      title: string;
      artifact_type: string;
      trust_lane: string;
      verified_at: string;
      event_kind?: string | null;
    }>;
  };
  links: Record<string, string>;
  context_teleport?: {
    enabled: boolean;
    packs: Array<{ pack_id: string; recipe_name: string; similarity: number; excerpt: string }>;
  };
  regret_simulator?: {
    enabled: boolean;
    regret_score: number;
    recommendation: string;
    summary: string;
    scenarios: Array<{ id: string; label: string; detail: string; severity: string }>;
  };
  ambient_forager?: {
    enabled: boolean;
    item_count: number;
    items: Array<{ id: string; title: string; detail: string; source: string }>;
  };
  parallel_hive_view?: {
    enabled: boolean;
    active_count: number;
    sessions: Array<{ session_id: string; goal: string; status: string; merge_ready: boolean }>;
  };
  swarm_immune_system?: {
    enabled: boolean;
    quarantine_count: number;
    watch_count: number;
    healthy_count: number;
    summary: string;
    routines: Array<{ routine_id: string; name: string; immune_status: string; recommendation: string }>;
  };
  evolutionary_recipes?: {
    enabled: boolean;
    verified_outcomes: number;
    ready: boolean;
    summary: string;
    variants: Array<{ recipe_id: string | null; name: string; similarity: number; fitness_rank: number; detail: string }>;
  };
  icm_tools?: {
    enabled: boolean;
    link_drop_enabled: boolean;
    dialogue_extract_enabled: boolean;
    keyword_scan_enabled: boolean;
    min_dialogue_chars: number;
    min_url_chars: number;
    quick_automations: Array<{
      id: string;
      label: string;
      detail: string;
      kind: "action" | "link_drop" | "dialogue_extract" | "href";
      action: string | null;
      href: string | null;
    }>;
  };
  grok_control_plane?: {
    enabled: boolean;
    cli_available: boolean;
    active_runs: number;
    draft_runs: number;
    failed_runs: number;
    failed_alert_threshold?: number;
    health_level?: "ok" | "warn" | "error";
  };
}

function CockpitHint({ hintKey }: { hintKey: CockpitHintKey }) {
  return <InlineSectionHintKey hintKey={hintKey} />;
}

function priorityTone(p: CockpitAction["priority"]): "ok" | "warn" | "err" | "info" {
  if (p === "high") return "err";
  if (p === "medium") return "warn";
  return "info";
}

function immuneTone(s: SwarmFleetItem["immune_status"]): "ok" | "warn" | "err" {
  if (s === "quarantine") return "err";
  if (s === "watch") return "warn";
  return "ok";
}

function grokHealthTone(health: OperatorCockpitSnapshot["grok_control_plane"]): "ok" | "warn" | "err" | "info" {
  if (!health?.enabled) return "info";
  const level = health.health_level ?? "ok";
  if (level === "error") return "err";
  if (level === "warn") return "warn";
  if (level === "ok") return "ok";
  return "ok";
}

const COCKPIT_SECTIONS: {
  id: CockpitSection;
  label: string;
  icon: typeof Gauge;
}[] = [
  { id: "business", label: "Business brief", icon: Briefcase },
  { id: "overview", label: "Operator overview", icon: Gauge },
  { id: "lanes", label: "Lanes", icon: Waypoints },
  { id: "command", label: "Command", icon: MessageSquare },
  { id: "grok", label: "Grok", icon: Terminal },
  { id: "icm", label: "ICM tools", icon: Link2 },
  { id: "fleet", label: "Fleet", icon: Users },
  { id: "modules", label: "Modules", icon: FlaskConical },
  { id: "innovation", label: "Innovation", icon: Lightbulb },
];

const COCKPIT_SECTION_IDS: CockpitSection[] = COCKPIT_SECTIONS.map((row) => row.id);

function OperatorCockpitPanelInner() {
  const { soloMode } = usePlatform();
  const visibleSectionIds = useMemo(
    () => visibleCockpitSections(soloMode, COCKPIT_SECTION_IDS),
    [soloMode],
  );
  const cockpitNavSplit = useMemo(
    () => cockpitNavSections(soloMode, COCKPIT_SECTION_IDS),
    [soloMode],
  );
  const primaryCockpitNav = useMemo(
    () => COCKPIT_SECTIONS.filter((row) => cockpitNavSplit.primary.includes(row.id)),
    [cockpitNavSplit.primary],
  );
  const advancedCockpitNav = useMemo(
    () => COCKPIT_SECTIONS.filter((row) => cockpitNavSplit.advanced.includes(row.id)),
    [cockpitNavSplit.advanced],
  );
  const visibleCockpitNav = useMemo(
    () => COCKPIT_SECTIONS.filter((row) => visibleSectionIds.includes(row.id)),
    [visibleSectionIds],
  );
  const [snapshot, setSnapshot] = useState<OperatorCockpitSnapshot | null>(() =>
    readCockpitCoreCache<OperatorCockpitSnapshot>(),
  );
  const [loading, setLoading] = useState(() => readCockpitCoreCache<OperatorCockpitSnapshot>() === null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [modulesErr, setModulesErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [hotline, setHotline] = useState("");
  const [crystal, setCrystal] = useState("");
  const [crystalPlan, setCrystalPlan] = useState<Record<string, unknown> | null>(null);
  const [linkUrl, setLinkUrl] = useState("");
  const [linkBrief, setLinkBrief] = useState<Record<string, unknown> | null>(null);
  const [dialogueText, setDialogueText] = useState("");
  const [dialogueExtract, setDialogueExtract] = useState<Record<string, unknown> | null>(null);
  const [keywordMatches, setKeywordMatches] = useState<
    Array<{ id: string; label: string; detail: string; priority: string; href: string | null; action: string | null }>
  >([]);
  const searchParams = useSearchParams();
  const [section, setSection] = useState<CockpitSection>(() =>
    resolveCockpitSection({ visibleIds: visibleSectionIds }),
  );
  const [modulesHydrated, setModulesHydrated] = useState(false);
  const [modulesLoading, setModulesLoading] = useState(false);

  const dismissShellErrors = useCallback(() => {
    setLoadErr(null);
    setModulesErr(null);
  }, []);

  const shellError = hivePageShellErrorFirst([loadErr, modulesErr], dismissShellErrors);

  const selectSection = useCallback((next: CockpitSection) => {
    setSection(next);
    window.history.replaceState(null, "", cockpitSectionHref(next));
  }, []);

  const loadModules = useCallback(async () => {
    if (modulesHydrated) {
      return;
    }
    setModulesLoading(true);
    try {
      const partial = await hiveGet<OperatorCockpitSnapshot>("operator/cockpit?scope=modules");
      setSnapshot((prev) => (prev ? { ...prev, ...partial } : partial));
      setModulesHydrated(true);
      setModulesErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Modules snapshot unavailable";
      setModulesErr(msg);
    } finally {
      setModulesLoading(false);
    }
  }, [modulesHydrated]);

  const load = useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) {
      setLoading(true);
    }
    try {
      const cockpit = await hiveGet<OperatorCockpitSnapshot>("operator/cockpit?scope=core");
      setSnapshot(cockpit);
      writeCockpitCoreCache(cockpit);
      setLoadErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Agentic OS unavailable";
      setLoadErr(msg);
    } finally {
      if (!opts?.silent) {
        setLoading(false);
      }
    }
  }, []);

  const pollOpts = useRouteScopedPollOptions(COCKPIT_POLL_COLONY_TELEMETRY_MS, "/agentic-os");

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (section === "modules" && snapshot?.enabled) {
      void loadModules();
    }
  }, [section, snapshot?.enabled, loadModules]);

  useEffect(() => {
    const syncFromHash = (): void => {
      const fromHash = cockpitSectionFromHash(window.location.hash);
      if (fromHash && visibleSectionIds.includes(fromHash)) {
        setSection(fromHash);
        return;
      }
      const next = resolveCockpitSection({ visibleIds: visibleSectionIds });
      setSection(next);
      window.history.replaceState(null, "", cockpitSectionHref(next));
    };
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, [visibleSectionIds]);

  useEffect(() => {
    const ballroomSession = searchParams.get("ballroom_session")?.trim();
    const dumpSleepBatch = searchParams.get("dump_sleep_batch")?.trim();
    const importId = ballroomSession || dumpSleepBatch;
    if (!importId || dialogueText.trim().length >= 40) {
      return;
    }
    const path = ballroomSession
      ? `operator/ballroom/${encodeURIComponent(ballroomSession)}/transcript-text`
      : `operator/dump-sleep/${encodeURIComponent(dumpSleepBatch!)}/transcript-text`;
    let cancelled = false;
    void hiveGet<{ ok: boolean; text: string }>(path)
      .then((body) => {
        if (cancelled || !body.text?.trim()) {
          return;
        }
        setDialogueText(body.text);
        setSection("icm");
        window.history.replaceState(null, "", cockpitSectionHref("icm"));
        toast.success(
          ballroomSession ? "Ballroom transcript loaded — run Extract." : "Dump & Sleep briefing loaded — run Extract.",
        );
      })
      .catch((e) => {
        if (!cancelled) {
          toast.error(e instanceof HiveApiError ? e.message : "Transcript import unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [searchParams, dialogueText]);

  useEffect(() => {
    const ms = pollOpts.refreshInterval;
    if (typeof ms !== "number" || ms <= 0) {
      return;
    }
    const id = window.setInterval(() => {
      void load({ silent: true });
    }, ms);
    return () => window.clearInterval(id);
  }, [load, pollOpts.refreshInterval]);

  const runAction = useCallback(
    async (action: string, extra?: Record<string, unknown>) => {
      setBusy(action);
      try {
        const result = await hivePostJson<{ ok: boolean; message: string; href?: string }>("operator/act", {
          action,
          ...extra,
        });
        if (result.ok) {
          toast.success(result.message);
          if (result.href) {
            window.location.href = result.href;
          } else {
            await load();
          }
        } else {
          toast.error(result.message);
        }
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Action failed");
      } finally {
        setBusy(null);
      }
    },
    [load],
  );

  const previewCrystal = useCallback(async () => {
    const text = crystal.trim();
    if (text.length < 8) {
      toast.error("Min. 8 znakov pre crystallize.");
      return;
    }
    setBusy("crystal-preview");
    try {
      const result = await hivePostJson<{ ok: boolean; plan: Record<string, unknown> }>("operator/crystallize", {
        text,
        launch: false,
      });
      setCrystalPlan(result.plan);
      toast.success("Intent crystallized — preview ready.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Crystallize failed");
    } finally {
      setBusy(null);
    }
  }, [crystal]);

  const launchCrystal = useCallback(async () => {
    const text = crystal.trim();
    if (text.length < 8) {
      toast.error("Min. 8 znakov pre launch.");
      return;
    }
    setBusy("crystal-launch");
    try {
      const result = await hivePostJson<{ ok: boolean; message: string; href?: string; plan: Record<string, unknown> }>(
        "operator/crystallize",
        { text, launch: true },
      );
      setCrystalPlan(result.plan);
      if (result.ok) {
        toast.success(result.message);
        if (result.href) window.location.href = result.href;
      } else {
        toast.error(result.message);
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Launch failed");
    } finally {
      setBusy(null);
    }
  }, [crystal]);

  const runLinkDrop = useCallback(async (persist: boolean) => {
    const url = linkUrl.trim();
    if (url.length < 8) {
      toast.error("Enter a valid URL.");
      return;
    }
    setBusy(persist ? "link-persist" : "link-preview");
    try {
      const result = await hivePostJson<{ ok: boolean; brief: Record<string, unknown> }>("operator/link-drop", {
        url,
        persist,
      });
      setLinkBrief(result.brief);
      toast.success(persist ? "Brief saved to Knowledge." : "Link brief ready.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Link Drop failed");
    } finally {
      setBusy(null);
    }
  }, [linkUrl]);

  const runDialogueExtract = useCallback(
    async (apply: "preview" | "harness" | "knowledge" | "recipe") => {
      const text = dialogueText.trim();
      const min = snapshot?.icm_tools?.min_dialogue_chars ?? 40;
      if (text.length < min) {
        toast.error(`Minimum ${min} dialogue characters required.`);
        return;
      }
      setBusy(`dialogue-${apply}`);
      try {
        const result = await hivePostJson<{
          ok: boolean;
          extraction: Record<string, unknown>;
          applied?: { href?: string; recipe_id?: string };
        }>("operator/dialogue-extract", { text, apply });
        setDialogueExtract(result.extraction);
        if (snapshot?.icm_tools?.keyword_scan_enabled) {
          const scan = await hivePostJson<{ scan: { matches: typeof keywordMatches } }>("operator/keyword-scan", {
            text,
          });
          setKeywordMatches(scan.scan.matches ?? []);
        }
        if (apply === "harness") toast.success("Added to harness memory.");
        else if (apply === "knowledge") toast.success("Saved to Knowledge.");
        else if (apply === "recipe") {
          toast.success("Recipe draft saved.");
          if (result.applied?.href) window.location.href = result.applied.href;
        } else toast.success("Dialogue extract complete.");
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Dialogue extract failed");
      } finally {
        setBusy(null);
      }
    },
    [dialogueText, snapshot?.icm_tools],
  );

  const runQuickAutomation = useCallback(
    (preset: NonNullable<OperatorCockpitSnapshot["icm_tools"]>["quick_automations"][number]) => {
      if (preset.kind === "action" && preset.action) {
        void runAction(preset.action);
        return;
      }
      if (preset.kind === "href" && preset.href) {
        window.location.href = preset.href;
        return;
      }
      if (preset.kind === "link_drop") {
        document.getElementById("link-drop")?.scrollIntoView({ behavior: "smooth" });
        return;
      }
      if (preset.kind === "dialogue_extract") {
        document.getElementById("dialogue-extract")?.scrollIntoView({ behavior: "smooth" });
      }
    },
    [runAction],
  );

  const copyProofLink = useCallback(async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Proof link copied");
    } catch {
      toast.error("Copy failed");
    }
  }, []);

  const showSecondaryRow = soloMode && advancedCockpitNav.length > 0;
  const primaryActiveId = cockpitNavSplit.primary.includes(section) ? section : "";
  const secondaryActiveId = cockpitNavSplit.advanced.includes(section) ? section : "";

  const cockpitSubnav = (
    <HiveSectionSubnav
      primary={
        soloMode
          ? primaryCockpitNav.map(({ id, label, icon }) => ({ id, label, icon }))
          : visibleCockpitNav.map(({ id, label, icon }) => ({ id, label, icon }))
      }
      secondary={
        showSecondaryRow
          ? advancedCockpitNav.map(({ id, label, icon }) => ({ id, label, icon }))
          : undefined
      }
      activePrimary={soloMode ? primaryActiveId : section}
      activeSecondary={showSecondaryRow ? secondaryActiveId : undefined}
      onPrimaryChange={(id) => selectSection(id as CockpitSection)}
      onSecondaryChange={(id) => selectSection(id as CockpitSection)}
      primaryAriaLabel="Agentic OS sections"
      secondaryAriaLabel="Agentic OS tools"
      primaryMenuKey="cockpit-primary"
      secondaryMenuKey="cockpit-tools"
    />
  );

  if (loading && !snapshot) {
    return (
      <HivePageShell
        title="Agentic OS"
        subtitle="One entry point for bees, swarms, and factory."
        hintKey="cockpit"
        subnav={cockpitSubnav}
        error={shellError}
      >
        <HivePanelSectionSkeleton label="Loading operator snapshot" minHeightClass="min-h-[12rem]" />
      </HivePageShell>
    );
  }

  if (!snapshot?.enabled) {
    return (
      <HivePageShell
        title="Agentic OS"
        subtitle="Operator Control Plane"
        hintKey="cockpit"
        error={shellError}
      >
        <V4Card>
          <p className="text-sm text-(--qs-muted)">Operator Control Plane is disabled on this deployment.</p>
        </V4Card>
      </HivePageShell>
    );
  }

  const refreshButton = <HiveRefreshButton busy={loading} onClick={() => void load()} />;

  return (
    <HivePageShell
      title="Agentic OS"
      subtitle={
        soloMode
          ? "Optional automation & innovation — start daily work in Agents"
          : "One entry point for bees, swarms, and factory."
      }
      hintKey="cockpit"
      subnav={cockpitSubnav}
      error={shellError}
    >
      <HiveSubnavContent>
      {section === "business" && soloMode ? (
        <>
          <FirstRunSetupBanner />
          <BusinessOperatorPanel />
        </>
      ) : null}

      {section === "overview" ? (
        <V4Card>
          {soloMode ? (
            <div className="mb-4 rounded-lg border border-pollen/35 bg-pollen/5 p-3 text-xs leading-relaxed text-(--qs-text-2)">
              <p className="font-semibold text-pollen">Optional — not your daily start</p>
              <p className="mt-1">
                Primary workflow:{" "}
                <Link href="/agents#sessions" className="font-medium text-cyan underline">
                  Agents → Sessions
                </Link>
                . Four Lanes run on cron; Innovation Lab is for tech SCV proposals.
              </p>
            </div>
          ) : null}
          <V4CardHeader
            kicker="Control Plane"
            title="Operator overview"
            description="Now actions, trust lanes, proof receipts, and priority queue."
            hint={<CockpitHint hintKey="overview" />}
            actions={refreshButton}
          />
          <div className="mb-4 flex flex-wrap gap-2">
            <Link href="/agents#sessions" className="qs-btn qs-btn--primary qs-btn--sm gap-1">
              Open Agents
            </Link>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
              disabled={busy === "start_day"}
              onClick={() => void runAction("start_day")}
            >
              {busy === "start_day" ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
              Start day
            </button>
            {!soloMode ? (
              <Link href={snapshot.links.factory ?? "/factory"} className="qs-btn qs-btn--ghost qs-btn--sm gap-1">
                <Rocket className="size-4" /> Factory
              </Link>
            ) : null}
            {!soloMode ? (
              <Link href={snapshot.links.swarms ?? "/swarms"} className="qs-btn qs-btn--ghost qs-btn--sm">
                Swarms
              </Link>
            ) : null}
            {soloMode ? (
              <Link href="/agentic-os#lanes" className="qs-btn qs-btn--ghost qs-btn--sm">
                Four Lanes (optional)
              </Link>
            ) : null}
          </div>

          {snapshot.trust_autopilot?.enabled ? (
            <div className="mb-4 rounded-lg border border-pollen/30 bg-pollen/5 p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-pollen">Trust Autopilot</p>
              <p className="mt-1 text-xs text-(--qs-muted)">
                Priority Telegram pings only after verified outcomes — no spam.
              </p>
              <ul className="mt-2 space-y-0.5 text-[11px] text-(--qs-muted)">
                {Object.entries(snapshot.trust_autopilot.lanes ?? {}).map(([key, label]) => (
                  <li key={key}>{label}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {snapshot.grok_control_plane?.enabled ? (
            <div className="mb-4 rounded-lg border border-cyan/30 bg-cyan/5 p-3" id="grok-health-overview">
              {(() => {
                const healthLevel = snapshot.grok_control_plane?.health_level ?? "ok";
                const failedThreshold = snapshot.grok_control_plane?.failed_alert_threshold ?? 3;
                return (
                  <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-cyan">Grok Control Plane</p>
                <V4Badge
                  tone={grokHealthTone(snapshot.grok_control_plane)}
                  className={healthLevel === "error" ? "animate-pulse" : undefined}
                >
                  {healthLevel === "error"
                    ? "needs attention"
                    : healthLevel === "warn"
                      ? "in progress"
                      : "healthy"}
                </V4Badge>
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-(--qs-muted)">
                <span>active {snapshot.grok_control_plane.active_runs}</span>
                <span>draft {snapshot.grok_control_plane.draft_runs}</span>
                <span>
                  failed {snapshot.grok_control_plane.failed_runs}/{failedThreshold}
                </span>
                <span>cli {snapshot.grok_control_plane.cli_available ? "ok" : "missing"}</span>
              </div>
              <button
                type="button"
                className="mt-2 text-xs text-cyan hover:text-pollen"
                onClick={() => selectSection("grok")}
              >
                Open Grok queue →
              </button>
                  </>
                );
              })()}
            </div>
          ) : null}

          {snapshot.proof_of_hive?.enabled ? (
            <div className="mb-4 rounded-lg border border-[#00FF8833] bg-[#00FF8808] p-3" id="proof-of-hive">
              <p className="text-xs font-semibold uppercase tracking-wider text-[#00FF88]">Proof-of-Hive</p>
              <p className="mt-1 text-xs text-(--qs-muted)">
                Shareable verify receipts — HMAC signature, verify-first outcomes.
              </p>
              {snapshot.proof_of_hive.receipts.length === 0 ? (
                <p className="mt-2 text-[11px] text-(--qs-muted)">
                  No receipts yet — they appear after simulate-approved publish packs.
                </p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {snapshot.proof_of_hive.receipts.map((receipt) => (
                    <li
                      key={receipt.token}
                      className="flex flex-wrap items-center justify-between gap-2 rounded border border-(--qs-border) bg-black/20 px-2 py-1.5 text-xs"
                    >
                      <div className="min-w-0">
                        <span className="font-medium text-(--qs-text)">{receipt.title}</span>
                        <p className="text-[10px] text-(--qs-muted)">
                          {receipt.trust_lane} · {receipt.event_kind ?? receipt.artifact_type}
                        </p>
                      </div>
                      <div className="flex shrink-0 gap-1">
                        <Link href={receipt.share_url} className="qs-btn qs-btn--ghost qs-btn--sm" target="_blank">
                          Open
                        </Link>
                        <button
                          type="button"
                          className="qs-btn qs-btn--ghost qs-btn--sm"
                          onClick={() => void copyProofLink(receipt.share_url)}
                        >
                          <Copy className="size-3" aria-hidden />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : null}

          {snapshot.now_actions.length > 0 ? (
            <ul className="space-y-2">
              {snapshot.now_actions.map((action) => (
                <li
                  key={action.id}
                  className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-(--qs-text)">{action.label}</span>
                      <V4Badge tone={priorityTone(action.priority)}>{action.priority}</V4Badge>
                    </div>
                    <p className="mt-0.5 text-xs text-(--qs-muted)">{action.detail}</p>
                  </div>
                  {action.action ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--primary qs-btn--sm shrink-0 self-center"
                      disabled={busy === action.action}
                      onClick={() => void runAction(action.action!)}
                    >
                      Run
                    </button>
                  ) : action.href ? (
                    <Link href={action.href} className="qs-btn qs-btn--ghost qs-btn--sm shrink-0 self-center">
                      Go
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-(--qs-muted)">No priority actions right now.</p>
          )}
        </V4Card>
      ) : null}

      {section === "lanes" ? <SoloOperatorFourLanesPanel onMutate={() => void load({ silent: true })} /> : null}

      {section === "command" ? (
        <V4Card>
          <V4CardHeader
            kicker="Command lane"
            title="Hotline · Crystallizer · Zero-UI"
            description="Direct operator commands and intent routing."
            hint={<CockpitHint hintKey="command" />}
          />

        <div className="mb-4 rounded-lg border border-cyan/30 bg-cyan/5 p-3">
          <HiveSubsectionHeader
            tone="cyan"
            title="Bee Hotline"
            description="What do you need? Routes to the right bee automatically."
            hintKey="beeHotline"
          />
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={hotline}
              onChange={(e) => setHotline(e.target.value)}
              placeholder="What do you need? (routes to the right bee…)"
              className="qs-input flex-1 text-sm"
            />
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm shrink-0"
              disabled={!hotline.trim() || busy === "hotline"}
              onClick={() => void runAction("hotline", { text: hotline })}
            >
              {busy === "hotline" ? <Loader2 className="size-4 animate-spin" /> : "Run"}
            </button>
          </div>
        </div>

        {snapshot.intent_crystallizer?.enabled ? (
          <div
            className="mb-4 rounded-lg border border-[#FF00AA33] bg-[#FF00AA08] p-3"
            id="intent-crystallizer"
          >
            <HiveSubsectionHeader
              tone="magenta"
              title="Intent Crystallizer"
              description="Free text → swarm template + trust lane + deep links. Preview or launch a Queen goal."
              hintKey="intentCrystallizer"
            />
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                type="text"
                value={crystal}
                onChange={(e) => setCrystal(e.target.value)}
                placeholder="e.g. Research competitor pricing + publish brief…"
                className="qs-input flex-1 text-sm"
              />
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
                disabled={!crystal.trim() || busy === "crystal-preview"}
                onClick={() => void previewCrystal()}
              >
                {busy === "crystal-preview" ? <Loader2 className="size-4 animate-spin" /> : "Preview"}
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm shrink-0"
                disabled={!crystal.trim() || busy === "crystal-launch"}
                onClick={() => void launchCrystal()}
              >
                {busy === "crystal-launch" ? <Loader2 className="size-4 animate-spin" /> : "Launch"}
              </button>
            </div>
            {crystalPlan ? (
              <div className="mt-3 rounded border border-(--qs-border) bg-black/20 p-2 text-xs">
                <p className="font-medium text-(--qs-text)">{String(crystalPlan.title ?? "")}</p>
                <p className="mt-1 text-(--qs-muted)">
                  Trust: {String(crystalPlan.trust_lane ?? "")} · Templates:{" "}
                  {Array.isArray(crystalPlan.template_labels)
                    ? (crystalPlan.template_labels as string[]).join(", ")
                    : "—"}
                </p>
                {crystalPlan.primary_href ? (
                  <Link href={String(crystalPlan.primary_href)} className="mt-1 inline-block text-cyan hover:text-pollen">
                    Open primary →
                  </Link>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        {snapshot.zero_ui?.enabled ? (
          <div className="mb-4 rounded-lg border border-(--qs-border) bg-black/20 p-3" id="zero-ui">
            <HiveSubsectionHeader
              title="Zero-UI Hive Mode"
              description="Telegram commands — web optional. Set bot token + chat id in Execution Studio notifications."
              hintKey="zeroUi"
            />
            <div className="mt-2 flex flex-wrap gap-2">
              <V4Badge tone={snapshot.zero_ui.telegram_configured ? "ok" : "warn"}>
                Telegram {snapshot.zero_ui.telegram_configured ? "configured" : "missing"}
              </V4Badge>
              <V4Badge tone={snapshot.zero_ui.webhook_secret_configured ? "ok" : "warn"}>
                Webhook secret {snapshot.zero_ui.webhook_secret_configured ? "ok" : "missing"}
              </V4Badge>
            </div>
            {snapshot.zero_ui.webhook_url ? (
              <p className="mt-2 break-all font-mono text-[10px] text-cyan">{snapshot.zero_ui.webhook_url}</p>
            ) : null}
            {snapshot.zero_ui.commands.length > 0 ? (
              <ul className="mt-2 space-y-0.5 text-[11px] text-(--qs-muted)">
                {snapshot.zero_ui.commands.map((cmd) => (
                  <li key={cmd}>{cmd}</li>
                ))}
              </ul>
            ) : null}
            <Link
              href={snapshot.links.execution_studio ?? "/integrations?tab=studio"}
              className="mt-2 inline-block text-xs text-cyan hover:text-pollen"
            >
              Execution Studio notifications →
            </Link>
          </div>
        ) : null}
        </V4Card>
      ) : null}

      {section === "grok" ? <GrokControlPlanePanel /> : null}

      {section === "icm" && snapshot.icm_tools?.enabled ? (
        <V4Card>
          <V4CardHeader
            kicker="ICM layer"
            title="Quick automations · Link drop · Dialogue extract"
            description="Presets and ingest tools — verified actions without the builder."
            hint={<CockpitHint hintKey="icm" />}
          />
          <div className="space-y-4" id="icm-tools">
            <div className="rounded-lg border border-pollen/25 bg-pollen/5 p-3">
              <HiveSubsectionHeader
                tone="pollen"
                title="Quick Automations"
                description="Presets — no builder, verified actions only."
                hintKey="icmQuickAutomations"
              />
              <div className="mt-2 flex flex-wrap gap-2">
                {snapshot.icm_tools.quick_automations.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    title={preset.detail}
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    onClick={() => runQuickAutomation(preset)}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {snapshot.icm_tools.link_drop_enabled ? (
              <div className="rounded-lg border border-cyan/30 bg-cyan/5 p-3" id="link-drop">
                <HiveSubsectionHeader
                  tone="cyan"
                  title="Link Drop"
                  description="URL → structured brief (read-only fetch)."
                  hintKey="icmLinkDrop"
                />
                <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                  <input
                    type="url"
                    value={linkUrl}
                    onChange={(e) => setLinkUrl(e.target.value)}
                    placeholder="https://…"
                    className="flex-1 rounded border border-(--qs-border) bg-black/30 px-3 py-2 text-sm"
                  />
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={!linkUrl.trim() || busy === "link-preview"}
                    onClick={() => void runLinkDrop(false)}
                  >
                    Preview
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm"
                    disabled={!linkUrl.trim() || busy === "link-persist"}
                    onClick={() => void runLinkDrop(true)}
                  >
                    Save to Knowledge
                  </button>
                </div>
                {linkBrief ? (
                  <div className="mt-3 rounded border border-(--qs-border) bg-black/20 p-2 text-xs">
                    <p className="font-medium text-(--qs-text)">{String(linkBrief.title ?? "")}</p>
                    <p className="mt-1 text-(--qs-muted)">{String(linkBrief.summary ?? "").slice(0, 400)}</p>
                  </div>
                ) : null}
              </div>
            ) : null}

            {snapshot.icm_tools.dialogue_extract_enabled ? (
              <div className="rounded-lg border border-(--qs-border) bg-black/20 p-3" id="dialogue-extract">
                <HiveSubsectionHeader
                  title="Dialogue Extract"
                  description="Transcript → goals, constraints, decisions. Import from Ballroom or Dump & Sleep, or paste text below."
                  hintKey="icmDialogueExtract"
                />
                <textarea
                  value={dialogueText}
                  onChange={(e) => setDialogueText(e.target.value)}
                  rows={4}
                  placeholder="Paste chat or meeting transcript…"
                  className="mt-2 w-full rounded border border-(--qs-border) bg-black/30 px-3 py-2 text-sm"
                />
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={dialogueText.trim().length < (snapshot.icm_tools.min_dialogue_chars ?? 40)}
                    onClick={() => void runDialogueExtract("preview")}
                  >
                    Extract
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={dialogueText.trim().length < (snapshot.icm_tools.min_dialogue_chars ?? 40) || busy?.startsWith("dialogue-")}
                    onClick={() => void runDialogueExtract("harness")}
                  >
                    → Harness
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={dialogueText.trim().length < (snapshot.icm_tools.min_dialogue_chars ?? 40) || busy?.startsWith("dialogue-")}
                    onClick={() => void runDialogueExtract("knowledge")}
                  >
                    → Knowledge
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={dialogueText.trim().length < (snapshot.icm_tools.min_dialogue_chars ?? 40) || busy?.startsWith("dialogue-")}
                    onClick={() => void runDialogueExtract("recipe")}
                  >
                    → Recipe draft
                  </button>
                  {dialogueExtract?.task_prefill ? (
                    <Link
                      href={`/tasks/new?prefill=${encodeURIComponent(String(dialogueExtract.task_prefill))}`}
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                    >
                      → New task
                    </Link>
                  ) : null}
                </div>
                {dialogueExtract ? (
                  <div className="mt-3 space-y-3 rounded border border-(--qs-border) bg-black/40 p-2 text-xs" id="dialogue-extract-table">
                    {(
                      [
                        ["Goals", dialogueExtract.goals],
                        ["Constraints", dialogueExtract.constraints],
                        ["Decisions", dialogueExtract.decisions],
                        ["Next steps", dialogueExtract.next_steps],
                      ] as const
                    ).map(([label, items]) => {
                      const rows = Array.isArray(items) ? items.filter((row) => String(row).trim()) : [];
                      if (rows.length === 0) {
                        return null;
                      }
                      return (
                        <div key={label}>
                          <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-muted)">{label}</p>
                          <ul className="mt-1 space-y-1 text-(--qs-text)">
                            {rows.slice(0, 6).map((row, idx) => (
                              <li key={`${label}-${idx}`} className="rounded bg-black/25 px-2 py-1">
                                {String(row)}
                              </li>
                            ))}
                          </ul>
                        </div>
                      );
                    })}
                    {dialogueExtract.summary_md ? (
                      <details className="text-[11px] text-(--qs-muted)">
                        <summary className="cursor-pointer text-cyan">Full summary</summary>
                        <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap">{String(dialogueExtract.summary_md)}</pre>
                      </details>
                    ) : null}
                  </div>
                ) : null}
                {keywordMatches.length > 0 ? (
                  <ul className="mt-3 space-y-1" id="keyword-suggestions">
                    {keywordMatches.map((m) => (
                      <li key={m.id} className="flex flex-wrap items-center gap-2 text-xs">
                        <V4Badge tone={m.priority === "high" ? "err" : m.priority === "medium" ? "warn" : "info"}>
                          {m.label}
                        </V4Badge>
                        <span className="text-(--qs-muted)">{m.detail}</span>
                        {m.href ? (
                          <Link href={m.href} className="text-cyan hover:text-pollen">
                            Go →
                          </Link>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>
        </V4Card>
      ) : null}

      {section === "icm" && !snapshot.icm_tools?.enabled ? (
        <V4Card>
          <p className="text-sm text-(--qs-muted)">ICM tools are disabled on this deployment.</p>
        </V4Card>
      ) : null}

      {section === "fleet" ? (
        <>
      <V4Card id="swarm-fleet">
        <V4CardHeader
          kicker="Trust Autopilot"
          title="Swarm Fleet"
          description="Always-on routines — pause/resume without losing bees."
          hint={<CockpitHint hintKey="fleet" />}
        />
        {snapshot.swarm_fleet.length === 0 ? (
          <p className="text-xs text-(--qs-muted)">
            No routines yet —{" "}
            <Link href="/swarms/new" className="text-cyan underline">
              create a swarm
            </Link>
          </p>
        ) : (
          <ul className="space-y-2">
            {snapshot.swarm_fleet.slice(0, 12).map((row) => (
              <li
                key={row.routine_id}
                className="flex flex-col gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm"
              >
                <div className="min-w-0">
                  <span className="font-medium text-(--qs-text)">{row.name}</span>
                  <p className="text-xs text-(--qs-muted)">
                    {row.schedule_kind} · {row.autopilot ? "autopilot" : "manual"}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <V4Badge tone={row.active ? "ok" : "warn"}>{row.active ? "ON" : "OFF"}</V4Badge>
                  <V4Badge tone={immuneTone(row.immune_status)}>{row.immune_status}</V4Badge>
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={busy === row.routine_id}
                    onClick={() =>
                      void runAction(row.active ? "pause_routine" : "resume_routine", {
                        routine_id: row.routine_id,
                      })
                    }
                  >
                    {row.active ? "Pause" : "Resume"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </V4Card>

      {snapshot.swarm_immune_system?.enabled ? (
        <V4Card id="swarm-immune-system">
          <V4CardHeader
            kicker="Swarm Immune System"
            title={`${snapshot.swarm_immune_system.healthy_count} healthy · ${snapshot.swarm_immune_system.watch_count} watch · ${snapshot.swarm_immune_system.quarantine_count} quarantine`}
            description={snapshot.swarm_immune_system.summary}
          />
          {snapshot.swarm_immune_system.routines.length > 0 ? (
            <ul className="space-y-2">
              {snapshot.swarm_immune_system.routines.map((row) => (
                <li key={row.routine_id} className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-(--qs-text)">{row.name}</span>
                    <V4Badge tone={immuneTone(row.immune_status as SwarmFleetItem["immune_status"])}>
                      {row.immune_status}
                    </V4Badge>
                  </div>
                  <p className="mt-0.5 text-(--qs-muted)">{row.recommendation}</p>
                </li>
              ))}
            </ul>
          ) : null}
        </V4Card>
      ) : null}
        </>
      ) : null}

      {section === "modules" ? (
        <>
      {modulesLoading && !modulesHydrated ? (
        <V4Card>
          <V4CardHeader
            kicker="Capabilities"
            title="Futurist modules"
            description="Loading experimental modules…"
            hint={<CockpitHint hintKey="modules" />}
          />
          <div className="flex min-h-32 items-center justify-center gap-2 text-sm text-(--qs-muted)">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Loading futurist modules…
          </div>
        </V4Card>
      ) : null}
      {snapshot.evolutionary_recipes?.enabled ? (
        <V4Card id="evolutionary-recipes">
          <V4CardHeader
            kicker="Evolutionary Recipes"
            title={
              snapshot.evolutionary_recipes.ready
                ? `${snapshot.evolutionary_recipes.variants.length} competing variants`
                : "Collecting verified outcomes"
            }
            description={snapshot.evolutionary_recipes.summary}
          />
          {snapshot.evolutionary_recipes.variants.length > 0 ? (
            <ul className="space-y-2">
              {snapshot.evolutionary_recipes.variants.map((variant) => (
                <li key={`${variant.recipe_id ?? variant.name}-${variant.fitness_rank}`} className="rounded-lg border border-pollen/30 bg-pollen/5 px-3 py-2 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-(--qs-text)">#{variant.fitness_rank} {variant.name}</span>
                    <V4Badge tone="ok">{Math.round(variant.similarity * 100)}% match</V4Badge>
                  </div>
                  <p className="mt-0.5 text-(--qs-muted)">{variant.detail}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-(--qs-muted)">
              {snapshot.evolutionary_recipes.verified_outcomes} verified outcomes — need 3+ to rank variants.
            </p>
          )}
        </V4Card>
      ) : null}

      {snapshot.regret_simulator?.enabled ? (
        <V4Card id="regret-simulator">
          <V4CardHeader
            kicker="Regret Simulator"
            title={`Score ${snapshot.regret_simulator.regret_score}/100 · ${snapshot.regret_simulator.recommendation}`}
            description={snapshot.regret_simulator.summary}
          />
          <ul className="space-y-2">
            {snapshot.regret_simulator.scenarios.map((row) => (
              <li key={row.id} className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-xs">
                <span className="font-medium text-(--qs-text)">{row.label}</span>
                <p className="mt-0.5 text-(--qs-muted)">{row.detail}</p>
              </li>
            ))}
          </ul>
        </V4Card>
      ) : null}

      {snapshot.context_teleport?.enabled && snapshot.context_teleport.packs.length > 0 ? (
        <V4Card id="context-teleport">
          <V4CardHeader
            kicker="Context Teleport"
            title="Cross-swarm packs"
            description="Verified recipe fragments ready to inject."
          />
          <ul className="space-y-2">
            {snapshot.context_teleport.packs.slice(0, 4).map((pack) => (
              <li key={pack.pack_id} className="rounded-lg border border-cyan/30 bg-cyan/5 px-3 py-2 text-xs">
                <span className="font-medium text-(--qs-text)">{pack.recipe_name}</span>
                <p className="mt-0.5 text-(--qs-muted)">{pack.excerpt}</p>
              </li>
            ))}
          </ul>
        </V4Card>
      ) : null}

      {snapshot.ambient_forager?.enabled && snapshot.ambient_forager.items.length > 0 ? (
        <V4Card id="ambient-forager">
          <V4CardHeader
            kicker="Ambient Forager"
            title={`${snapshot.ambient_forager.item_count} relevance signals`}
            description="Passive scan — morning brief without spam."
          />
          <ul className="space-y-2">
            {snapshot.ambient_forager.items.map((item) => (
              <li key={item.id} className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-xs">
                <span className="font-medium text-(--qs-text)">{item.title}</span>
                <p className="mt-0.5 text-(--qs-muted)">{item.detail}</p>
              </li>
            ))}
          </ul>
        </V4Card>
      ) : null}

      {snapshot.parallel_hive_view?.enabled && snapshot.parallel_hive_view.sessions.length > 0 ? (
        <V4Card id="parallel-hive">
          <V4CardHeader
            kicker="Parallel Hive View"
            title={`${snapshot.parallel_hive_view.active_count} active sessions`}
            description="Mission control — open session for merge/approve."
          />
          <ul className="space-y-2">
            {snapshot.parallel_hive_view.sessions.slice(0, 6).map((sess) => (
              <li key={sess.session_id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-xs">
                <div className="min-w-0">
                  <span className="font-medium text-(--qs-text)">{sess.goal}</span>
                  <p className="text-(--qs-muted)">{sess.status}{sess.merge_ready ? " · merge ready" : ""}</p>
                </div>
                <Link href={`/agents?session=${sess.session_id}`} className="qs-btn qs-btn--ghost qs-btn--sm">
                  Open
                </Link>
              </li>
            ))}
          </ul>
        </V4Card>
      ) : null}

      <V4Card>
        <V4CardHeader
          kicker="Capabilities"
          title="Futurist modules"
          description="Compose-only — existing bees and swarms unchanged."
          hint={<CockpitHint hintKey="modules" />}
        />
        <div className="flex flex-wrap gap-2">
          {snapshot.feature_modules.map((mod) => (
            <V4Badge key={mod.id} tone={mod.enabled ? "ok" : "info"}>
              {mod.label} · {mod.status}
            </V4Badge>
          ))}
        </div>
      </V4Card>
        </>
      ) : null}

      {section === "innovation" ? (
      <V4Card id="innovation-lab" className="relative">
        <V4CardHeader
          kicker="Innovation Lab"
          title="Brainstorm → approve → auto-implement"
          description="Propose a new feature — after approval, Queen Maintainer implements via PR."
          hint={<CockpitHint hintKey="innovation" />}
          actions={
            <V4Badge tone={snapshot.innovation_lab.pending_count > 0 ? "warn" : "ok"}>
              {snapshot.innovation_lab.pending_count} pending
            </V4Badge>
          }
        />
        <InnovationLabPanel onMutate={() => void load({ silent: true })} />
        <div className="mt-6 flex justify-end border-t border-(--qs-border) pt-4">
          <Link
            href={executionStudioSectionHref("innovation")}
            className="qs-btn qs-btn--primary qs-btn--sm gap-1"
          >
            Execution Studio
            <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>
      </V4Card>
      ) : null}
      </HiveSubnavContent>
    </HivePageShell>
  );
}

export const OperatorCockpitPanel = memo(OperatorCockpitPanelInner);
OperatorCockpitPanel.displayName = "OperatorCockpitPanel";
