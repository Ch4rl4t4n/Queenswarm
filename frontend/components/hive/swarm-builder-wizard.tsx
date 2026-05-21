"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { usePlatform } from "@/components/hive/platform-context";
import { ProUpgradeBanner } from "@/components/hive/pro-upgrade-banner";
import { V4Badge, V4Card, V4CardHeader, V4PageCanvas } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import {
  getSwarmWizardTemplate,
  SWARM_WIZARD_TEMPLATES,
  templateRequiresProTier,
  type SwarmWizardTemplate,
  type SwarmWizardTemplateId,
} from "@/lib/swarm-wizard-templates";
import { patternCountLabel, SWARM_TEMPLATE_PATTERN_STACKS } from "@/lib/swarm-pattern-stacks";
import { cn } from "@/lib/utils";

type WizardStep = "pick" | "review" | "building" | "done";

interface BuildResult {
  swarmId: string;
  agentIds: string[];
  routineId?: string;
}

async function runSwarmWizardBuild(template: SwarmWizardTemplate): Promise<BuildResult> {
  const swarm = await hivePostJson<{ id: string }>("swarms", {
    name: template.swarmName,
    purpose: template.swarmPurpose,
    local_memory: {
      wizard_template: template.id,
      manager_slug:
        template.id === "lead-waterfall"
          ? "execution_operations"
          : template.id === "content-flywheel"
            ? "content_creation"
            : "personal_life",
      hive_ui: {
        swarm_role_label: template.name,
        swarm_color_hex: template.accentHex,
        manager_system_prompt: template.description,
      },
    },
    is_active: true,
  });

  const agentIds: string[] = [];
  for (const spec of template.agents) {
    const created = await hivePostJson<{ agent_id: string }>("agents/dynamic", {
      name: spec.name,
      hive_tier: spec.hiveTier,
      swarm_id: swarm.id,
      system_prompt: spec.systemPrompt,
      tools: spec.tools,
      output_format: "text",
      output_destination: "dashboard",
      schedule_type: spec.scheduleType ?? "on_demand",
      schedule_value: spec.scheduleValue ?? null,
      output_config: { wizard_template: template.id },
      agent_status: "idle",
    });
    agentIds.push(created.agent_id);
  }

  let routineId: string | undefined;
  if (template.routine) {
    const routine = await hivePostJson<{ id: string }>("agents/routines", {
      name: template.routine.name,
      goal_template: template.routine.goalTemplate,
      schedule_kind: template.routine.scheduleKind,
      interval_seconds: template.routine.intervalSeconds ?? null,
      cron_expr: template.routine.cronExpr ?? null,
      runtime_mode: "durable",
      roles: [],
      retrieval_contract: null,
      skills: [],
      context_payload: { wizard_template: template.id, swarm_id: swarm.id },
    });
    routineId = routine.id;
  }

  return { swarmId: swarm.id, agentIds, routineId };
}

