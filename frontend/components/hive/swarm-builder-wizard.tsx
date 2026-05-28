"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Building2, CheckCircle2, Loader2, Radar, Sparkles, User } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { MarketingOpsQuickstart } from "@/components/hive/marketing-ops-quickstart";
import { usePlatform } from "@/components/hive/platform-context";
import { ProUpgradeBanner } from "@/components/hive/pro-upgrade-banner";
import { V4Badge, V4Card, V4CardHeader, V4PageCanvas } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import {
  buildPrdKanbanTasksUrl,
  type PrdKanbanLaunchParams,
} from "@/lib/prd-kanban-flow";
import {
  patternCountLabel,
  SWARM_TEMPLATE_PATTERN_STACKS,
} from "@/lib/swarm-pattern-stacks";
import {
  getSwarmWizardTemplate,
  getPersonalSwarmTemplates,
  getSentinelSwarmTemplates,
  getVirtualCompanyTemplates,
  templateRequiresProTier,
  type SwarmWizardTemplate,
  type SwarmWizardTemplateId,
} from "@/lib/swarm-wizard-templates";
import {
  buildSwarmLocalMemoryForTemplate,
  getDepartmentByTemplateId,
  VIRTUAL_COMPANY_FUTURE_DEPARTMENTS,
} from "@/lib/virtual-company-departments";
import { profileContextLine, type VirtualCompanyProfile } from "@/lib/virtual-company-api";
import { VirtualCompanyProfilePanel } from "@/components/hive/virtual-company-profile-panel";

type WizardStep = "pick" | "review" | "building" | "done";

interface BuildResult {
  swarmId: string;
  agentIds: string[];
  routineId?: string;
}

