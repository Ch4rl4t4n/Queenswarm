"use client";

import {
  Archive,
  BookOpenText,
  Copy,
  Download,
  Loader2,
  PencilLine,
  Play,
  Save,
  ShieldCheck,
  ShieldX,
  Square,
  Terminal,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { InfoHint } from "@/components/hive/info-hint";
import { HiveApiError, hiveDelete, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";

interface GrokRunStep {
  id: string;
  title: string;
  kind: "plan" | "command" | "verify" | "deploy";
  status: "pending" | "running" | "done" | "failed" | "skipped";
  command: string | null;
  output: string | null;
  exit_code: number | null;
}

interface GrokRunEvent {
  at: string;
  level: "info" | "warning" | "error" | "success";
  code: string;
  message: string;
}

interface GrokRun {
  id: string;
  objective: string;
  run_mode: "read_only" | "code_edit" | "code_edit_and_test" | "deploy_candidate" | "prod_deploy";
  risk_level: "low" | "medium" | "high" | "critical";
  command_profile: string;
  status: "draft" | "awaiting_approval" | "approved" | "running" | "succeeded" | "failed" | "cancelled" | "rejected";
  created_at: string;
  updated_at: string;
  steps: GrokRunStep[];
  events: GrokRunEvent[];
  artifacts?: Array<{
    id: string;
    kind: string;
    title: string;
    mime_type: string;
    content_text: string | null;
  }>;
  metadata?: Record<string, unknown>;
}

interface GrokApproval {
  id: string;
  decision: string;
  decided_by: string;
  note: string | null;
  decided_at: string | null;
}

interface GrokSnapshot {
  enabled: boolean;
  cli_available: boolean;
  active_runs: number;
  draft_runs: number;
  failed_runs: number;
  failed_alert_threshold?: number;
  health_level?: "ok" | "warn" | "error";
  available_context_sources?: string[];
  guardrails: {
    command_allow_profiles: string[];
    require_approval_for_risk: string[];
    deny_patterns: string[];
    allow_prod_deploy: boolean;
  };
  governance?: {
    window_hours?: number;
    estimated_cost_usd?: number;
    cost_cap_usd?: number;
    cost_utilization?: number;
    cost_cap_breached?: boolean;
    timeout_breaches?: number;
    timeout_threshold?: number;
    timeout_escalated?: boolean;
    high_risk_runs?: number;
    risk_threshold?: number;
    risk_escalated?: boolean;
    escalation_resumes_24h?: number;
    timeout_trend?: "up" | "down" | "flat";
    risk_trend?: "up" | "down" | "flat";
    resume_trend?: "up" | "down" | "flat";
  };
  last_resumed_escalation?: {
    run_id?: string;
    escalation_kind?: string;
    resumed_at?: string;
    remaining_ttl_hours?: number;
  } | null;
}

interface GrokTemplate {
  id: string;
  name: string;
  description: string | null;
  objective: string;
  scope_paths: string[];
  run_mode: GrokRun["run_mode"];
  risk_level: GrokRun["risk_level"];
  command_profile: string;
  context_sources: string[];
  tags: string[];
  usage_count: number;
  is_archived: boolean;
  last_used_at: string | null;
  updated_at: string;
}

interface GrokIntakeAdviceCandidate {
  source_type: "task" | "recipe" | "knowledge" | "grok_run";
  source_id: string;
  title: string;
  score: number;
  status: string | null;
  updated_at: string | null;
}

interface GrokIntakeAdvice {
  dedup_score: number;
  recommendation: "reuse" | "hybrid" | "new";
  rationale: string;
  top_candidates: GrokIntakeAdviceCandidate[];
  context_sources: string[];
  hard_gate_enabled?: boolean;
  hard_gate_blocked?: boolean;
  thresholds?: {
    reuse?: number;
    hybrid?: number;
  };
}

interface GrokHiveMindReviewItem {
  knowledge_item_id: string;
  source_url: string | null;
  confidence_score: number;
  priority: "high" | "medium" | "low";
  preview: string;
  topic_tags: string[];
  created_at: string;
  updated_at: string;
}

interface GrokHiveMindReviewQueue {
  count: number;
  oldest_pending_age_hours?: number;
  sla_hours?: number;
  sla_breached?: boolean;
  items: GrokHiveMindReviewItem[];
}

interface StudioActivity {
  event_type: string;
  message: string;
  at: string;
  payload?: Record<string, unknown>;
}

interface StudioOverviewLite {
  recent_activity?: StudioActivity[];
}

const MODE_OPTIONS: Array<GrokRun["run_mode"]> = [
  "read_only",
  "code_edit",
  "code_edit_and_test",
  "deploy_candidate",
  "prod_deploy",
];
const RISK_OPTIONS: Array<GrokRun["risk_level"]> = ["low", "medium", "high", "critical"];
const ARTIFACT_KIND_OPTIONS = ["all", "context", "plan", "command_log", "summary"] as const;
const TEMPLATE_PAGE_SIZE = 8;
const ESCALATION_COOLDOWN_MS = 10 * 60 * 1000;
const MANUAL_HINT_OPTIONS = [
  "read_only: audit a mapovanie bez zásahu do súborov.",
  "code_edit: menšie zmeny v konkrétnom scope.",
  "code_edit_and_test: bezpečný default pre väčšinu vývoja.",
  "deploy_candidate: release kandidát bez priameho production deploy kroku.",
  "prod_deploy: iba po approvals + explicitných guardrails.",
  "Risk low/medium: bežné zmeny; high/critical: povinné schválenie.",
];
const DEFAULT_CONTEXT_SOURCES = ["tasks", "swarms", "recipes", "knowledge", "grok_history"];

const RUN_MODE_GUIDE: Array<{ mode: GrokRun["run_mode"]; when: string; execution: string }> = [
  {
    mode: "read_only",
    when: "Audit, analýza root-cause, zber kontextu pred implementáciou.",
    execution: "Start (plan-only)",
  },
  {
    mode: "code_edit",
    when: "Malý fix alebo izolovaná úprava v 1-2 moduloch.",
    execution: "Start (with commands) po overení scope a profilu.",
  },
  {
    mode: "code_edit_and_test",
    when: "Štandardný vývoj: implementácia + verifikácia testami/lintom.",
    execution: "Preferovaný default pre väčšinu taskov.",
  },
  {
    mode: "deploy_candidate",
    when: "Príprava release kandidáta, smoke check a deployment artefaktov.",
    execution: "Najprv plan-only, potom command run po schválení.",
  },
  {
    mode: "prod_deploy",
    when: "Priamy produkčný zásah s jasným rollback plánom.",
    execution: "Len pri explicitnom schválení a zapnutých guardrails.",
  },
];

type GrokPreset = {
  id: string;
  label: string;
  objective: string;
  scopePaths: string;
  runMode: GrokRun["run_mode"];
  riskLevel: GrokRun["risk_level"];
  commandProfile: string;
};

type EscalationKind = "review_queue_sla" | "governance_cost" | "governance_timeout" | "governance_risk";

const RUN_ID_PATTERN = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i;

const GROK_PRESETS: GrokPreset[] = [
  {
    id: "readonly-audit",
    label: "Read-only audit",
    objective: "Audituj auth a API guardrails, identifikuj riziká a navrhni fixy bez zásahu do kódu.",
    scopePaths: "backend/app/presentation/api,backend/app/core",
    runMode: "read_only",
    riskLevel: "low",
    commandProfile: "ci_quick",
  },
  {
    id: "safe-fix",
    label: "Safe bugfix + tests",
    objective: "Oprav regresiu v API route a over cez cielené testy a lint.",
    scopePaths: "backend/app/presentation/api,backend/tests",
    runMode: "code_edit_and_test",
    riskLevel: "medium",
    commandProfile: "ci_quick",
  },
  {
    id: "release-candidate",
    label: "Release candidate",
    objective: "Priprav release kandidáta vrátane changelog summary, test evidence a deploy checklistu.",
    scopePaths: "backend,frontend,scripts",
    runMode: "deploy_candidate",
    riskLevel: "high",
    commandProfile: "release_safe",
  },
  {
    id: "publish-template-pack",
    label: "Publish template pack",
    objective:
      "Vytvor Grok template pack pre publish lane (audit/fix/release/security), pridaj acceptance criteria a anti-dup odporucania pre kazdu sablonu.",
    scopePaths:
      "backend/app/application/services/grok_control_plane.py,frontend/components/hive/grok-control-plane-panel.tsx,docs",
    runMode: "code_edit_and_test",
    riskLevel: "medium",
    commandProfile: "ci_quick",
  },
  {
    id: "publish-variant-generator",
    label: "Publish variants",
    objective:
      "Vygeneruj 3-5 publish variantov pre X/Telegram/Notion/Webhook, zachovaj core message, uprav CTA podla kanala a navrhni scoring pre auto-vyber.",
    scopePaths:
      "backend/app/application/services/social_publish.py,backend/app/application/services/publish_pack.py,frontend/components/connectors/execution-studio-social-publish-panel.tsx",
    runMode: "code_edit_and_test",
    riskLevel: "medium",
    commandProfile: "ci_quick",
  },
  {
    id: "publish-pipeline-governance",
    label: "Publish governance",
    objective:
      "Over publish pipeline guardrails: approval gates, rollback receipts, audit events a fail-fast spravanie pre multi-target orchestration.",
    scopePaths:
      "backend/app/application/services/social_publish_pipeline.py,backend/app/application/services/publish_audit.py,backend/app/presentation/api/routers/social_publish.py",
    runMode: "code_edit_and_test",
    riskLevel: "high",
    commandProfile: "release_safe",
  },
];

function runTone(status: GrokRun["status"]): "ok" | "warn" | "err" | "info" {
  if (status === "succeeded") return "ok";
  if (status === "failed" || status === "rejected") return "err";
  if (status === "awaiting_approval" || status === "running") return "warn";
  return "info";
}

function healthTone(level: GrokSnapshot["health_level"]): "ok" | "warn" | "err" | "info" {
  if (level === "error") return "err";
  if (level === "warn") return "warn";
  if (level === "ok") return "ok";
  return "info";
}

function resumedRunExpirySuffix(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return "";
  }
  return ` · expiruje za ${Math.ceil(value)}h`;
}

function trendIcon(value: "up" | "down" | "flat" | undefined): string {
  if (value === "up") return "↑";
  if (value === "down") return "↓";
  return "→";
}

export function GrokControlPlanePanel() {
  const [snapshot, setSnapshot] = useState<GrokSnapshot | null>(null);
  const [runs, setRuns] = useState<GrokRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const [objective, setObjective] = useState("");
  const [scopePaths, setScopePaths] = useState("");
  const [runMode, setRunMode] = useState<GrokRun["run_mode"]>("code_edit_and_test");
  const [riskLevel, setRiskLevel] = useState<GrokRun["risk_level"]>("medium");
  const [commandProfile, setCommandProfile] = useState("ci_quick");
  const [contextSources, setContextSources] = useState<string[]>(DEFAULT_CONTEXT_SOURCES);
  const [forceFreshRun, setForceFreshRun] = useState(false);
  const [templateIdForRun, setTemplateIdForRun] = useState<string | null>(null);
  const [artifactKind, setArtifactKind] = useState<(typeof ARTIFACT_KIND_OPTIONS)[number]>("all");
  const [approvals, setApprovals] = useState<GrokApproval[]>([]);
  const [templates, setTemplates] = useState<GrokTemplate[]>([]);
  const [showArchivedTemplates, setShowArchivedTemplates] = useState(false);
  const [templateQuery, setTemplateQuery] = useState("");
  const [templateOffset, setTemplateOffset] = useState(0);
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [intakeAdvice, setIntakeAdvice] = useState<GrokIntakeAdvice | null>(null);
  const [reviewQueueMeta, setReviewQueueMeta] = useState<{
    count: number;
    oldestPendingAgeHours: number;
    slaHours: number;
    slaBreached: boolean;
  }>({ count: 0, oldestPendingAgeHours: 0, slaHours: 24, slaBreached: false });
  const [reviewQueue, setReviewQueue] = useState<GrokHiveMindReviewItem[]>([]);
  const [browserGoal, setBrowserGoal] = useState("Verify connector fallback flow for Grok operator lane.");
  const [browserStartUrl, setBrowserStartUrl] = useState("https://queenswarm.love");
  const [browserMode, setBrowserMode] = useState<"draft" | "simulate" | "live">("simulate");
  const [browserConfirmLive, setBrowserConfirmLive] = useState(false);
  const [browserResult, setBrowserResult] = useState<string | null>(null);
  const [browserAudit, setBrowserAudit] = useState<StudioActivity[]>([]);
  const [lastEscalationResume, setLastEscalationResume] = useState<{
    kind: EscalationKind;
    runId: string;
    at: number;
  } | null>(null);

  const selectedRun = useMemo(
    () => runs.find((row) => row.id === selectedRunId) ?? null,
    [runs, selectedRunId],
  );

  const loadTemplates = useCallback(async () => {
    const params = new URLSearchParams({
      limit: String(TEMPLATE_PAGE_SIZE),
      offset: String(templateOffset),
      include_archived: String(showArchivedTemplates),
    });
    if (showArchivedTemplates) {
      params.set("archived_only", "true");
    }
    if (templateQuery.trim()) {
      params.set("query", templateQuery.trim());
    }
    const rows = await hiveGet<GrokTemplate[]>(`operator/grok/templates?${params.toString()}`);
    setTemplates(rows);
  }, [templateOffset, showArchivedTemplates, templateQuery]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextSnapshot, nextRuns, studioOverview] = await Promise.all([
        hiveGet<GrokSnapshot>("operator/grok/snapshot"),
        hiveGet<GrokRun[]>("operator/grok/runs"),
        hiveGet<StudioOverviewLite>("execution-studio/overview").catch(() => ({ recent_activity: [] })),
      ]);
      const review = await hiveGet<GrokHiveMindReviewQueue>("operator/grok/hivemind-review-queue");
      setSnapshot(nextSnapshot);
      setRuns(nextRuns);
      setReviewQueue(review.items ?? []);
      setReviewQueueMeta({
        count: Number(review.count ?? 0),
        oldestPendingAgeHours: Number(review.oldest_pending_age_hours ?? 0),
        slaHours: Number(review.sla_hours ?? 24),
        slaBreached: Boolean(review.sla_breached),
      });
      const activity = Array.isArray(studioOverview.recent_activity) ? studioOverview.recent_activity : [];
      setBrowserAudit(
        activity
          .filter((row) => {
            const eventType = String(row.event_type || "").toLowerCase();
            const lane = String((row.payload?.lane as string | undefined) || "").toLowerCase();
            return eventType === "browser_step" || (eventType === "approval_cleared" && lane === "browser");
          })
          .slice(0, 8),
      );
      await loadTemplates();
      if (!selectedRunId && nextRuns.length > 0) {
        setSelectedRunId(nextRuns[0]!.id);
      }
      if (contextSources.length === 0) {
        setContextSources(nextSnapshot.available_context_sources ?? DEFAULT_CONTEXT_SOURCES);
      }
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : "Grok Control Plane unavailable");
    } finally {
      setLoading(false);
    }
  }, [selectedRunId, loadTemplates, contextSources.length]);

  const reviewQueueItem = useCallback(async (item: GrokHiveMindReviewItem, decision: "approve" | "reject") => {
    setBusy(`queue-${decision}-${item.knowledge_item_id}`);
    try {
      await hivePostJson(`operator/grok/hivemind-review/${encodeURIComponent(item.knowledge_item_id)}`, {
        decision,
      });
      toast.success(`HiveMind item ${decision}d.`);
      await load();
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : `Failed to ${decision} item`);
    } finally {
      setBusy(null);
    }
  }, [load]);

  const runBrowserLaneStep = useCallback(async () => {
    if (browserGoal.trim().length < 3) {
      toast.error("Browser goal must have at least 3 characters.");
      return;
    }
    if (browserMode === "live" && !browserConfirmLive) {
      toast.error("Live mode requires explicit operator confirm toggle.");
      return;
    }
    setBusy("browser-step");
    setBrowserResult(null);
    try {
      const out = await hivePostJson<{
        ok: boolean;
        mode?: "draft" | "simulate" | "live";
        message?: string;
        error?: string;
        retry_after_sec?: number;
      }>("execution-studio/browser/step", {
        goal: browserGoal.trim(),
        start_url: browserStartUrl.trim() || undefined,
        mode: browserMode,
        operator_confirmed: browserMode === "live" ? browserConfirmLive : false,
      });
      const msg = out.message ?? out.error ?? (out.ok ? "Browser step completed." : "Browser step failed.");
      setBrowserResult(msg);
      toast.success(msg);
      await load();
    } catch (error) {
      const msg = error instanceof HiveApiError ? error.message : "Browser step failed";
      setBrowserResult(msg);
      toast.error(msg);
    } finally {
      setBusy(null);
    }
  }, [browserGoal, browserStartUrl, browserMode, browserConfirmLive, load]);

  const loadRunExtras = useCallback(async (runId: string) => {
    const [approvalRows, artifactRows] = await Promise.all([
      hiveGet<GrokApproval[]>(`operator/grok/runs/${encodeURIComponent(runId)}/approvals`),
      hiveGet<NonNullable<GrokRun["artifacts"]>>(
        `operator/grok/runs/${encodeURIComponent(runId)}/artifacts`,
      ),
    ]);
    setApprovals(approvalRows);
    setRuns((prev) =>
      prev.map((run) => (run.id === runId ? { ...run, artifacts: artifactRows } : run)),
    );
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedRunId) {
      setApprovals([]);
      return;
    }
    void loadRunExtras(selectedRunId).catch((error: unknown) => {
      toast.error(error instanceof HiveApiError ? error.message : "Failed to load run approvals/artifacts");
    });
  }, [selectedRunId, loadRunExtras]);

  useEffect(() => {
    void loadTemplates().catch((error: unknown) => {
      toast.error(error instanceof HiveApiError ? error.message : "Failed to load templates");
    });
  }, [loadTemplates]);

  const createRun = useCallback(async () => {
    const objectiveText = objective.trim();
    if (objectiveText.length < 8) {
      toast.error("Objective must have at least 8 characters.");
      return;
    }
    setBusy("create");
    try {
      const created = await hivePostJson<GrokRun>("operator/grok/runs", {
        objective: objectiveText,
        scope_paths: scopePaths
          .split(",")
          .map((row) => row.trim())
          .filter(Boolean),
        run_mode: runMode,
        risk_level: riskLevel,
        command_profile: commandProfile,
        context_sources: contextSources,
        template_id: templateIdForRun,
        force_fresh_run: forceFreshRun,
      });
      setObjective("");
      setScopePaths("");
      setTemplateIdForRun(null);
      setForceFreshRun(false);
      toast.success("Grok run created.");
      await load();
      setSelectedRunId(created.id);
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : "Failed to create run");
    } finally {
      setBusy(null);
    }
  }, [objective, scopePaths, runMode, riskLevel, commandProfile, contextSources, templateIdForRun, forceFreshRun, load]);

  const runEscalation = useCallback(async (kind: EscalationKind) => {
    if (!snapshot) return;
    const now = Date.now();
    const recent = runs.find((row) => {
      const metadata = row.metadata && typeof row.metadata === "object" ? row.metadata : {};
      const escalationKind = String((metadata as Record<string, unknown>).escalation_kind ?? "");
      if (escalationKind !== kind) return false;
      const created = Date.parse(row.created_at);
      if (Number.isNaN(created)) return false;
      return now - created < ESCALATION_COOLDOWN_MS;
    });
    if (recent) {
      setSelectedRunId(recent.id);
      toast.message("Escalation run already exists in cooldown window.");
      return;
    }
    const fallbackProfile =
      ["ci_quick", "deploy_candidate", "read_only", "prod_deploy"].find((profile) =>
        (snapshot.guardrails.command_allow_profiles ?? []).includes(profile),
      ) ?? snapshot.guardrails.command_allow_profiles[0] ?? "ci_quick";
    const base = {
      context_sources: DEFAULT_CONTEXT_SOURCES,
      run_mode: "code_edit_and_test" as const,
      risk_level: "high" as const,
      command_profile: fallbackProfile,
    };
    const configs: Record<EscalationKind, { name: string; description: string; objective: string; scope_paths: string[] }> = {
      review_queue_sla: {
        name: "Escalation: HiveMind review queue SLA",
        description: "Auto-generated escalation when low-confidence review queue breaches SLA.",
        objective:
          "Investigate low-confidence review queue SLA breach, prioritize root causes, and propose safe remediation with verification evidence.",
        scope_paths: [
          "backend/app/application/services/grok_control_plane.py",
          "frontend/components/hive/grok-control-plane-panel.tsx",
          "backend/app/core/config.py",
        ],
      },
      governance_cost: {
        name: "Escalation: Grok governance cost cap",
        description: "Auto-generated escalation for 24h Grok cost cap breach.",
        objective:
          "Reduce Grok execution cost pressure, identify expensive run patterns, and ship guardrail updates with measurable impact.",
        scope_paths: [
          "backend/app/application/services/grok_control_plane.py",
          "backend/app/core/config.py",
          "frontend/components/hive/grok-control-plane-panel.tsx",
        ],
      },
      governance_timeout: {
        name: "Escalation: Grok timeout breaches",
        description: "Auto-generated escalation for repeated timeout breaches in last 24h.",
        objective:
          "Investigate recurring Grok command timeouts, tune command profiles/timeouts, and verify stability improvements.",
        scope_paths: [
          "backend/app/application/services/grok_control_plane.py",
          "backend/app/core/config.py",
          "scripts/ci-local.sh",
        ],
      },
      governance_risk: {
        name: "Escalation: Grok high-risk volume",
        description: "Auto-generated escalation for high volume of high/critical risk runs.",
        objective:
          "Audit high-risk Grok run volume, enforce stricter approval and scope policies, and document rollback-safe execution path.",
        scope_paths: [
          "backend/app/application/services/grok_control_plane.py",
          "backend/app/presentation/api/routers/grok_control_plane.py",
          "frontend/components/hive/grok-control-plane-panel.tsx",
        ],
      },
    };
    const cfg = configs[kind];
    setBusy(`escalate-${kind}`);
    try {
      const query = new URLSearchParams({
        limit: "4",
        offset: "0",
        include_archived: "false",
        query: cfg.name,
      });
      const existingTemplates = await hiveGet<GrokTemplate[]>(`operator/grok/templates?${query.toString()}`);
      let template = existingTemplates.find((row) => row.name.trim().toLowerCase() === cfg.name.trim().toLowerCase());
      if (!template) {
        template = await hivePostJson<GrokTemplate>("operator/grok/templates", {
          name: cfg.name,
          description: cfg.description,
          objective: cfg.objective,
          scope_paths: cfg.scope_paths,
          run_mode: base.run_mode,
          risk_level: base.risk_level,
          command_profile: base.command_profile,
          context_sources: base.context_sources,
          tags: ["escalation", "auto", "grok-governance"],
        });
      }
      const created = await hivePostJson<GrokRun>("operator/grok/runs", {
        objective: template.objective,
        scope_paths: template.scope_paths,
        run_mode: template.run_mode,
        risk_level: template.risk_level,
        command_profile: template.command_profile,
        context_sources: template.context_sources.length > 0 ? template.context_sources : DEFAULT_CONTEXT_SOURCES,
        template_id: template.id,
        force_fresh_run: true,
        metadata: {
          escalation_kind: kind,
          escalation_source: "grok_panel",
        },
      });
      toast.success(`Escalation run created: ${cfg.name}`);
      setLastEscalationResume(null);
      setTemplateIdForRun(template.id);
      setObjective(template.objective);
      setScopePaths(template.scope_paths.join(","));
      setRunMode(template.run_mode);
      setRiskLevel(template.risk_level);
      setCommandProfile(template.command_profile);
      setContextSources(template.context_sources.length > 0 ? template.context_sources : DEFAULT_CONTEXT_SOURCES);
      await load();
      setSelectedRunId(created.id);
    } catch (error) {
      const message = error instanceof HiveApiError ? error.message : "Failed to create escalation run";
      const runId = message.match(RUN_ID_PATTERN)?.[0] ?? null;
      if (runId) {
        setSelectedRunId(runId);
        setLastEscalationResume({ kind, runId, at: Date.now() });
        toast.message("Escalation cooldown active. Opened existing escalation run.");
        await load();
      } else {
        toast.error(message);
      }
    } finally {
      setBusy(null);
    }
  }, [snapshot, runs, load]);

  const resumedRunForReview = lastEscalationResume?.kind === "review_queue_sla" ? lastEscalationResume : null;
  const resumedRunForGovernance =
    lastEscalationResume && lastEscalationResume.kind !== "review_queue_sla" ? lastEscalationResume : null;
  const persistedResume = useMemo(() => {
    const raw = snapshot?.last_resumed_escalation;
    if (!raw?.run_id || !raw?.escalation_kind) {
      return null;
    }
    const kind = raw.escalation_kind as EscalationKind;
    if (!["review_queue_sla", "governance_cost", "governance_timeout", "governance_risk"].includes(kind)) {
      return null;
    }
    return {
      kind,
      runId: raw.run_id,
      at: Date.now(),
      remainingTtlHours: Number(raw.remaining_ttl_hours ?? 0),
    };
  }, [snapshot?.last_resumed_escalation]);
  const resolvedReviewResume = resumedRunForReview ?? (persistedResume?.kind === "review_queue_sla" ? persistedResume : null);
  const resolvedGovernanceResume =
    resumedRunForGovernance ?? (persistedResume && persistedResume.kind !== "review_queue_sla" ? persistedResume : null);

  const postAction = useCallback(
    async (action: "approve" | "reject" | "cancel" | "start", options?: { executeCommands?: boolean }) => {
      if (!selectedRun) {
        return;
      }
      setBusy(action);
      try {
        const body = action === "start" ? { execute_commands: Boolean(options?.executeCommands) } : { note: null };
        await hivePostJson<GrokRun>(`operator/grok/runs/${encodeURIComponent(selectedRun.id)}/${action}`, body);
        toast.success(`Run ${action} queued.`);
        await load();
      } catch (error) {
        toast.error(error instanceof HiveApiError ? error.message : `Run ${action} failed`);
      } finally {
        setBusy(null);
      }
    },
    [selectedRun, load],
  );

  const prefillFromSelected = useCallback(() => {
    if (!selectedRun) return;
    setObjective(`${selectedRun.objective} (re-run)`);
    setRunMode(selectedRun.run_mode);
    setRiskLevel(selectedRun.risk_level);
    setCommandProfile(selectedRun.command_profile);
    setContextSources(snapshot?.available_context_sources ?? DEFAULT_CONTEXT_SOURCES);
    toast.success("Intake prefilled from selected run.");
  }, [selectedRun, snapshot?.available_context_sources]);

  const applyPreset = useCallback((preset: GrokPreset) => {
    setObjective(preset.objective);
    setScopePaths(preset.scopePaths);
    setRunMode(preset.runMode);
    setRiskLevel(preset.riskLevel);
    setCommandProfile(preset.commandProfile);
    setContextSources(DEFAULT_CONTEXT_SOURCES);
    setTemplateIdForRun(null);
    setForceFreshRun(false);
    toast.success(`Preset applied: ${preset.label}`);
  }, []);

  const applyTemplateToIntake = useCallback((template: GrokTemplate) => {
    setObjective(template.objective);
    setScopePaths((template.scope_paths ?? []).join(","));
    setRunMode(template.run_mode);
    setRiskLevel(template.risk_level);
    setCommandProfile(template.command_profile);
    setContextSources(
      template.context_sources.length > 0
        ? template.context_sources
        : (snapshot?.available_context_sources ?? DEFAULT_CONTEXT_SOURCES),
    );
    setTemplateIdForRun(template.id);
    setForceFreshRun(false);
    toast.success(`Template applied: ${template.name}`);
  }, [snapshot?.available_context_sources]);

  const clearTemplateForm = useCallback(() => {
    setActiveTemplateId(null);
    setTemplateName("");
    setTemplateDescription("");
  }, []);

  const openTemplateForEdit = useCallback((template: GrokTemplate) => {
    setActiveTemplateId(template.id);
    setTemplateName(template.name);
    setTemplateDescription(template.description ?? "");
    setObjective(template.objective);
    setScopePaths(template.scope_paths.join(","));
    setRunMode(template.run_mode);
    setRiskLevel(template.risk_level);
    setCommandProfile(template.command_profile);
    setContextSources(
      template.context_sources.length > 0
        ? template.context_sources
        : (snapshot?.available_context_sources ?? DEFAULT_CONTEXT_SOURCES),
    );
    setTemplateIdForRun(template.id);
  }, [snapshot?.available_context_sources]);

  const saveTemplate = useCallback(async () => {
    if (templateName.trim().length < 2) {
      toast.error("Template name must have at least 2 characters.");
      return;
    }
    if (objective.trim().length < 8) {
      toast.error("Objective must have at least 8 characters.");
      return;
    }
    setBusy("template-save");
    try {
      const payload = {
        name: templateName.trim(),
        description: templateDescription.trim() || null,
        objective: objective.trim(),
        scope_paths: scopePaths
          .split(",")
          .map((row) => row.trim())
          .filter(Boolean),
        run_mode: runMode,
        risk_level: riskLevel,
        command_profile: commandProfile,
        context_sources: contextSources,
        tags: [],
      };
      if (activeTemplateId) {
        await hivePatchJson<GrokTemplate>(`operator/grok/templates/${encodeURIComponent(activeTemplateId)}`, payload);
        toast.success("Template updated.");
      } else {
        await hivePostJson<GrokTemplate>("operator/grok/templates", payload);
        toast.success("Template created.");
      }
      await loadTemplates();
      clearTemplateForm();
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : "Template save failed");
    } finally {
      setBusy(null);
    }
  }, [
    templateName,
    objective,
    templateDescription,
    scopePaths,
    runMode,
    riskLevel,
    commandProfile,
    contextSources,
    activeTemplateId,
    loadTemplates,
    clearTemplateForm,
  ]);

  const analyzeIntakeDedup = useCallback(async () => {
    const objectiveText = objective.trim();
    if (objectiveText.length < 8) {
      toast.error("Objective must have at least 8 characters.");
      return;
    }
    setBusy("advice");
    try {
      const advice = await hivePostJson<GrokIntakeAdvice>("operator/grok/intake-advice", {
        objective: objectiveText,
        scope_paths: scopePaths
          .split(",")
          .map((row) => row.trim())
          .filter(Boolean),
        context_sources: contextSources,
      });
      setIntakeAdvice(advice);
      toast.success("Dedup advice ready.");
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : "Intake analysis failed");
    } finally {
      setBusy(null);
    }
  }, [objective, scopePaths, contextSources]);

  const archiveTemplate = useCallback(async (template: GrokTemplate, archived: boolean) => {
    setBusy(`template-archive-${template.id}`);
    try {
      await hivePatchJson<GrokTemplate>(`operator/grok/templates/${encodeURIComponent(template.id)}`, {
        is_archived: archived,
      });
      toast.success(archived ? "Template archived." : "Template restored.");
      await loadTemplates();
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : "Template archive action failed");
    } finally {
      setBusy(null);
    }
  }, [loadTemplates]);

  const deleteTemplate = useCallback(async (template: GrokTemplate) => {
    setBusy(`template-delete-${template.id}`);
    try {
      await hiveDelete(`operator/grok/templates/${encodeURIComponent(template.id)}`);
      toast.success("Template deleted.");
      await loadTemplates();
      if (activeTemplateId === template.id) {
        clearTemplateForm();
      }
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : "Template delete failed");
    } finally {
      setBusy(null);
    }
  }, [loadTemplates, activeTemplateId, clearTemplateForm]);

  const pushArtifactToHiveMind = useCallback(async (runId: string, artifactId: string) => {
    setBusy(`push-${artifactId}`);
    try {
      const out = await hivePostJson<{ priority?: string; confidence_score?: number }>(
        `operator/grok/runs/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(artifactId)}/push-hivemind`,
        {
        tags: ["grok", "analysis"],
        auto_priority: true,
        },
      );
      const confidencePct =
        typeof out?.confidence_score === "number" ? `${Math.round(out.confidence_score * 100)}%` : "n/a";
      toast.success(`Artifact pushed (${out?.priority ?? "medium"} priority, confidence ${confidencePct}).`);
      await load();
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : "Push to HiveMind failed");
    } finally {
      setBusy(null);
    }
  }, [load]);

  const rerunSelected = useCallback(async () => {
    if (!selectedRun) return;
    setBusy("rerun");
    try {
      const cloned = await hivePostJson<GrokRun>(`operator/grok/runs/${encodeURIComponent(selectedRun.id)}/rerun`, {
        objective_override: `${selectedRun.objective} (re-run)`,
      });
      toast.success("Re-run draft created.");
      await load();
      setSelectedRunId(cloned.id);
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : "Re-run failed");
    } finally {
      setBusy(null);
    }
  }, [selectedRun, load]);

  const rerunAndStartWithCommands = useCallback(async () => {
    if (!selectedRun) return;
    setBusy("rerun-start");
    try {
      const cloned = await hivePostJson<GrokRun>(`operator/grok/runs/${encodeURIComponent(selectedRun.id)}/rerun`, {
        objective_override: `${selectedRun.objective} (re-run with commands)`,
      });
      await hivePostJson<GrokRun>(`operator/grok/runs/${encodeURIComponent(cloned.id)}/start`, {
        execute_commands: true,
      });
      toast.success("Re-run created and started with commands.");
      await load();
      setSelectedRunId(cloned.id);
    } catch (error) {
      toast.error(error instanceof HiveApiError ? error.message : "Re-run + start failed");
    } finally {
      setBusy(null);
    }
  }, [selectedRun, load]);

  const copyArtifact = useCallback(async (artifact: NonNullable<GrokRun["artifacts"]>[number]) => {
    const text = artifact.content_text?.trim();
    if (!text) {
      toast.error("Artifact has no text content.");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Artifact copied.");
    } catch {
      toast.error("Copy failed.");
    }
  }, []);

  const downloadArtifact = useCallback((artifact: NonNullable<GrokRun["artifacts"]>[number]) => {
    const text = artifact.content_text ?? "";
    const blob = new Blob([text], { type: artifact.mime_type || "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const safeTitle = artifact.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    anchor.href = url;
    anchor.download = `${safeTitle || "artifact"}-${artifact.id.slice(0, 8)}.txt`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }, []);

  const artifactCounts = useMemo(() => {
    const rows = selectedRun?.artifacts ?? [];
    return {
      all: rows.length,
      context: rows.filter((artifact) => artifact.kind === "context").length,
      plan: rows.filter((artifact) => artifact.kind === "plan").length,
      command_log: rows.filter((artifact) => artifact.kind === "command_log").length,
      summary: rows.filter((artifact) => artifact.kind === "summary").length,
    } as const;
  }, [selectedRun]);

  const visibleArtifacts = useMemo(() => {
    const rows = selectedRun?.artifacts ?? [];
    if (artifactKind === "all") {
      return rows;
    }
    return rows.filter((artifact) => artifact.kind === artifactKind);
  }, [selectedRun, artifactKind]);

  const recentTrend = useMemo(() => {
    const recent = runs.slice(0, 5);
    const total = recent.length;
    const success = recent.filter((run) => run.status === "succeeded").length;
    const failed = recent.filter((run) => run.status === "failed" || run.status === "rejected").length;
    const active = recent.filter((run) => run.status === "running" || run.status === "approved").length;
    const waiting = recent.filter((run) => run.status === "awaiting_approval").length;
    return { total, success, failed, active, waiting };
  }, [runs]);

  if (loading && !snapshot) {
    return (
      <V4Card>
        <div className="flex min-h-32 items-center justify-center gap-2 text-sm text-(--qs-muted)">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading Grok Control Plane…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-muted)">Grok Control Plane is disabled for this deployment.</p>
      </V4Card>
    );
  }

  return (
    <div className="space-y-4" id="grok-control-plane">
      <V4Card>
        <V4CardHeader
          kicker="Operator manual"
          title="How Grok Build works in this environment"
          description="Grok Control Plane je riadený workflow pre plánovanie a vykonanie technických taskov s guardrails, approvals a audit trailom."
        />
        <div className="space-y-3 text-sm text-(--qs-muted)">
          <p>
            Použi Grok panel, keď chceš bezpečne spustiť technický task end-to-end: najprv vytvoríš run intake
            (objective, scope, mode, risk, command profile), potom run schváliš/spustíš a sleduješ kroky, eventy a
            artefakty.
          </p>
          <div className="rounded-lg border border-(--qs-border) bg-black/20 p-3">
            <p className="font-semibold text-(--qs-text)">Odporúčaný workflow</p>
            <ol className="mt-2 space-y-1 pl-4 text-xs">
              <li>1) Zadaj konkrétny objective (čo sa má zmeniť a ako overiť výsledok).</li>
              <li>2) Obmedz scope paths na minimálnu potrebnú časť repozitára.</li>
              <li>3) Vyber run mode podľa typu úlohy (nižšie) a risk level podľa dopadu.</li>
              <li>4) Pre nové alebo citlivé tasky začni vždy cez Start (plan-only).</li>
              <li>5) Až potom použi Start (with commands), sleduj Steps/Events/Artifacts.</li>
              <li>6) Pri neúspechu použi Re-run as new alebo Re-run + start commands.</li>
            </ol>
          </div>
          <div className="rounded-lg border border-(--qs-border) bg-black/20 p-3">
            <p className="font-semibold text-(--qs-text)">Run mode mapovanie</p>
            <ul className="mt-2 space-y-1 text-xs">
              {RUN_MODE_GUIDE.map((row) => (
                <li key={row.mode}>
                  <span className="font-semibold text-(--qs-text)">{row.mode}</span>: {row.when} ·{" "}
                  <span className="text-cyan">{row.execution}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg border border-(--qs-border) bg-black/20 p-3">
            <p className="font-semibold text-(--qs-text)">Príklady taskov a nastavení (one-click)</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {GROK_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                  onClick={() => applyPreset(preset)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs">
              Guardrails rešpektujú command profiles, deny patterns a approval pravidlá zo snapshotu nižšie.
            </p>
          </div>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          kicker="HiveMind review queue"
          title="Nízka dôvera vyžaduje schválenie"
          description="Auto-priority zápisy s nízkou dôverou sa zaparkujú pred plným trustom."
          actions={
            <div className="flex items-center gap-1">
              <V4Badge tone={reviewQueueMeta.slaBreached ? "err" : reviewQueueMeta.count > 0 ? "warn" : "ok"}>
                čaká {reviewQueueMeta.count}
              </V4Badge>
              <V4Badge tone={reviewQueueMeta.slaBreached ? "err" : "info"}>
                najstaršia {Math.round(reviewQueueMeta.oldestPendingAgeHours * 10) / 10}h / SLA {reviewQueueMeta.slaHours}h
              </V4Badge>
            </div>
          }
        />
        <div className="mb-2 flex flex-wrap gap-2">
          {reviewQueueMeta.slaBreached ? (
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busy === "escalate-review_queue_sla"}
              onClick={() => void runEscalation("review_queue_sla")}
            >
              {busy === "escalate-review_queue_sla" ? <Loader2 className="size-3 animate-spin" aria-hidden /> : null}
              Eskalácia na 1 klik
            </button>
          ) : null}
          {resolvedReviewResume ? (
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={() => setSelectedRunId(resolvedReviewResume.runId)}
            >
              Obnovený run {resolvedReviewResume.runId.slice(0, 8)}…
              {resumedRunExpirySuffix((resolvedReviewResume as { remainingTtlHours?: unknown }).remainingTtlHours)}
            </button>
          ) : null}
        </div>
        {reviewQueue.length === 0 ? (
          <p className="text-xs text-(--qs-muted)">Queue je čistá. Žiadne nízko-dôverné položky nečakajú na review.</p>
        ) : (
          <ul className="space-y-2">
            {reviewQueue.map((item) => (
              <li key={item.knowledge_item_id} className="rounded border border-(--qs-border) bg-black/20 p-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs text-(--qs-text)">
                      confidence {Math.round(item.confidence_score * 100)}% · priority {item.priority}
                    </p>
                    <p className="mt-1 text-[11px] text-(--qs-muted)">{item.preview}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      disabled={busy === `queue-approve-${item.knowledge_item_id}`}
                      onClick={() => void reviewQueueItem(item, "approve")}
                    >
                      <ShieldCheck className="size-3" aria-hidden /> Approve
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      disabled={busy === `queue-reject-${item.knowledge_item_id}`}
                      onClick={() => void reviewQueueItem(item, "reject")}
                    >
                      <ShieldX className="size-3" aria-hidden /> Reject
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </V4Card>

      <V4Card>
        <V4CardHeader
          kicker="Production governance"
          title="Eskalácie nákladov, timeoutov a rizika"
          description="24h guardrail snapshot pre Grok execution lane."
          actions={
            <div className="flex items-center gap-1">
              <V4Badge tone={snapshot.governance?.cost_cap_breached ? "err" : "info"}>
                cost ${Number(snapshot.governance?.estimated_cost_usd ?? 0).toFixed(2)} / $
                {Number(snapshot.governance?.cost_cap_usd ?? 0).toFixed(2)}
              </V4Badge>
              <V4Badge tone={snapshot.governance?.timeout_escalated ? "err" : "ok"}>
                timeouts {Number(snapshot.governance?.timeout_breaches ?? 0)} /{" "}
                {Number(snapshot.governance?.timeout_threshold ?? 3)}
              </V4Badge>
              <V4Badge tone={snapshot.governance?.risk_escalated ? "err" : "warn"}>
                high-risk {Number(snapshot.governance?.high_risk_runs ?? 0)} /{" "}
                {Number(snapshot.governance?.risk_threshold ?? 6)}
              </V4Badge>
              <V4Badge
                tone={
                  Number(snapshot.governance?.escalation_resumes_24h ?? 0) >= 6
                    ? "err"
                    : Number(snapshot.governance?.escalation_resumes_24h ?? 0) >= 3
                      ? "warn"
                      : "info"
                }
              >
                resumes {Number(snapshot.governance?.escalation_resumes_24h ?? 0)}
              </V4Badge>
            </div>
          }
        />
        <div className="mb-2 flex flex-wrap gap-2">
          {snapshot.governance?.cost_cap_breached ? (
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busy === "escalate-governance_cost"}
              onClick={() => void runEscalation("governance_cost")}
            >
              {busy === "escalate-governance_cost" ? <Loader2 className="size-3 animate-spin" aria-hidden /> : null}
              Eskalovať cost cap
            </button>
          ) : null}
          {snapshot.governance?.timeout_escalated ? (
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busy === "escalate-governance_timeout"}
              onClick={() => void runEscalation("governance_timeout")}
            >
              {busy === "escalate-governance_timeout" ? <Loader2 className="size-3 animate-spin" aria-hidden /> : null}
              Eskalovať timeouty
            </button>
          ) : null}
          {snapshot.governance?.risk_escalated ? (
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busy === "escalate-governance_risk"}
              onClick={() => void runEscalation("governance_risk")}
            >
              {busy === "escalate-governance_risk" ? <Loader2 className="size-3 animate-spin" aria-hidden /> : null}
              Eskalovať objem rizika
            </button>
          ) : null}
          {resolvedGovernanceResume ? (
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={() => setSelectedRunId(resolvedGovernanceResume.runId)}
            >
              Obnovený run {resolvedGovernanceResume.runId.slice(0, 8)}…
              {resumedRunExpirySuffix((resolvedGovernanceResume as { remainingTtlHours?: unknown }).remainingTtlHours)}
            </button>
          ) : null}
        </div>
        <div className="text-xs text-(--qs-muted)">
          Window {Number(snapshot.governance?.window_hours ?? 24)}h · utilization{" "}
          {Math.round(Number(snapshot.governance?.cost_utilization ?? 0) * 100)}% · prod deploy{" "}
          {snapshot.guardrails.allow_prod_deploy ? "enabled" : "blocked"}
        </div>
        <div className="mt-1 text-xs text-(--qs-muted)">
          Trend 24h: timeout {trendIcon(snapshot.governance?.timeout_trend)} · risk{" "}
          {trendIcon(snapshot.governance?.risk_trend)} · resumes {trendIcon(snapshot.governance?.resume_trend)}
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          kicker="Browser execution lane"
          title="Guarded browser/computer-use fallback"
          description="Spusti browser fallback z Grok panela s draft/simulate/live guardrails."
          actions={<V4Badge tone={browserMode === "live" ? "warn" : "info"}>{browserMode}</V4Badge>}
        />
        <div className="grid gap-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Goal</label>
          <input
            type="text"
            value={browserGoal}
            onChange={(event) => setBrowserGoal(event.target.value)}
            className="qs-input"
            placeholder="What should browser lane verify?"
          />
          <label className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Start URL</label>
          <input
            type="text"
            value={browserStartUrl}
            onChange={(event) => setBrowserStartUrl(event.target.value)}
            className="qs-input"
            placeholder="https://queenswarm.love"
          />
          <label className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Mode</label>
          <select
            value={browserMode}
            onChange={(event) => setBrowserMode(event.target.value as "draft" | "simulate" | "live")}
            className="qs-input"
          >
            <option value="draft">draft</option>
            <option value="simulate">simulate</option>
            <option value="live">live</option>
          </select>
          <button
            type="button"
            className={`qs-btn qs-btn--sm ${browserConfirmLive ? "qs-btn--primary" : "qs-btn--ghost"}`}
            onClick={() => setBrowserConfirmLive((prev) => !prev)}
          >
            {browserConfirmLive ? "Live confirm ZAP" : "Live confirm VYP"}
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busy === "browser-step"}
            onClick={() => void runBrowserLaneStep()}
          >
            {busy === "browser-step" ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Play className="size-4" aria-hidden />}
            Spusti browser krok
          </button>
          {browserResult ? <p className="text-xs text-(--qs-muted)">{browserResult}</p> : null}
        </div>
        {browserAudit.length > 0 ? (
          <div className="mt-3 space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Audit trail (posledné)</p>
            <ul className="space-y-1">
              {browserAudit.map((row) => (
                <li key={`${row.at}-${row.event_type}-${row.message.slice(0, 12)}`} className="rounded border border-(--qs-border) bg-black/20 px-2 py-1.5 text-xs">
                  <p className="text-(--qs-text)">{row.event_type}</p>
                  <p className="text-(--qs-muted)">{row.message}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </V4Card>

      <V4Card>
        <V4CardHeader
          kicker="Template library"
          title="Create, edit, archive and reuse run templates"
          description="Samostatné menu na správu veľkého počtu šablón. Karty sú kompaktné, aby sa ich naraz zmestilo 6-8."
          actions={
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              onClick={clearTemplateForm}
            >
              <BookOpenText className="size-4" aria-hidden />
              New template
            </button>
          }
        />
        <div className="space-y-3">
          <div className="grid gap-2 md:grid-cols-2">
            <input
              type="text"
              value={templateName}
              onChange={(event) => setTemplateName(event.target.value)}
              className="qs-input"
              placeholder="Template name (napr. API bugfix fastlane)"
            />
            <input
              type="text"
              value={templateDescription}
              onChange={(event) => setTemplateDescription(event.target.value)}
              className="qs-input"
              placeholder="Short description (optional)"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              onClick={() => void saveTemplate()}
              disabled={busy === "template-save"}
            >
              {busy === "template-save" ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Save className="size-4" aria-hidden />}
              {activeTemplateId ? "Update template" : "Save as template"}
            </button>
            {activeTemplateId ? (
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={clearTemplateForm}>
                Cancel edit
              </button>
            ) : null}
            {templateIdForRun ? <V4Badge tone="info">intake bound to template</V4Badge> : null}
          </div>

          <div className="grid gap-2 md:grid-cols-3">
            <input
              type="text"
              value={templateQuery}
              onChange={(event) => {
                setTemplateQuery(event.target.value);
                setTemplateOffset(0);
              }}
              className="qs-input"
              placeholder="Search templates"
            />
            <button
              type="button"
              className={`qs-btn qs-btn--sm ${showArchivedTemplates ? "qs-btn--primary" : "qs-btn--ghost"}`}
              onClick={() => {
                setShowArchivedTemplates((prev) => !prev);
                setTemplateOffset(0);
              }}
            >
              {showArchivedTemplates ? "Showing archived" : "Showing active"}
            </button>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                disabled={templateOffset === 0}
                onClick={() => setTemplateOffset((prev) => Math.max(0, prev - TEMPLATE_PAGE_SIZE))}
              >
                Prev
              </button>
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                disabled={templates.length < TEMPLATE_PAGE_SIZE}
                onClick={() => setTemplateOffset((prev) => prev + TEMPLATE_PAGE_SIZE)}
              >
                Next
              </button>
            </div>
          </div>

          {templates.length === 0 ? (
            <p className="text-xs text-(--qs-muted)">No templates in this view yet.</p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {templates.map((template) => (
                <article key={template.id} className="rounded border border-(--qs-border) bg-black/20 p-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className="line-clamp-2 text-xs font-semibold text-(--qs-text)">{template.name}</p>
                    <V4Badge tone={template.is_archived ? "warn" : "ok"}>{template.is_archived ? "archived" : "active"}</V4Badge>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[11px] text-(--qs-muted)">
                    {template.description || template.objective}
                  </p>
                  <p className="mt-1 text-[11px] text-(--qs-muted)">
                    {template.run_mode} · {template.risk_level} · use {template.usage_count}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" onClick={() => applyTemplateToIntake(template)}>
                      Apply
                    </button>
                    <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => openTemplateForEdit(template)}>
                      <PencilLine className="size-3" aria-hidden /> Edit
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      disabled={busy === `template-archive-${template.id}`}
                      onClick={() => void archiveTemplate(template, !template.is_archived)}
                    >
                      <Archive className="size-3" aria-hidden /> {template.is_archived ? "Restore" : "Archive"}
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm"
                      disabled={busy === `template-delete-${template.id}`}
                      onClick={() => void deleteTemplate(template)}
                    >
                      <Trash2 className="size-3" aria-hidden /> Delete
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          kicker="Grok Control Plane"
          title="Plan-first run intake"
          description="Create Grok runs with policy guardrails and approval gates."
          actions={
            <InfoHint
              title="Grok Build quick guide"
              description="Grok Control Plane riadi technické tasky cez plan-first intake, approval gates a audit artefakty. Začni runom v narrow scope a podľa rizika vyber plan-only alebo command execution."
              options={MANUAL_HINT_OPTIONS}
              manualHref="/manual#cockpit-overview"
              manualLabel="Open operator manual →"
            />
          }
        />
        <div className="grid gap-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Objective</label>
          <input
            type="text"
            value={objective}
            onChange={(event) => setObjective(event.target.value)}
            className="qs-input"
            placeholder="Objective: e.g. harden auth middleware and verify regression tests"
          />
          <label className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Scope paths</label>
          <input
            type="text"
            value={scopePaths}
            onChange={(event) => setScopePaths(event.target.value)}
            className="qs-input"
            placeholder="Scope paths (comma-separated): backend/app/presentation/api,frontend/components/hive"
          />
          <label className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Run mode</label>
          <select value={runMode} onChange={(event) => setRunMode(event.target.value as GrokRun["run_mode"])} className="qs-input">
            {MODE_OPTIONS.map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </select>
          <label className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Risk level</label>
          <select
            value={riskLevel}
            onChange={(event) => setRiskLevel(event.target.value as GrokRun["risk_level"])}
            className="qs-input"
          >
            {RISK_OPTIONS.map((risk) => (
              <option key={risk} value={risk}>
                {risk}
              </option>
            ))}
          </select>
          <label className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Command profile</label>
          <select value={commandProfile} onChange={(event) => setCommandProfile(event.target.value)} className="qs-input">
            {(snapshot.guardrails.command_allow_profiles ?? []).map((profile) => (
              <option key={profile} value={profile}>
                {profile}
              </option>
            ))}
          </select>
          <div className="rounded border border-(--qs-border) bg-black/20 p-2">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Context sources</p>
            <div className="flex flex-wrap gap-1">
              {(snapshot.available_context_sources ?? DEFAULT_CONTEXT_SOURCES).map((source) => {
                const selected = contextSources.includes(source);
                return (
                  <button
                    key={source}
                    type="button"
                    className={`qs-btn qs-btn--sm ${selected ? "qs-btn--primary" : "qs-btn--ghost"}`}
                    onClick={() =>
                      setContextSources((prev) =>
                        prev.includes(source) ? prev.filter((item) => item !== source) : [...prev, source],
                      )
                    }
                  >
                    {source}
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-[11px] text-(--qs-muted)">
              Grok dostane tieto zdroje ako context pack, aby sa sústredil na high-impact úlohy bez duplicít.
            </p>
          </div>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm"
            disabled={busy === "advice"}
            onClick={() => void analyzeIntakeDedup()}
          >
            {busy === "advice" ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
            Analyze duplicates & reuse
          </button>
          <button
            type="button"
            className={`qs-btn qs-btn--sm ${forceFreshRun ? "qs-btn--primary" : "qs-btn--ghost"}`}
            onClick={() => setForceFreshRun((prev) => !prev)}
          >
            {forceFreshRun ? "Dedup override ON" : "Force fresh run (override dedup)"}
          </button>
          {intakeAdvice ? (
            <div className="rounded border border-(--qs-border) bg-black/20 p-2 text-xs">
              <p className="text-(--qs-text)">
                dedup score <span className="font-semibold">{Math.round(intakeAdvice.dedup_score * 100)}%</span> ·
                recommendation <span className="font-semibold">{intakeAdvice.recommendation}</span>
              </p>
              {intakeAdvice.thresholds ? (
                <p className="mt-1 text-(--qs-muted)">
                  thresholds reuse {Math.round((intakeAdvice.thresholds.reuse ?? 0.62) * 100)}% · hybrid{" "}
                  {Math.round((intakeAdvice.thresholds.hybrid ?? 0.35) * 100)}%
                </p>
              ) : null}
              {intakeAdvice.hard_gate_enabled && intakeAdvice.hard_gate_blocked ? (
                <p className="mt-1 text-(--qs-red)">
                  Hard gate: high overlap detected. Reuse template/artifacts or enable force fresh run.
                </p>
              ) : null}
              <p className="mt-1 text-(--qs-muted)">{intakeAdvice.rationale}</p>
              {intakeAdvice.top_candidates.length > 0 ? (
                <ul className="mt-2 space-y-1 text-(--qs-muted)">
                  {intakeAdvice.top_candidates.map((candidate) => (
                    <li key={`${candidate.source_type}-${candidate.source_id}`}>
                      {candidate.source_type}: {candidate.title} ({Math.round(candidate.score * 100)}%)
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
          <button
            type="button"
            className="qs-btn qs-btn--primary qs-btn--sm"
            disabled={busy === "create" || Boolean(intakeAdvice?.hard_gate_enabled && intakeAdvice.hard_gate_blocked && !forceFreshRun)}
            onClick={() => void createRun()}
          >
            {busy === "create" ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Terminal className="size-4" aria-hidden />}
            Create run
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {(() => {
            const healthLevel = snapshot.health_level ?? "ok";
            const failedThreshold = snapshot.failed_alert_threshold ?? 3;
            return (
              <>
          <V4Badge tone={snapshot.cli_available ? "ok" : "warn"}>CLI {snapshot.cli_available ? "available" : "missing"}</V4Badge>
          <V4Badge
            tone={healthTone(healthLevel)}
            className={healthLevel === "error" ? "animate-pulse" : undefined}
          >
            health {healthLevel}
          </V4Badge>
          <V4Badge tone="info">Active {snapshot.active_runs}</V4Badge>
          <V4Badge tone="warn">Draft {snapshot.draft_runs}</V4Badge>
          <V4Badge
            tone={snapshot.failed_runs >= failedThreshold ? "err" : snapshot.failed_runs > 0 ? "warn" : "ok"}
            className={snapshot.failed_runs >= failedThreshold ? "animate-pulse" : undefined}
          >
            Failed {snapshot.failed_runs}/{failedThreshold}
          </V4Badge>
              </>
            );
          })()}
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          kicker="Run queue"
          title="Recent Grok runs"
          description="Select run to inspect steps, logs, and actions."
          actions={
            recentTrend.total > 0 ? (
              <div className="flex flex-wrap items-center gap-1">
                <V4Badge tone={recentTrend.failed > 0 ? "err" : "ok"}>
                  last5 {recentTrend.success}/{recentTrend.total} success
                </V4Badge>
                {recentTrend.failed > 0 ? <V4Badge tone="err">fail {recentTrend.failed}</V4Badge> : null}
                {recentTrend.active > 0 ? <V4Badge tone="warn">active {recentTrend.active}</V4Badge> : null}
                {recentTrend.waiting > 0 ? <V4Badge tone="info">awaiting {recentTrend.waiting}</V4Badge> : null}
              </div>
            ) : null
          }
        />
        {runs.length === 0 ? (
          <p className="text-sm text-(--qs-muted)">No runs yet. Create your first run above.</p>
        ) : (
          <ul className="space-y-2">
            {runs.map((run) => (
              <li key={run.id} className="rounded border border-(--qs-border) bg-black/20 p-2">
                <button
                  type="button"
                  className="w-full text-left"
                  onClick={() => setSelectedRunId(run.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-medium text-(--qs-text)">{run.objective}</p>
                    <V4Badge tone={runTone(run.status)}>{run.status}</V4Badge>
                  </div>
                  <p className="mt-1 text-xs text-(--qs-muted)">
                    {run.run_mode} · risk {run.risk_level} · profile {run.command_profile}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </V4Card>

      {selectedRun ? (
        <V4Card>
          <V4CardHeader
            kicker="Run detail"
            title={selectedRun.objective}
            description={`Status ${selectedRun.status} · mode ${selectedRun.run_mode} · risk ${selectedRun.risk_level}`}
          />
          <div className="mb-3 flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={busy === "approve"}
              onClick={() => void postAction("approve")}
            >
              <ShieldCheck className="size-4" aria-hidden /> Approve
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={busy === "reject"}
              onClick={() => void postAction("reject")}
            >
              <ShieldX className="size-4" aria-hidden /> Reject
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busy === "start"}
              onClick={() => void postAction("start", { executeCommands: false })}
            >
              <Play className="size-4" aria-hidden /> Start (plan-only)
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={busy === "start"}
              onClick={() => void postAction("start", { executeCommands: true })}
            >
              <Play className="size-4" aria-hidden /> Start (with commands)
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={busy === "cancel"}
              onClick={() => void postAction("cancel")}
            >
              <Square className="size-4" aria-hidden /> Cancel
            </button>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={prefillFromSelected}>
              Prefill Intake
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm"
              disabled={busy === "rerun"}
              onClick={() => void rerunSelected()}
            >
              Re-run as new
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busy === "rerun-start"}
              onClick={() => void rerunAndStartWithCommands()}
            >
              Re-run + start commands
            </button>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Steps</p>
              {selectedRun.steps.map((step) => (
                <details key={step.id} className="rounded border border-(--qs-border) bg-black/20 px-2 py-1.5">
                  <summary className="cursor-pointer text-xs text-(--qs-text)">
                    {step.title} · {step.status}
                    {step.exit_code !== null ? ` · exit ${step.exit_code}` : ""}
                  </summary>
                  {step.command ? <pre className="mt-2 overflow-auto text-[11px] text-cyan">{step.command}</pre> : null}
                  {step.output ? <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-[11px] text-(--qs-muted)">{step.output}</pre> : null}
                </details>
              ))}
            </div>
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Events</p>
              <ul className="space-y-1">
                {selectedRun.events.slice().reverse().map((event) => (
                  <li key={`${event.at}-${event.code}`} className="rounded border border-(--qs-border) bg-black/20 px-2 py-1.5 text-xs">
                    <p className="text-(--qs-text)">
                      {event.code} · {event.level}
                    </p>
                    <p className="text-(--qs-muted)">{event.message}</p>
                  </li>
                ))}
              </ul>
              {selectedRun.artifacts && selectedRun.artifacts.length > 0 ? (
                <>
                  <div className="flex items-center justify-between gap-2 pt-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Artifacts</p>
                      {artifactKind !== "all" ? (
                        <p className="text-[11px] text-cyan">
                          filtered by `{artifactKind}` ({visibleArtifacts.length})
                        </p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {ARTIFACT_KIND_OPTIONS.map((option) => (
                        <button
                          key={option}
                          type="button"
                          className={`qs-btn qs-btn--sm ${artifactKind === option ? "qs-btn--primary" : "qs-btn--ghost"}`}
                          onClick={() => setArtifactKind(option)}
                        >
                          {option} ({artifactCounts[option]})
                        </button>
                      ))}
                    </div>
                  </div>
                  {visibleArtifacts.length === 0 ? (
                    <p className="text-xs text-(--qs-muted)">No artifacts for selected filter.</p>
                  ) : (
                    <ul className="space-y-1">
                      {visibleArtifacts.map((artifact) => (
                      <li key={artifact.id} className="rounded border border-(--qs-border) bg-black/20 px-2 py-1.5 text-xs">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-(--qs-text)">
                            {artifact.title} · {artifact.kind}
                          </p>
                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              className="qs-btn qs-btn--ghost qs-btn--sm"
                              onClick={() => void copyArtifact(artifact)}
                            >
                              <Copy className="size-3" aria-hidden />
                            </button>
                            <button
                              type="button"
                              className="qs-btn qs-btn--ghost qs-btn--sm"
                              onClick={() => downloadArtifact(artifact)}
                            >
                              <Download className="size-3" aria-hidden />
                            </button>
                            <button
                              type="button"
                              className="qs-btn qs-btn--ghost qs-btn--sm"
                              disabled={busy === `push-${artifact.id}`}
                              onClick={() => void pushArtifactToHiveMind(selectedRun.id, artifact.id)}
                            >
                              {busy === `push-${artifact.id}` ? <Loader2 className="size-3 animate-spin" aria-hidden /> : "HiveMind"}
                            </button>
                          </div>
                        </div>
                        {artifact.content_text ? (
                          <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap text-[11px] text-(--qs-muted)">
                            {artifact.content_text}
                          </pre>
                        ) : null}
                      </li>
                      ))}
                    </ul>
                  )}
                </>
              ) : null}
              {approvals.length > 0 ? (
                <>
                  <p className="pt-2 text-xs font-semibold uppercase tracking-wider text-(--qs-muted)">Approvals</p>
                  <ul className="space-y-1">
                    {approvals.map((approval) => (
                      <li key={approval.id} className="rounded border border-(--qs-border) bg-black/20 px-2 py-1.5 text-xs">
                        <p className="text-(--qs-text)">
                          {approval.decision} · {approval.decided_by}
                        </p>
                        {approval.note ? <p className="text-(--qs-muted)">{approval.note}</p> : null}
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
            </div>
          </div>
        </V4Card>
      ) : null}
    </div>
  );
}