/** Swarm Builder — opinionated templates (Phase 0). */
export function SwarmBuilderWizard(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { platformMode, subscriptionTier } = usePlatform();
  const preselected = searchParams.get("template") as SwarmWizardTemplateId | null;

  const [step, setStep] = useState<WizardStep>(preselected ? "review" : "pick");
  const [selectedId, setSelectedId] = useState<SwarmWizardTemplateId | null>(
    preselected && getSwarmWizardTemplate(preselected) ? preselected : null,
  );
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BuildResult | null>(null);

  const template = useMemo(
    () => (selectedId ? getSwarmWizardTemplate(selectedId) : undefined),
    [selectedId],
  );

  const proRequired = useMemo(
    () =>
      template
        ? templateRequiresProTier(template, platformMode, subscriptionTier)
        : false,
    [template, platformMode, subscriptionTier],
  );

  const build = useCallback(async (): Promise<void> => {
    if (!template || template.comingSoon) {
      return;
    }
    if (proRequired) {
      toast.error("This template needs Pro — Free tier allows 2 agents and 1 swarm.");
      return;
    }
    setStep("building");
    setBusy(true);
    try {
      const built = await runSwarmWizardBuild(template);
      setResult(built);
      setStep("done");
      toast.success(`${template.name} swarm is ready`);
    } catch (err) {
      setStep("review");
      if (err instanceof HiveApiError && err.status === 429) {
        toast.error("Plan limit reached — upgrade to Pro for more agents or swarms.");
        return;
      }
      toast.error(err instanceof Error ? err.message : "Wizard build failed");
    } finally {
      setBusy(false);
    }
  }, [template, proRequired]);

  return (
    <V4PageCanvas>
      <HivePageHeader
        title={step === "pick" ? "Swarm Builder" : template?.name ?? "Swarm wizard"}
        subtitle="Opinionated swarms in ~10 minutes — 20 industry agentic patterns, zero prompt engineering."
        actions={
          <Link href="/swarms" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Swarms
          </Link>
        }
      />

      <ProUpgradeBanner
        className="mb-4"
        reason={
          proRequired
            ? `${template?.name} needs 3 agents — Free tier allows 2. Upgrade to Pro to build.`
            : "Free tier: up to 2 agents and 1 swarm. Pro unlocks all templates."
        }
      />

      {step === "pick" ? (
        <div className="grid gap-4 lg:grid-cols-3">
          {SWARM_WIZARD_TEMPLATES.map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={item.comingSoon}
              className={cn(
                "rounded-xl border border-(--qs-border) bg-black/25 p-4 text-left transition hover:border-pollen/40",
                item.comingSoon && "opacity-60",
              )}
              onClick={() => {
                setSelectedId(item.id);
                setStep("review");
              }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: item.accentHex }}
                  aria-hidden
                />
                <Sparkles className="h-4 w-4 text-pollen" aria-hidden />
                <h3 className="text-sm font-semibold text-(--qs-text)">{item.name}</h3>
                {item.comingSoon ? <V4Badge tone="warn">Soon</V4Badge> : null}
              </div>
              <p className="mt-2 text-xs text-(--qs-text-3)">{item.tagline}</p>
              <p className="mt-2 text-[11px] text-pollen">
                ~{item.estimatedMinutes} min · saves ~{item.timeSavedHoursPerWeek} h/week
              </p>
              {!item.comingSoon ? (
                <p className="mt-1 text-[10px] text-cyan">{patternCountLabel(item.id)}</p>
              ) : null}
            </button>
          ))}
        </div>
      ) : null}

      {step === "review" && template ? (
        <V4Card>
          <V4CardHeader
            title={template.name}
            description={template.description}
            actions={
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => setStep("pick")}>
                Back
              </button>
            }
          />
          <dl className="grid gap-2 text-sm text-(--qs-text-2) sm:grid-cols-2">
            <div>
              <dt className="text-xs text-(--qs-text-3)">Colony</dt>
              <dd>{template.swarmName}</dd>
            </div>
            <div>
              <dt className="text-xs text-(--qs-text-3)">Bees</dt>
              <dd>{template.agents.length}</dd>
            </div>
            <div>
              <dt className="text-xs text-(--qs-text-3)">Est. time saved</dt>
              <dd className="text-pollen">~{template.timeSavedHoursPerWeek} h/week</dd>
            </div>
            {template.routine ? (
              <div>
                <dt className="text-xs text-(--qs-text-3)">Routine</dt>
                <dd>{template.routine.name}</dd>
              </div>
            ) : null}
          </dl>
          <ul className="mt-4 space-y-2">
            {template.agents.map((agent) => (
              <li
                key={agent.name}
                className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-xs"
              >
                <span className="font-medium text-(--qs-text)">{agent.name}</span>
                <span className="ml-2 text-(--qs-text-3)">· {agent.hiveTier}</span>
              </li>
            ))}
          </ul>
          {SWARM_TEMPLATE_PATTERN_STACKS[template.id]?.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {SWARM_TEMPLATE_PATTERN_STACKS[template.id].map((label) => (
                <V4Badge key={label} tone="info">
                  {label}
                </V4Badge>
              ))}
            </div>
          ) : null}
          {proRequired ? (
            <p className="mt-4 rounded-lg border border-pollen/35 bg-pollen/10 px-3 py-2 text-xs text-pollen">
              Pro plan required — this template creates {template.agents.length} agents (Free max 2).
              <Link href="/settings/billing" className="ml-1 underline">
                View plans
              </Link>
            </p>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm"
              disabled={busy || proRequired}
              onClick={() => void build()}
            >
              Build swarm
            </button>
          </div>
        </V4Card>
      ) : null}

      {step === "building" ? (
        <V4Card className="flex items-center gap-3 p-6">
          <Loader2 className="h-5 w-5 animate-spin text-pollen" aria-hidden />
          <p className="text-sm text-(--qs-text-2)">Building {template?.name}…</p>
        </V4Card>
      ) : null}

      {step === "done" && result && template ? (
        <V4Card>
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-6 w-6 text-[#00FF88]" aria-hidden />
            <div>
              <h3 className="text-sm font-semibold text-(--qs-text)">{template.name} is live</h3>
              <p className="mt-1 text-xs text-(--qs-text-3)">
                Your swarm will use {(SWARM_TEMPLATE_PATTERN_STACKS[template.id] ?? []).length || "several"} agentic
                patterns on the first supervisor run — {result.agentIds.length} agents
                {result.routineId ? " · routine scheduled" : ""}.
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(SWARM_TEMPLATE_PATTERN_STACKS[template.id] ?? []).map((label) => (
                  <V4Badge key={label} tone="ok">
                    {label}
                  </V4Badge>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm"
                  onClick={() => router.push("/swarms")}
                >
                  Open swarms
                </button>
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                  onClick={() => router.push("/agents")}
                >
                  View agents
                </button>
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm"
                  onClick={() => router.push("/agents#sessions")}
                >
                  Run supervisor
                </button>
              </div>
            </div>
          </div>
        </V4Card>
      ) : null}
    </V4PageCanvas>
  );
}
