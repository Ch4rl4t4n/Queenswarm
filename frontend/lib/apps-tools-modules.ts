export type AppsToolsModuleStatus = "live" | "beta" | "stub";

export interface AppsToolsModuleDef {
  moduleKey:
    | "marketing_automation"
    | "ecommerce_workspace"
    | "mcp_ops_studio"
    | "trading_automation"
    | "browser_automation"
    | "content_factory"
    | "research_workspace";
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
    moduleKey: "ecommerce_workspace",
    slug: "ecommerce-automation",
    title: "E-commerce Ops",
    summary: "Shopify + Stripe order sync, webhook queue, and eshop-ops swarm workspace.",
    status: "beta",
    href: "/apps-tools/ecommerce-automation",
    capabilityKeys: ["apps.ecommerce.shopify_sync.v1", "apps.ecommerce.stripe_checkout.v1"],
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
