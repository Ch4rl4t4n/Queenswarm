"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowRight,
  Hexagon,
  Lightbulb,
  Loader2,
  Play,
  RefreshCw,
  Rocket,
  Sparkles,
  Copy,
} from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { useRouteScopedPollOptions } from "@/lib/hooks/use-route-scoped-poll";
import { cn } from "@/lib/utils";

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

interface InnovationProposal {
  id: string;
  title: string;
  status: string;
  risk_level: string;
  feature_modules: string[];
  implementation_plan_md: string;
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

function OperatorCockpitPanelInner() {
  const [snapshot, setSnapshot] = useState<OperatorCockpitSnapshot | null>(null);
  const [proposals, setProposals] = useState<InnovationProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [hotline, setHotline] = useState("");
  const [brainstorm, setBrainstorm] = useState("");
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

  const load = useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) {
      setLoading(true);
    }
    try {
      const [cockpit, lab] = await Promise.all([
        hiveGet<OperatorCockpitSnapshot>("operator/cockpit"),
        hiveGet<{ proposals: InnovationProposal[] }>("operator/innovation-lab"),
      ]);
      setSnapshot(cockpit);
      setProposals(lab.proposals ?? []);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Cockpit unavailable");
    } finally {
      if (!opts?.silent) {
        setLoading(false);
      }
    }
  }, []);

  const pollOpts = useRouteScopedPollOptions(COCKPIT_POLL_COLONY_TELEMETRY_MS, "/cockpit");

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const ballroomSession = searchParams.get("ballroom_session")?.trim();
    if (!ballroomSession || dialogueText.trim().length >= 40) {
      return;
    }
    let cancelled = false;
    void hiveGet<{ ok: boolean; text: string }>(`operator/ballroom/${encodeURIComponent(ballroomSession)}/transcript-text`)
      .then((body) => {
        if (cancelled || !body.text?.trim()) {
          return;
        }
        setDialogueText(body.text);
        document.getElementById("dialogue-extract")?.scrollIntoView({ behavior: "smooth" });
        toast.success("Ballroom transcript loaded — run Extract.");
      })
      .catch((e) => {
        if (!cancelled) {
          toast.error(e instanceof HiveApiError ? e.message : "Ballroom transcript unavailable");
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
      toast.error("Zadaj platnú URL.");
      return;
    }
    setBusy(persist ? "link-persist" : "link-preview");
    try {
      const result = await hivePostJson<{ ok: boolean; brief: Record<string, unknown> }>("operator/link-drop", {
        url,
        persist,
      });
      setLinkBrief(result.brief);
      toast.success(persist ? "Brief uložený do Knowledge." : "Link brief pripravený.");
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
        toast.error(`Min. ${min} znakov dialógu.`);
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
        if (apply === "harness") toast.success("Pridané do harness memory.");
        else if (apply === "knowledge") toast.success("Uložené do Knowledge.");
        else if (apply === "recipe") {
          toast.success("Recipe draft uložený.");
          if (result.applied?.href) window.location.href = result.applied.href;
        } else toast.success("Dialogue extract hotový.");
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

  const submitBrainstorm = useCallback(async () => {
    const prompt = brainstorm.trim();
    if (prompt.length < 8) {
      toast.error("Min. 8 znakov pre brainstorm.");
      return;
    }
    setBusy("brainstorm");
    try {
      await hivePostJson("operator/innovation-lab/brainstorm", { prompt, category: "feature" });
      toast.success("Návrh vytvorený — schváľ a implementuj.");
      setBrainstorm("");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Brainstorm failed");
    } finally {
      setBusy(null);
    }
  }, [brainstorm, load]);

  const reviewProposal = useCallback(
    async (id: string, decision: "approved" | "rejected") => {
      setBusy(id);
      try {
        await hivePostJson(`operator/innovation-lab/proposals/${id}/review`, { decision });
        toast.success(decision === "approved" ? "Schválené" : "Zamietnuté");
        await load();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Review failed");
      } finally {
        setBusy(null);
      }
    },
    [load],
  );

  const implementProposal = useCallback(
    async (id: string) => {
      setBusy(`impl-${id}`);
      try {
        const result = await hivePostJson<{ ok: boolean; handoff?: { session_id?: string } }>(
          `operator/innovation-lab/proposals/${id}/implement`,
          {},
        );
        if (result.ok) {
          toast.success("Queen Maintainer queued — PR-only implementácia.");
          await load();
        } else {
          toast.error("Implementácia zlyhala — skontroluj Maintainer.");
        }
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Implement failed");
      } finally {
        setBusy(null);
      }
    },
    [load],
  );

  const copyProofLink = useCallback(async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Proof link skopírovaný");
    } catch {
      toast.error("Kopírovanie zlyhalo");
    }
  }, []);

  if (loading && !snapshot) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden /> Loading Hive Cockpit…
      </p>
    );
  }

  if (!snapshot?.enabled) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-muted)">Operator Control Plane is disabled on this deployment.</p>
      </V4Card>
    );
  }

  const trioBound = snapshot.trio.lanes_bound ?? snapshot.trio.bound_lane_count ?? 0;

  return (
    <div className="space-y-6">
      <V4Card>
        <V4CardHeader
          kicker="Control Plane"
          title="Hive Cockpit"
          description="Jeden vstup — všetky včely, swarms a Factory. Advanced UI ostáva nezmenené."
        />
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <V4Badge tone="info">
            <Hexagon className="mr-1 inline size-3" aria-hidden />
            3 Bees {trioBound}/3
          </V4Badge>
          <V4Badge tone={snapshot.innovation_lab.pending_count > 0 ? "warn" : "ok"}>
            Innovation {snapshot.innovation_lab.pending_count} pending
          </V4Badge>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => void load()}>
            <RefreshCw className={cn("size-4", loading && "animate-spin")} aria-hidden />
            Refresh
          </button>
          <Link href={snapshot.links.advanced_dashboard ?? "/dashboard"} className="qs-btn qs-btn--ghost qs-btn--sm">
            Advanced dashboard
          </Link>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm gap-1"
            disabled={busy === "start_day"}
            onClick={() => void runAction("start_day")}
          >
            {busy === "start_day" ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
            Spusti deň
          </button>
          <Link href={snapshot.links.factory ?? "/factory"} className="qs-btn qs-btn--ghost qs-btn--sm gap-1">
            <Rocket className="size-4" /> Factory
          </Link>
          <Link href={snapshot.links.swarms ?? "/swarms"} className="qs-btn qs-btn--ghost qs-btn--sm">
            Swarms
          </Link>
          <Link href={snapshot.links.agents ?? "/agents"} className="qs-btn qs-btn--ghost qs-btn--sm">
            Agents
          </Link>
        </div>

        <div className="mb-4 rounded-lg border border-cyan/30 bg-cyan/5 p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan">Bee Hotline</p>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={hotline}
              onChange={(e) => setHotline(e.target.value)}
              placeholder="Čo potrebuješ? (routuje na správnu včelu…)"
              className="qs-input flex-1 text-sm"
            />
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm shrink-0"
              disabled={!hotline.trim() || busy === "hotline"}
              onClick={() => void runAction("hotline", { text: hotline })}
            >
              {busy === "hotline" ? <Loader2 className="size-4 animate-spin" /> : "Spusti"}
            </button>
          </div>
        </div>

        {snapshot.intent_crystallizer?.enabled ? (
          <div
            className="mb-4 rounded-lg border border-[#FF00AA33] bg-[#FF00AA08] p-3"
            id="intent-crystallizer"
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-[#FF00AA]">Intent Crystallizer</p>
            <p className="mt-1 text-xs text-(--qs-muted)">
              Voľný text → swarm template + trust lane + deep links. Preview alebo Launch Queen goal.
            </p>
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                type="text"
                value={crystal}
                onChange={(e) => setCrystal(e.target.value)}
                placeholder="Napr. Research competitor pricing + publish brief…"
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

        {snapshot.icm_tools?.enabled ? (
          <div className="mb-4 space-y-4" id="icm-tools">
            <div className="rounded-lg border border-pollen/25 bg-pollen/5 p-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-pollen">Quick Automations</p>
              <p className="mt-1 text-xs text-(--qs-muted)">Presety — žiadny builder, len overené akcie.</p>
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
                <p className="text-xs font-semibold uppercase tracking-wider text-cyan">Link Drop</p>
                <p className="mt-1 text-xs text-(--qs-muted)">URL → structured brief (read-only fetch).</p>
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
                <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Dialogue Extract</p>
                <p className="mt-1 text-xs text-(--qs-muted)">
                  Transcript → ciele, constraints, rozhodnutia. V Ballroom klikni „Dialogue Extract“ alebo vlož text nižšie.
                </p>
                <textarea
                  value={dialogueText}
                  onChange={(e) => setDialogueText(e.target.value)}
                  rows={4}
                  placeholder="Vlož chat alebo meeting transcript…"
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
                  <pre className="mt-3 max-h-48 overflow-auto rounded border border-(--qs-border) bg-black/40 p-2 text-[11px] text-(--qs-muted) whitespace-pre-wrap">
                    {String(dialogueExtract.summary_md ?? "")}
                  </pre>
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
                        {m.action === "dialogue_extract_hint" ? (
                          <button
                            type="button"
                            className="text-cyan hover:text-pollen"
                            onClick={() => document.getElementById("dialogue-extract")?.scrollIntoView({ behavior: "smooth" })}
                          >
                            Extract →
                          </button>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        {snapshot.zero_ui?.enabled ? (
          <div className="mb-4 rounded-lg border border-(--qs-border) bg-black/20 p-3" id="zero-ui">
            <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Zero-UI Hive Mode</p>
            <p className="mt-1 text-xs text-(--qs-muted)">
              Telegram príkazy — web voliteľný. Nastav bot token + chat id v Execution Studio notifications.
            </p>
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

        {snapshot.trust_autopilot?.enabled ? (
          <div className="mb-4 rounded-lg border border-pollen/30 bg-pollen/5 p-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-pollen">Trust Autopilot</p>
            <p className="mt-1 text-xs text-(--qs-muted)">
              Priority Telegram pingy len po verified outcomes — bez spamu.
            </p>
            <ul className="mt-2 space-y-0.5 text-[11px] text-(--qs-muted)">
              {Object.entries(snapshot.trust_autopilot.lanes ?? {}).map(([key, label]) => (
                <li key={key}>{label}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {snapshot.proof_of_hive?.enabled ? (
          <div className="mb-4 rounded-lg border border-[#00FF8833] bg-[#00FF8808] p-3" id="proof-of-hive">
            <p className="text-xs font-semibold uppercase tracking-wider text-[#00FF88]">Proof-of-Hive</p>
            <p className="mt-1 text-xs text-(--qs-muted)">
              Shareable verify receipts — HMAC podpis, verify-first outcomes.
            </p>
            {snapshot.proof_of_hive.receipts.length === 0 ? (
              <p className="mt-2 text-[11px] text-(--qs-muted)">
                Zatiaľ žiadne receipts — vzniknú po schválení/simulate publish packu.
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

        {snapshot.oracle_warnings.length > 0 ? (
          <div className="mb-4 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-pollen">Hive Oracle</p>
              <Link href="/oracle" className="text-xs text-cyan hover:text-pollen">
                Full Oracle →
              </Link>
            </div>
            {snapshot.oracle_warnings.map((w) => (
              <div
                key={w.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-pollen/30 bg-pollen/5 px-3 py-2 text-xs"
              >
                <span>{w.message}</span>
                {w.fix_href ? (
                  <Link href={w.fix_href} className="text-cyan hover:text-pollen">
                    Fix
                  </Link>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}

        {snapshot.now_actions.length > 0 ? (
          <ul className="space-y-2">
            {snapshot.now_actions.map((action) => (
              <li
                key={action.id}
                className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-(--qs-text)">{action.label}</span>
                    <V4Badge tone={priorityTone(action.priority)}>{action.priority}</V4Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-(--qs-muted)">{action.detail}</p>
                </div>
                {action.action === "start_day" ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm"
                    disabled={busy === "start_day"}
                    onClick={() => void runAction("start_day")}
                  >
                    Run
                  </button>
                ) : action.href ? (
                  <Link href={action.href} className="qs-btn qs-btn--ghost qs-btn--sm">
                    Go
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
      </V4Card>

      <V4Card id="swarm-fleet">
        <V4CardHeader
          kicker="Trust Autopilot"
          title="Swarm Fleet"
          description="Always-on routines — pause/resume bez straty včiel."
        />
        {snapshot.swarm_fleet.length === 0 ? (
          <p className="text-xs text-(--qs-muted)">
            Žiadne routines —{" "}
            <Link href="/swarms/new" className="text-cyan underline">
              vytvor swarm
            </Link>
          </p>
        ) : (
          <ul className="space-y-2">
            {snapshot.swarm_fleet.slice(0, 12).map((row) => (
              <li
                key={row.routine_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm"
              >
                <div>
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
          description="Compose-only — existujúce bees & swarms ostávajú."
        />
        <div className="flex flex-wrap gap-2">
          {snapshot.feature_modules.map((mod) => (
            <V4Badge key={mod.id} tone={mod.enabled ? "ok" : "info"}>
              {mod.label} · {mod.status}
            </V4Badge>
          ))}
        </div>
      </V4Card>

      <V4Card id="innovation-lab">
        <V4CardHeader
          kicker="Innovation Lab"
          title="Brainstorm → approve → auto-implement"
          description="Navrhni novú funkciu — po schválení Queen Maintainer zapracuje cez PR."
        />
        <div className="mb-4 space-y-2">
          <textarea
            value={brainstorm}
            onChange={(e) => setBrainstorm(e.target.value)}
            rows={3}
            placeholder="Napr.: Pridaj Telegram inbound pre Bee Hotline s trust lanes…"
            className="qs-input w-full text-sm"
          />
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm gap-1"
            disabled={busy === "brainstorm"}
            onClick={() => void submitBrainstorm()}
          >
            {busy === "brainstorm" ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Lightbulb className="size-4" />
            )}
            Brainstorm
          </button>
        </div>
        {proposals.length === 0 ? (
          <p className="text-xs text-(--qs-muted)">Zatiaľ žiadne návrhy.</p>
        ) : (
          <ul className="space-y-3">
            {proposals.map((p) => (
              <li key={p.id} className="rounded-lg border border-(--qs-border) bg-black/20 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-(--qs-text)">{p.title}</p>
                    <p className="mt-1 text-xs text-(--qs-muted)">
                      {p.status} · risk {p.risk_level} · {p.feature_modules.join(", ")}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {p.status === "pending" ? (
                      <>
                        <button
                          type="button"
                          className="qs-btn qs-btn--primary qs-btn--sm"
                          disabled={busy === p.id}
                          onClick={() => void reviewProposal(p.id, "approved")}
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          className="qs-btn qs-btn--ghost qs-btn--sm"
                          disabled={busy === p.id}
                          onClick={() => void reviewProposal(p.id, "rejected")}
                        >
                          Reject
                        </button>
                      </>
                    ) : null}
                    {p.status === "approved" ? (
                      <button
                        type="button"
                        className="qs-btn qs-btn--primary qs-btn--sm gap-1"
                        disabled={busy === `impl-${p.id}`}
                        onClick={() => void implementProposal(p.id)}
                      >
                        <Sparkles className="size-3.5" /> Implement
                      </button>
                    ) : null}
                  </div>
                </div>
                {p.implementation_plan_md ? (
                  <pre className="mt-2 max-h-32 overflow-auto font-mono text-[10px] text-(--qs-text-3)">
                    {p.implementation_plan_md.slice(0, 800)}
                  </pre>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        <Link
          href={snapshot.links.execution_studio ?? "/integrations?tab=studio"}
          className="mt-3 inline-flex items-center gap-1 text-xs text-cyan hover:text-pollen"
        >
          Execution Studio <ArrowRight className="size-3" aria-hidden />
        </Link>
      </V4Card>
    </div>
  );
}

export const OperatorCockpitPanel = memo(OperatorCockpitPanelInner);
OperatorCockpitPanel.displayName = "OperatorCockpitPanel";

const LazyOperatorCockpitPanel = dynamic(() => Promise.resolve({ default: OperatorCockpitPanel }), {
  ssr: false,
  loading: () => (
    <p className="flex items-center gap-2 text-sm text-(--qs-muted)">
      <Loader2 className="size-4 animate-spin" aria-hidden /> Loading Hive Cockpit…
    </p>
  ),
});

export { LazyOperatorCockpitPanel };
