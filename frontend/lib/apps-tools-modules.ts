export type AppsToolsModuleStatus = "live" | "beta" | "stub";

/** Long-term product tier — core = revenue + harness; frozen = maintained but deprioritized. */
export type AppsToolsModuleTier = "core" | "frozen";

export interface AppsToolsModuleDef {
  moduleKey:
    | "marketing_automation"
    | "ecommerce_workspace"
    | "mcp_ops_studio"
    | "trading_automation"
    | "browser_automation"
    | "content_factory"
    | "research_workspace"
    | "analytics_workspace"
    | "trading_journal"
    | "skill_factory";
  slug: string;
  title: string;
  summary: string;
  status: AppsToolsModuleStatus;
  tier: AppsToolsModuleTier;
  href: string;
  capabilityKeys: string[];
}

export const APPS_TOOLS_MODULES: AppsToolsModuleDef[] = [
  {
    moduleKey: "skill_factory",
    slug: "skill-factory",
    title: "Skill Factory",
    summary: "Verified Niche Harness production — research → build → eval → GitHub/Gumroad export.",
    status: "live",
    tier: "core",
    href: "/apps-tools/skill-factory",
    capabilityKeys: ["apps.skill_factory.research.v1", "apps.skill_factory.build.v1"],
  },
  {
    moduleKey: "content_factory",
    slug: "content-factory",
    title: "Content Pack Factory",
    summary: "Niche social/content harness packs — same eval lane as Skill Factory.",
    status: "beta",
    tier: "core",
    href: "/apps-tools/content-factory#research",
    capabilityKeys: ["apps.content.factory.v1"],
  },
  {
    moduleKey: "analytics_workspace",
    slug: "analytics",
    title: "Analytics Workspace",
    summary: "Business question → read-only metrics → decision report with lineage and export staging.",
    status: "beta",
    tier: "core",
    href: "/apps-tools/analytics",
    capabilityKeys: ["apps.analytics.decision_report.v1"],
  },
  {
    moduleKey: "mcp_ops_studio",
    slug: "mcp-ops-studio",
    title: "MCP Ops Studio",
    summary: "MCP catalog, install queue, and tool health — harness integration layer.",
    status: "beta",
    tier: "core",
    href: "/apps-tools/mcp-ops-studio#catalog",
    capabilityKeys: ["apps.mcp.catalog.discover.v1"],
  },
  {
    moduleKey: "marketing_automation",
    slug: "marketing-automation",
    title: "Marketing Automation",
    summary: "Publish queue and social distribution — frozen until first Gumroad revenue.",
    status: "live",
    tier: "frozen",
    href: "/apps-tools/marketing-automation",
    capabilityKeys: ["apps.marketing.publish_pipeline.v1", "apps.marketing.omni_publish.compose.v1"],
  },
  {
    moduleKey: "research_workspace",
    slug: "research-workspace",
    title: "Research Workspace",
    summary: "Structured briefing flows — use Agents → Sessions for primary research.",
    status: "stub",
    tier: "frozen",
    href: "/apps-tools/research-workspace",
    capabilityKeys: ["apps.research.briefing.v1"],
  },
  {
    moduleKey: "ecommerce_workspace",
    slug: "ecommerce-automation",
    title: "E-commerce Ops",
    summary: "Shopify + Stripe sync — frozen (no paying niche yet).",
    status: "beta",
    tier: "frozen",
    href: "/apps-tools/ecommerce-automation",
    capabilityKeys: [
      "apps.ecommerce.shopify_sync.v1",
      "apps.ecommerce.stripe_checkout.v1",
      "apps.marketing.ga4_analytics.v1",
    ],
  },
  {
    moduleKey: "trading_journal",
    slug: "trading-journal",
    title: "Trading Journal",
    summary: "Learning Loop Studio — fields, review cron, Obsidian export, mistake recall.",
    status: "beta",
    tier: "frozen",
    href: "/apps-tools/trading-journal",
    capabilityKeys: ["apps.trading.journal_studio.v1"],
  },
  {
    moduleKey: "trading_automation",
    slug: "trading-automation",
    title: "Trading Automation",
    summary: "Trading cockpit — frozen (regulatory + commodity risk).",
    status: "beta",
    tier: "frozen",
    href: "/apps-tools/trading-automation",
    capabilityKeys: ["apps.trading.execution.v1", "apps.live_lane.execution.v1"],
  },
  {
    moduleKey: "browser_automation",
    slug: "browser-automation",
    title: "Browser Automation",
    summary: "Live browser lane — frozen; prefer MCP + supervised sessions.",
    status: "beta",
    tier: "frozen",
    href: "/apps-tools/browser-automation",
    capabilityKeys: ["apps.browser.automation.v1"],
  },
];

/** Primary modules shown on Apps & Tools index (12–24 mo strategy). */
export const APPS_TOOLS_MODULES_CORE: AppsToolsModuleDef[] = APPS_TOOLS_MODULES.filter(
  (row) => row.tier === "core",
);

/** Deprioritized modules — collapsible on index; routes still work. */
export const APPS_TOOLS_MODULES_FROZEN: AppsToolsModuleDef[] = APPS_TOOLS_MODULES.filter(
  (row) => row.tier === "frozen",
);

const MODULE_AGENT_USAGE: Record<AppsToolsModuleDef["moduleKey"], string> = {
  marketing_automation:
    "Frozen lane — publish after first harness products sell on Gumroad.",
  ecommerce_workspace:
    "Frozen — eshop sync when a commerce niche harness proves revenue.",
  mcp_ops_studio:
    "Connect MCP tools listed in TOOLS.json for each exported harness pack.",
  trading_automation:
    "Frozen — not part of first-revenue strategy.",
  browser_automation:
    "Frozen — supervised browser via Agents when explicitly needed.",
  content_factory:
    "Pack factory builds niche content harnesses with critic eval + Gumroad export.",
  analytics_workspace:
    "Codex-style reports via business-analytics-report template — fetch, analyze, critic, export simulate.",
  trading_journal:
    "Configure journal fields, overnight review cron, Obsidian subfolder, and mistake tags — HITL before vault write.",
  research_workspace:
    "Use Agents → New session for research; this stub remains for future briefing UX.",
  skill_factory:
    "Research → build → eval gate → Launch queue → GitHub/Gumroad (Verified Niche Harness).",
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
  analytics_workspace: "analytics",
  trading_journal: "trading",
  research_workspace: "research",
  skill_factory: "harness",
};