async function runSwarmWizardBuild(
  template: SwarmWizardTemplate,
  profile: VirtualCompanyProfile | null,
): Promise<BuildResult> {
  const deptMemory = buildSwarmLocalMemoryForTemplate(template.id);
  const dept = getDepartmentByTemplateId(template.id);
  const profileLine = profile ? profileContextLine(profile) : "";

  const swarm = await hivePostJson<{ id: string }>("swarms", {
    name: template.swarmName,
    purpose: template.swarmPurpose,
    local_memory: {
      wizard_template: template.id,
      ...deptMemory,
      operator_profile: profile?.onboarded
        ? {
            brand_name: profile.brand_name,
            industry: profile.industry,
            focus_areas: profile.focus_areas,
            risk_tolerance: profile.risk_tolerance,
            primary_goal: profile.primary_goal,
          }
        : null,
      operator_profile_context: profileLine || null,
      hive_ui: {
        swarm_role_label: template.name,
        swarm_color_hex: template.accentHex,
        manager_system_prompt: template.description,
        virtual_company: dept?.id ?? (template.category === "sentinel" ? "sentinel" : null),
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
      output_config: {
        wizard_template: template.id,
        virtual_company_department: dept?.id ?? null,
        execution_studio: deptMemory.execution_studio ?? null,
      },
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
      skills: ["execution-studio"],
      context_payload: {
        wizard_template: template.id,
        swarm_id: swarm.id,
        virtual_company_department: dept?.id ?? null,
        execution_studio: deptMemory.execution_studio ?? null,
      },
    });
    routineId = routine.id;
  }

  return { swarmId: swarm.id, agentIds, routineId };
}

function TemplatePickCard({
  item,
  onSelect,
}: {
  item: SwarmWizardTemplate;
  onSelect: (id: SwarmWizardTemplateId) => void;
}): JSX.Element {
  const dept = getDepartmentByTemplateId(item.id);
  return (
    <button
      type="button"
      className="rounded-xl border border-(--qs-border) bg-black/25 p-4 text-left transition hover:border-pollen/40"
      onClick={() => onSelect(item.id)}
    >
      <div className="flex items-center gap-2">
        <span
          className="h-2.5 w-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: item.accentHex }}
          aria-hidden
        />
        <Sparkles className="h-4 w-4 text-pollen" aria-hidden />
        <h3 className="text-sm font-semibold text-(--qs-text)">{item.name}</h3>
        {item.category === "virtual_company" ? (
          <V4Badge tone="info">Dept</V4Badge>
        ) : null}
      </div>
      <p className="mt-2 text-xs text-(--qs-text-3)">{item.tagline}</p>
      {dept?.execution?.suggested_connectors.length ? (
        <p className="mt-1 text-[10px] text-cyan">
          Free connectors: {dept.execution.suggested_connectors.join(", ")}
        </p>
      ) : null}
      <p className="mt-2 text-[11px] text-pollen">
        ~{item.estimatedMinutes} min · saves ~{item.timeSavedHoursPerWeek} h/week
      </p>
      <p className="mt-1 text-[10px] text-cyan">{patternCountLabel(item.id)}</p>
    </button>
  );
}

/** Swarm Builder — Virtual Company departments + personal templates. */
export function SwarmBuilderWizard(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { platformMode, subscriptionTier } = usePlatform();
  const preselected = searchParams.get("template") as SwarmWizardTemplateId | null;

  const virtualTemplates = useMemo(() => getVirtualCompanyTemplates(), []);
  const sentinelTemplates = useMemo(() => getSentinelSwarmTemplates(), []);
  const personalTemplates = useMemo(() => getPersonalSwarmTemplates(), []);

  const [operatorProfile, setOperatorProfile] = useState<VirtualCompanyProfile | null>(null);
  const [step, setStep] = useState<WizardStep>(preselected ? "review" : "pick");
  const [selectedId, setSelectedId] = useState<SwarmWizardTemplateId | null>(
    preselected && getSwarmWizardTemplate(preselected) && !getSwarmWizardTemplate(preselected)?.comingSoon
      ? preselected
      : null,
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

  const dept = useMemo(
    () => (template ? getDepartmentByTemplateId(template.id) : undefined),
    [template],
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
      const built = await runSwarmWizardBuild(template, operatorProfile);
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
  }, [template, proRequired, operatorProfile]);

  return (
    <V4PageCanvas>
      <HivePageHeader
        title={step === "pick" ? "Swarm Builder" : template?.name ?? "Swarm wizard"}
        subtitle="Virtual Company departments — swarms wired to Execution Studio (simulate default, free OAuth)."
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
            ? `${template?.name} needs ${template?.agents.length} agents — Free tier allows 2. Upgrade to Pro to build.`
            : "Solo/internal: all department templates available. Commercial Free: 2 agents, 1 swarm."
        }
      />

      <VirtualCompanyProfilePanel onProfileChange={setOperatorProfile} />

      {step === "pick" ? (
        <div className="space-y-8">
          <section>
            <div className="mb-3 flex items-center gap-2">
              <Radar className="h-4 w-4 text-cyan" aria-hidden />
              <h2 className="text-sm font-semibold text-(--qs-text)">Sentinel</h2>
              <span className="text-xs text-(--qs-text-3)">— read-only intelligence (€0)</span>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {sentinelTemplates.map((item) => (
                <TemplatePickCard
                  key={item.id}
                  item={item}
                  onSelect={(id) => {
                    setSelectedId(id);
                    setStep("review");
                  }}
                />
              ))}
            </div>
          </section>

          <section>
            <div className="mb-3 flex items-center gap-2">
              <Building2 className="h-4 w-4 text-pollen" aria-hidden />
              <h2 className="text-sm font-semibold text-(--qs-text)">Virtual Company</h2>
              <span className="text-xs text-(--qs-text-3)">— firm departments as swarms + Execution Studio</span>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {virtualTemplates.map((item) => (
                <TemplatePickCard
                  key={item.id}
                  item={item}
                  onSelect={(id) => {
                    setSelectedId(id);
                    setStep("review");
                  }}
                />
              ))}
              {VIRTUAL_COMPANY_FUTURE_DEPARTMENTS.map((slot) => (
                <div
                  key={slot.id}
                  className="rounded-xl border border-dashed border-(--qs-border) bg-black/10 p-4 opacity-55"
                >
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-(--qs-text-2)">{slot.label}</h3>
                    <V4Badge tone="warn">Soon</V4Badge>
                  </div>
                  <p className="mt-2 text-xs text-(--qs-text-3)">{slot.tagline}</p>
                </div>
              ))}
            </div>
          </section>

          <section>
            <div className="mb-3 flex items-center gap-2">
              <User className="h-4 w-4 text-cyan" aria-hidden />
              <h2 className="text-sm font-semibold text-(--qs-text)">Personal</h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {personalTemplates.map((item) => (
                <TemplatePickCard
                  key={item.id}
                  item={item}
                  onSelect={(id) => {
                    setSelectedId(id);
                    setStep("review");
                  }}
                />
              ))}
            </div>
          </section>
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
          {dept?.execution ? (
            <div className="mb-4 rounded-lg border border-cyan/25 bg-cyan/5 px-3 py-2 text-xs text-(--qs-text-2)">
              <strong className="text-cyan">Execution Studio:</strong> default {dept.execution.default_mode}, live
              approval required. Connectors: {dept.execution.suggested_connectors.join(", ")} in{" "}
              <Link href="/integrations?tab=studio" className="underline">
                Integrations → Execution Studio
              </Link>
              .
            </div>
          ) : null}
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
              <dt className="text-xs text-(--qs-text-3)">Tools</dt>
              <dd className="font-mono text-[11px]">hive_memory · task_list · mcp_invoke</dd>
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
          {template.prdKanban ? (
            <p className="mt-4 rounded-lg border border-cyan/30 bg-cyan/5 px-3 py-2 text-xs text-(--qs-text-2)">
              {template.prdKanban.kanbanHint}
            </p>
          ) : null}
          {proRequired ? (
            <p className="mt-4 rounded-lg border border-pollen/35 bg-pollen/10 px-3 py-2 text-xs text-pollen">
              Pro plan required — this template creates {template.agents.length} agents.
            </p>
          ) : null}
          <div className="mt-4 flex flex-wrap justify-end gap-2">
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
                {result.agentIds.length} agents
                {result.routineId ? " · routine scheduled" : ""}. Wire free connectors in Execution Studio, then run
                supervisor in simulate mode.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {template.prdKanban ? (
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm"
                    onClick={() =>
                      router.push(
                        buildPrdKanbanTasksUrl({
                          template: template.id,
                          swarmId: result.swarmId,
                        } satisfies PrdKanbanLaunchParams),
                      )
                    }
                  >
                    Start PRD → Kanban
                  </button>
                ) : null}
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm"
                  onClick={() => router.push("/integrations?tab=studio")}
                >
                  Open Execution Studio
                </button>
                <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => router.push("/swarms")}>
                  Open swarms
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
          {template.id === "marketing-ops" ? <MarketingOpsQuickstart swarmId={result.swarmId} /> : null}
        </V4Card>
      ) : null}
    </V4PageCanvas>
  );
}
