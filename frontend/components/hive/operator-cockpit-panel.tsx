"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
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

  const load = useCallback(async () => {
    setLoading(true);
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
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

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
