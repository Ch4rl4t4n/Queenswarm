export type AppsToolsModuleStatus = "live" | "beta" | "stub";

export interface AppsToolsModuleDef {
  moduleKey:
    | "marketing_automation"
    | "ecommerce_workspace"
    | "mcp_ops_studio"
    | "trading_automation"
    | "browser_automation"
    | "content_factory"
    | "research_workspace"
    | "skill_factory";
  slug: string;
  title: string;
  summary: string;
  status: AppsToolsModuleStatus;
  href: string;
  capabilityKeys: string[];
}

export const APPS_TOOLS_MODULES: AppsToolsModuleDef[] = [
  {
    moduleKey: "marketing_automation",
    slug: "marketing-automation",
    title: "Marketing Automation",
    summary: "Publish queue, social distribution, and performance loop in one workspace.",
    status: "live",
    href: "/apps-tools/marketing-automation",
    capabilityKeys: ["apps.marketing.publish_pipeline.v1", "apps.marketing.omni_publish.compose.v1"],
  },
  {
    moduleKey: "skill_factory",
    slug: "skill-factory",
    title: "Skill Factory",
    summary: "Research market niches, auto-build verified skills, export GitHub packs — no in-app sales.",
    status: "live",
    href: "/apps-tools/skill-factory",
    capabilityKeys: ["apps.skill_factory.research.v1", "apps.skill_factory.build.v1"],
  },
  {
    moduleKey: "ecommerce_workspace",
    slug: "ecommerce-automation",
    title: "E-commerce Ops",
    summary: "Shopify + Stripe order sync, webhook queue, and eshop-ops swarm workspace.",
    status: "beta",
    href: "/apps-tools/ecommerce-automation",
    capabilityKeys: [
      "apps.ecommerce.shopify_sync.v1",
      "apps.ecommerce.stripe_checkout.v1",
      "apps.marketing.ga4_analytics.v1",
    ],
  },
  {
    moduleKey: "mcp_ops_studio",
    slug: "mcp-ops-studio",
    title: "MCP Ops Studio",
    summary: "MCP catalog discovery, install governance, health checks, and lifecycle controls.",
    status: "stub",
    href: "/apps-tools/mcp-ops-studio",
    capabilityKeys: ["apps.mcp.catalog.discover.v1"],
  },
  {
    moduleKey: "trading_automation",
    slug: "trading-automation",
    title: "Trading Automation",
    summary: "Trading cockpit controls and guarded live execution handoff.",
    status: "beta",
    href: "/apps-tools/trading-automation",
    capabilityKeys: ["apps.trading.execution.v1", "apps.live_lane.execution.v1"],
  },
  {
    moduleKey: "browser_automation",
    slug: "browser-automation",
    title: "Browser Automation",
    summary: "Operator-approved browser/live lane automations and action governance.",
    status: "beta",
    href: "/apps-tools/browser-automation",
    capabilityKeys: ["apps.browser.automation.v1"],
  },
  {
    moduleKey: "content_factory",
    slug: "content-factory",
    title: "Content Factory",
    summary: "Media agency lane and micro-SaaS factory workflows in one module.",
    status: "beta",
    href: "/apps-tools/content-factory",
    capabilityKeys: ["apps.content.factory.v1"],
  },
  {
    moduleKey: "research_workspace",
    slug: "research-workspace",
    title: "Research Workspace",
    summary: "Structured briefing and transcript extraction flows for swarm decisions.",
    status: "stub",
    href: "/apps-tools/research-workspace",
    capabilityKeys: ["apps.research.briefing.v1"],
  },
];

const MODULE_AGENT_USAGE: Record<AppsToolsModuleDef["moduleKey"], string> = {
  marketing_automation:
    "Publish lanes compose social packs and push approved items through omni-publish capabilities when the workspace is live.",
  ecommerce_workspace:
    "Eshop-ops swarms sync Shopify and Stripe order events, then route webhook payloads into automation lanes.",
  mcp_ops_studio:
    "Agents discover MCP manifests, install connectors, and run health checks before supervisor lanes bind tools.",
  trading_automation:
    "Trading cockpit lanes invoke guarded execution capabilities with policy gates before any live handoff.",
  browser_automation:
    "Operator-approved browser sessions run live-lane automations with explicit approval guardrails per action.",
  content_factory:
    "Media agency and micro-SaaS factory lanes generate assets via content-factory capabilities in sequence.",
  research_workspace:
    "Research bees extract briefings and transcripts into swarm decisions via structured research capabilities.",
  skill_factory:
    "Research lane scores niches from HiveMind; factory sessions produce tenant skills exported to GitHub/Gumroad.",
};

/** Operator-facing copy for the “How agents use this” block on module cards. */
export function appsToolsModuleAgentUsage(module: AppsToolsModuleDef): string {
  return MODULE_AGENT_USAGE[module.moduleKey];
}

export const APPS_TOOLS_MODULE_CATEGORY: Record<AppsToolsModuleDef["moduleKey"], string> = {
  marketing_automation: "marketing",
  ecommerce_workspace: "commerce",
  mcp_ops_studio: "mcp",
  trading_automation: "trading",
  browser_automation: "browser",
  content_factory: "content",
  research_workspace: "research",
  skill_factory: "content",
};
