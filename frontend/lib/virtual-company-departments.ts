/**
 * Virtual Company department registry — swarms as firm departments wired to Execution Studio.
 * Solo free-first: direct OAuth connectors only (Gmail, Notion, GitHub); default simulate mode.
 */

import type { SwarmWizardTemplateId } from "@/lib/swarm-wizard-templates";

export type VirtualCompanyDepartmentId =
  | "marketing"
  | "sales"
  | "finance"
  | "digital"
  | "rnd"
  | "product";

export type VirtualCompanyDepartmentStatus = "active" | "coming_soon";

/** Manager lane slugs — must match Super Tool Router + connector allowlists. */
export type DepartmentManagerSlug =
  | "content_creation"
  | "execution_operations"
  | "research_intelligence"
  | "review_quality"
  | "product_mission"
  | "personal_life";

export interface VirtualCompanyExecutionWire {
  default_mode: "simulate";
  live_requires_approval: true;
  free_first_routing: true;
  manager_slug: DepartmentManagerSlug;
  /** Super Tool Router preset hint (operator enables in Integrations). */
  super_router_preset?: "solo_app_actions" | "solo_dev_workspace";
  /** Suggested free OAuth connector slugs — operator installs in Connector hub. */
  suggested_connectors: string[];
}

export interface VirtualCompanyDepartment {
  id: VirtualCompanyDepartmentId;
  label: string;
  tagline: string;
  status: VirtualCompanyDepartmentStatus;
  templateId: SwarmWizardTemplateId | null;
  execution: VirtualCompanyExecutionWire | null;
}

/** Standard toolset for department bees — enables governed external execution. */
export const DEPARTMENT_EXECUTION_TOOLS = [
  "hive_memory_search",
  "task_list",
  "mcp_invoke",
] as const;

export const VIRTUAL_COMPANY_DEPARTMENTS: VirtualCompanyDepartment[] = [
  {
    id: "marketing",
    label: "Marketing",
    tagline: "Research → content → simulate publish (Notion, Gmail)",
    status: "active",
    templateId: "marketing-ops",
    execution: {
      default_mode: "simulate",
      live_requires_approval: true,
      free_first_routing: true,
      manager_slug: "content_creation",
      super_router_preset: "solo_app_actions",
      suggested_connectors: ["notion_workspace", "gmail_workspace"],
    },
  },
  {
    id: "sales",
    label: "Sales",
    tagline: "Lead pipeline → outreach drafts → approval before send",
    status: "active",
    templateId: "lead-waterfall",
    execution: {
      default_mode: "simulate",
      live_requires_approval: true,
      free_first_routing: true,
      manager_slug: "execution_operations",
      super_router_preset: "solo_app_actions",
      suggested_connectors: ["gmail_workspace", "notion_workspace"],
    },
  },
  {
    id: "finance",
    label: "Finance",
    tagline: "Read-only reports and cashflow summaries — no live banking",
    status: "active",
    templateId: "finance-ops",
    execution: {
      default_mode: "simulate",
      live_requires_approval: true,
      free_first_routing: true,
      manager_slug: "review_quality",
      suggested_connectors: ["notion_workspace"],
    },
  },
  {
    id: "digital",
    label: "E-commerce / Digital",
    tagline: "Shopify + Stripe + competitor research — simulate-first",
    status: "active",
    templateId: "eshop-ops",
    execution: {
      default_mode: "simulate",
      live_requires_approval: true,
      free_first_routing: true,
      manager_slug: "research_intelligence",
      super_router_preset: "solo_app_actions",
      suggested_connectors: ["shopify_admin", "stripe_rest", "notion_workspace", "apify_store"],
    },
  },
  {
    id: "rnd",
    label: "R&D / Development",
    tagline: "Codebase health, GitHub PR lane, opportunity research",
    status: "active",
    templateId: "rnd-dev",
    execution: {
      default_mode: "simulate",
      live_requires_approval: true,
      free_first_routing: true,
      manager_slug: "research_intelligence",
      super_router_preset: "solo_dev_workspace",
      suggested_connectors: ["github_rest", "notion_workspace"],
    },
  },
  {
    id: "product",
    label: "Product",
    tagline: "PRD → slices → GitHub/Notion ship lane",
    status: "active",
    templateId: "product-ship",
    execution: {
      default_mode: "simulate",
      live_requires_approval: true,
      free_first_routing: true,
      manager_slug: "product_mission",
      super_router_preset: "solo_dev_workspace",
      suggested_connectors: ["github_rest", "notion_workspace"],
    },
  },
];

/** Future departments — architecture slot only (Swarm Builder shows Soon). */
export const VIRTUAL_COMPANY_FUTURE_DEPARTMENTS: Array<{
  id: string;
  label: string;
  tagline: string;
}> = [
  { id: "hr", label: "HR", tagline: "Recruiting templates, culture docs" },
  { id: "support", label: "Customer Support", tagline: "Ticket drafts, FAQ updates" },
  { id: "legal", label: "Legal", tagline: "Read-only contract research" },
  { id: "operations", label: "Operations", tagline: "Cross-dept process efficiency" },
  { id: "supply", label: "Supply Chain", tagline: "Supplier intelligence" },
  { id: "pr", label: "PR & Comms", tagline: "Press drafts, media lists" },
  { id: "ceo", label: "Executive Office", tagline: "Cross-dept briefings" },
];

const EXECUTION_PROMPT_SUFFIX =
  " Use Execution Studio policy: default simulate; live writes only after operator approval. Prefer free OAuth connectors (Notion, Gmail, GitHub). Never skip simulation before reporting.";

export function executionPromptSuffix(): string {
  return EXECUTION_PROMPT_SUFFIX;
}

export function getDepartmentByTemplateId(
  templateId: SwarmWizardTemplateId,
): VirtualCompanyDepartment | undefined {
  return VIRTUAL_COMPANY_DEPARTMENTS.find((d) => d.templateId === templateId);
}

export function buildSwarmLocalMemoryForTemplate(templateId: SwarmWizardTemplateId): Record<string, unknown> {
  const dept = getDepartmentByTemplateId(templateId);
  if (dept?.execution) {
    return {
      virtual_company_department: dept.id,
      manager_slug: dept.execution.manager_slug,
      execution_studio: {
        default_mode: dept.execution.default_mode,
        live_requires_approval: dept.execution.live_requires_approval,
        free_first_routing: dept.execution.free_first_routing,
        super_router_preset: dept.execution.super_router_preset ?? null,
        suggested_connectors: dept.execution.suggested_connectors,
      },
    };
  }
  if (templateId === "sentinel-radar") {
    return {
      manager_slug: "research_intelligence",
      virtual_company_sentinel: true,
      execution_studio: {
        default_mode: "simulate",
        live_requires_approval: true,
        read_only: true,
      },
    };
  }
  if (templateId === "exec-assistant") {
    return { manager_slug: "personal_life" };
  }
  if (templateId === "life-os") {
    return { manager_slug: "personal_life" };
  }
  if (templateId === "content-flywheel") {
    return { manager_slug: "content_creation" };
  }
  return { manager_slug: "personal_life" };
}

export function activeVirtualCompanyTemplateIds(): SwarmWizardTemplateId[] {
  return VIRTUAL_COMPANY_DEPARTMENTS.filter((d) => d.status === "active" && d.templateId).map(
    (d) => d.templateId as SwarmWizardTemplateId,
  );
}
