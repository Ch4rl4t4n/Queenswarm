/** Virtual Company profile + bootstrap API client. */

import { hiveGet, hivePostJson, hivePutJson } from "@/lib/api";

export interface VirtualCompanyProfile {
  brand_name: string;
  industry: string;
  focus_areas: string[];
  risk_tolerance: "low" | "medium" | "high";
  primary_goal: string;
  onboarded: boolean;
}

export interface BootstrapChecklist {
  profile_complete: boolean;
  routing_mode: string;
  free_first_active: boolean;
  departments_ready: number;
  departments_total: number;
  next_steps: string[];
  connectors: Array<{
    slug: string;
    installed: boolean;
    installed_active: boolean;
    oauth_provider?: string | null;
    departments: string[];
  }>;
  super_routers?: {
    provisioned: number;
    provisioned_total: number;
    active: number;
    slugs: string[];
  };
  swarms?: {
    built_templates: string[];
    departments_built: number;
    departments_total: number;
    sentinel_built: boolean;
  };
  first_run?: {
    marketing_ops_completed: boolean;
    core_first_runs_completed?: boolean;
    all_department_first_runs_completed?: boolean;
    completed_count?: number;
    playbooks_total?: number;
    completed_templates: string[];
    sessions: Array<{ template_id: string; session_id: string; status: string }>;
  };
  readiness_score?: number;
  simulate_path_complete?: boolean;
  blockers?: string[];
  optional_next_steps?: string[];
  oauth_progress?: {
    configured: number;
    connected: number;
    total: number;
    env_ready: boolean;
    connectors_ready: boolean;
  };
  profile?: VirtualCompanyProfile;
}

export interface ReadinessAudit {
  checklist: BootstrapChecklist;
  oauth_env: Record<string, boolean>;
  oauth_env_ready: boolean;
  readiness_score: number;
  blockers: string[];
}

export interface FirstRunPlaybook {
  template_id: string;
  title: string;
  goal: string;
  runtime_mode: "durable" | "inprocess";
  skills: string[];
  roles: string[];
}

export interface ConnectorInstallResult {
  slug: string;
  template_id: string;
  status: string;
  oauth_provider: string | null;
  connector_id: string | null;
}

export interface OAuthProviderRow {
  provider_key: string;
  label: string;
  template_id: string;
  configured: boolean;
}

export async function fetchVirtualCompanyProfile(): Promise<VirtualCompanyProfile> {
  return hiveGet<VirtualCompanyProfile>("virtual-company/profile");
}

export async function saveVirtualCompanyProfile(
  patch: Partial<Omit<VirtualCompanyProfile, "onboarded">>,
): Promise<VirtualCompanyProfile> {
  return hivePutJson<VirtualCompanyProfile>("virtual-company/profile", patch);
}

export async function fetchBootstrapChecklist(): Promise<BootstrapChecklist> {
  return hiveGet<BootstrapChecklist>("virtual-company/bootstrap-checklist");
}

export async function fetchReadinessAudit(): Promise<ReadinessAudit> {
  return hiveGet<ReadinessAudit>("virtual-company/readiness-audit");
}

export interface OAuthSetupGuide {
  redirect_uri: string;
  public_origin: string;
  all_configured: boolean;
  vendors: Array<{
    provider_key: string;
    label: string;
    env_id: string;
    env_secret: string;
    console_url: string;
    scopes_hint: string;
    configured: boolean;
  }>;
}

export async function fetchOAuthSetupGuide(): Promise<OAuthSetupGuide> {
  return hiveGet<OAuthSetupGuide>("virtual-company/oauth-setup-guide");
}

export async function applySoloBootstrap(): Promise<{ routing: { changed: boolean }; checklist: BootstrapChecklist }> {
  return hivePostJson("virtual-company/bootstrap-solo", {});
}

export async function seedDefaultProfile(): Promise<VirtualCompanyProfile> {
  return hivePostJson<VirtualCompanyProfile>("virtual-company/seed-default-profile", {});
}

export async function installFreeConnectors(): Promise<{
  installs: ConnectorInstallResult[];
  checklist: BootstrapChecklist;
}> {
  return hivePostJson("virtual-company/install-free-connectors", {});
}

export async function provisionSoloRouters(): Promise<{
  routers: Array<{ slug: string; status: string; is_active: boolean }>;
  checklist: BootstrapChecklist;
}> {
  return hivePostJson("virtual-company/provision-solo-routers", {});
}

export async function fetchFirstRunPlaybook(templateId: string): Promise<FirstRunPlaybook> {
  return hiveGet<FirstRunPlaybook>(`virtual-company/first-run/${encodeURIComponent(templateId)}`);
}

export async function startFirstRunSession(templateId: string): Promise<{
  session_id: string;
  template_id: string;
  goal_preview?: string;
  status?: string;
}> {
  return hivePostJson(`virtual-company/first-run/${encodeURIComponent(templateId)}/start-session`, {});
}

export async function buildDepartmentSwarm(templateId: string): Promise<{
  build: { status: string; swarm_id: string; agent_ids: string[] };
  checklist: BootstrapChecklist;
}> {
  return hivePostJson("virtual-company/build-department-swarm", {
    template_id: templateId,
    skip_if_exists: true,
  });
}

export async function buildAllDepartmentSwarms(includeSentinel = true): Promise<{
  builds: Array<{ status: string; template_id: string; swarm_id: string }>;
  checklist: BootstrapChecklist;
}> {
  return hivePostJson("virtual-company/build-all-departments", { include_sentinel: includeSentinel });
}

export async function fetchOAuthProviders(): Promise<{ providers: OAuthProviderRow[] }> {
  return hiveGet<{ providers: OAuthProviderRow[] }>("oauth/providers");
}

export function profileContextLine(profile: VirtualCompanyProfile): string {
  if (!profile.onboarded) {
    return "";
  }
  const areas = profile.focus_areas.length ? profile.focus_areas.join(", ") : "general";
  return `Operator: ${profile.brand_name} (${profile.industry}) · focus ${areas} · ${profile.primary_goal.slice(0, 160)}`;
}
