/** Platform capabilities atlas — live features, architecture, and roadmap (Settings export source). */

export type CapabilityPriority = "P0" | "P1" | "P2" | "P3" | "P4";
export type CapabilityImpact = "high" | "medium" | "low";
export type CapabilityStatus = "live" | "beta" | "flagged";
export type RolloutPhase = "phase0" | "phase1" | "phase2" | "phase3" | "ops";
export type PlannedOwner = "operator" | "dev" | "both";

export interface CapabilityStackHint {
  frontend?: string[];
  backend?: string[];
}

export interface PlatformCapability {
  id: string;
  section: string;
  name: string;
  status: CapabilityStatus;
  summary: string;
  howItWorks: string;
  value: string;
  competitiveEdge: string;
  routes?: string[];
  stack?: CapabilityStackHint;
}

export interface PlannedCapability {
  id: string;
  name: string;
  priority: CapabilityPriority;
  impact: CapabilityImpact;
  rolloutPhase: RolloutPhase;
  summary: string;
  rationale: string;
  competitiveEdge: string;
  hints?: string;
  targetPhase?: string;
  week?: number;
  owner?: PlannedOwner;
  auditGate?: string;
}

/** Mission north star — synced with docs/MISSION_EXECUTION_BACKLOG.md */
export const MISSION_NORTH_STAR = {
  metric: "Verified workflows / active user / week",
  tagline: "Agent Operating System — self-improving hive, not another chatbot.",
  phase0Weeks: 4,
  phase0Hours: "80–120",
} as const;

export const ROLLOUT_PHASE_LABELS: Record<RolloutPhase, string> = {
  phase0: "Fáza 0 · Revenue + hero wizard (4 týždne)",
  phase1: "Fáza 1 · Marketplace + stickiness (mesiace 2–6)",
  phase2: "Fáza 2 · Scale + enterprise (mesiace 7–12)",
  phase3: "Fáza 3 · Ecosystem",
  ops: "Ops · Blockery & infra",
};

export interface ArchitectureLayer {
  id: string;
  label: string;
  tone: "cyan" | "pollen" | "purple" | "green" | "magenta" | "zinc";
  nodes: { id: string; label: string; detail: string }[];
}

export const PLATFORM_ARCHITECTURE_LAYERS: ArchitectureLayer[] = [
  {
    id: "client",
    label: "Frontend · Next.js 15",
    tone: "cyan",
    nodes: [
      { id: "app-router", label: "App Router UI", detail: "RSC + client islands, Tailwind v4, shadcn" },
      { id: "pwa", label: "PWA shell", detail: "Service worker, offline, mobile bottom nav" },
      { id: "proxy", label: "/api/proxy", detail: "JWT cookie → FastAPI, WebSocket passthrough" },
    ],
  },
  {
    id: "edge",
    label: "Edge · TLS + Nginx",
    tone: "pollen",
    nodes: [
      { id: "nginx", label: "Reverse proxy", detail: "queenswarm.love, rate-limit headers" },
      { id: "auth-edge", label: "Session cookies", detail: "Refresh + tenant context" },
    ],
  },
  {
    id: "api",
    label: "Backend · FastAPI",
    tone: "purple",
    nodes: [
      { id: "rest", label: "REST /api/v1", detail: "43 routers, Pydantic v2, JWT guards" },
      { id: "ws", label: "WebSocket", detail: "Ballroom, supervisor audit live feed" },
      { id: "langgraph", label: "LangGraph", detail: "Supervisor orchestration + sub-agents" },
    ],
  },
  {
    id: "worker",
    label: "Workers · Celery",
    tone: "magenta",
    nodes: [
      { id: "celery", label: "Async tasks", detail: "Routines tick, workflows, simulations" },
      { id: "beat", label: "Celery Beat", detail: "Scheduled supervisor + hive sync jobs" },
    ],
  },
  {
    id: "data",
    label: "Data plane",
    tone: "green",
    nodes: [
      { id: "pg", label: "PostgreSQL + pgvector", detail: "Tenants, sessions, recipes, vectors" },
      { id: "redis", label: "Redis", detail: "Rate limits, cache, leaderboard, capsules" },
      { id: "neo", label: "Neo4j", detail: "HiveMind graph, imitation chains" },
      { id: "chroma", label: "Chroma / vault", detail: "Embeddings + Obsidian markdown vault" },
    ],
  },
  {
    id: "llm",
    label: "LLM router",
    tone: "zinc",
    nodes: [
      { id: "litellm", label: "LiteLLM", detail: "Grok primary, Claude fallback, GPT-4o-mini cheap" },
      { id: "sandbox", label: "Docker sandbox", detail: "256MB, no network, verified outputs only" },
    ],
  },
];

export const LIVE_PLATFORM_CAPABILITIES: PlatformCapability[] = [
  {
    id: "dashboard",
    section: "Overview",
    name: "Queen Dashboard",
    status: "live",
    summary: "Command center so stavom swarmu, workflows a health signálmi.",
    howItWorks: "Agreguje `/dashboard/summary`, zobrazuje stat grid, hybrid runtime a waggle feed.",
    value: "Jeden vstupný bod pred každou operáciou — vidíš tlak hosta aj aktívne toky.",
    competitiveEdge: "Bee-hive density UI s realtime pollen glow namiesto statického BI dashboardu.",
    routes: ["/", "/dashboard"],
    stack: { frontend: ["queen-dashboard-chrome.tsx"], backend: ["dashboard.py"] },
  },
  {
    id: "supervisor-sessions",
    section: "Agents",
    name: "Dynamic Supervisor Sessions",
    status: "live",
    summary: "Multi-step supervisor s sub-agentmi, approve/reject a needs_input.",
    howItWorks: "LangGraph session lifecycle cez `/agents/sessions`, shared context + event log.",
    value: "Bezpečná autonómia — high-risk kroky nikdy neobídu manuálny review.",
    competitiveEdge: "Light control plane + skills packs namiesto monolitného „auto-GPT“ agenta.",
    routes: ["/agents#sessions"],
    stack: { frontend: ["agents-sessions-panel.tsx"], backend: ["agent_sessions.py"] },
  },
  {
    id: "agents-roster",
    section: "Agents",
    name: "Agent roster & spawn",
    status: "live",
    summary: "Správa včiel, swarm lanes a spawn z template library.",
    howItWorks: "CRUD agentov, bee role types, `/agents/new` wizard s tenant templates.",
    value: "Každá včela = jedna rola — composable swarm namiesto jedného mega-promptu.",
    competitiveEdge: "Template library s edit/delete a API-backed role types.",
    routes: ["/agents", "/agents/new"],
    stack: { backend: ["agents.py", "agent_templates.py"] },
  },
  {
    id: "learning-loop",
    section: "Agents",
    name: "Learning loop & context graph",
    status: "live",
    summary: "Memory evolution, agent initiatives a Neo4j context constellation.",
    howItWorks: "Poll `/hive-mind/memory-evolution` + `/agents/suggestions`, graph z `/hive-mind/graph`.",
    value: "Schválené učenie naprieč sessionami, nie len single-run memory.",
    competitiveEdge: "Graf + vector fallback s explicitnými approval gates.",
    routes: ["/agents"],
    stack: { frontend: ["agents-learning-loop-panel.tsx", "agents-context-graph-strip.tsx"] },
  },
  {
    id: "tasks",
    section: "Execution",
    name: "Tasks & execution queue",
    status: "live",
    summary: "Prioritizovaná fronta úloh s filtrami a lane cards.",
    howItWorks: "Tasks API + client filters, sync tlačidlo pre queue refresh.",
    value: "Operačná viditeľnosť medzi supervisor rozhodnutím a doručením.",
    competitiveEdge: "Prepojenie task → session → recipe v jednom IA hub-e.",
    routes: ["/tasks"],
    stack: { backend: ["tasks.py"] },
  },
  {
    id: "routines",
    section: "Execution",
    name: "Supervisor routines",
    status: "live",
    summary: "Periodické supervisor sessions cez Celery beat.",
    howItWorks: "Flag `ROUTINES_ENABLED`, tick `hive.supervisor_routines_tick`.",
    value: "Opakované procesy bez manuálneho spúšťania.",
    competitiveEdge: "Routines sú súčasť supervisor control plane, nie oddelený cron systém.",
    routes: ["/agents#sessions"],
    stack: { backend: ["agent_sessions.py"] },
  },
  {
    id: "workflows",
    section: "Execution",
    name: "Workflows DAG",
    status: "live",
    summary: "Vizualizácia a spúšťanie workflow grafov.",
    howItWorks: "Workflows router + DAG page s pause/resume toggles.",
    value: "Transparentná orchestrácia pre komplexné multi-step delivery.",
    competitiveEdge: "Overené kroky sa ukladajú do Recipe Library automaticky.",
    routes: ["/workflows"],
    stack: { backend: ["workflows.py"] },
  },
  {
    id: "hivemind",
    section: "Knowledge",
    name: "HiveMind retrieval",
    status: "live",
    summary: "Neo4j graph + pgvector/Chroma semantic search + vault export.",
    howItWorks: " `/hive-mind/search`, `/hive-mind/graph`, Obsidian vault sync.",
    value: "Retrieval-first — menej tokenov, vyššia presnosť kontextu.",
    competitiveEdge: "Graceful degradation: Neo4j down → vector fallback stále funguje.",
    routes: ["/knowledge#hivemind"],
    stack: { backend: ["hive_mind.py"] },
  },
  {
    id: "recipes",
    section: "Knowledge",
    name: "Recipe Library",
    status: "live",
    summary: "Overené workflowy s hybrid scoring (vector + imitation graph).",
    howItWorks: "Recipes API, playbook auto-save po approve, cosine + graph blend.",
    value: "Opakovateľné playbooks namiesto one-off promptov.",
    competitiveEdge: "Imitation engine v backend-e — recepty sa učia z úspešných susedov.",
    routes: ["/knowledge#recipes"],
    stack: { backend: ["recipes.py"] },
  },
  {
    id: "integrations-hub",
    section: "Integrations",
    name: "Integrations hub",
    status: "live",
    summary: "Connectors, marketplace, plugins, external projects v jednom paneli.",
    howItWorks: "Tab routing `?tab=`, ecosystem lane, refresh pulse API.",
    value: "Jeden cockpit pre celý tool lattice.",
    competitiveEdge: "One-click marketplace install → okamžite dostupné supervisor lanes.",
    routes: ["/integrations"],
    stack: { frontend: ["integrations-page-client.tsx"] },
  },
  {
    id: "connectors",
    section: "Integrations",
    name: "Dynamic Connector Hub (MCP)",
    status: "live",
    summary: "OAuth consent, vault, connector provisioning a ping test.",
    howItWorks: "Phase 3 connectors console, Fernet-encrypted secrets.",
    value: "Bezpečné napojenie externých API bez hardcoded keys v kóde.",
    competitiveEdge: "MCP-native hub s tenant RBAC a rate limits per connector.",
    routes: ["/integrations?tab=hub"],
    stack: { backend: ["connectors.py", "connectors_dynamic.py"] },
  },
  {
    id: "plugins",
    section: "Integrations",
    name: "Plugin lattice",
    status: "live",
    summary: "Built-in moduly + operator `.py` upload s on/off switchmi.",
    howItWorks: " `/plugins` catalog, enable/disable endpoints, reload generation.",
    value: "Rýchle rozšírenie hive bez redeploy.",
    competitiveEdge: "Hot-reload user plugins v sandboxovanom worker prostredí.",
    routes: ["/integrations?tab=plugins"],
    stack: { backend: ["plugins_catalog.py"] },
  },
  {
    id: "browser-harness",
    section: "Integrations",
    name: "Browser harness",
    status: "live",
    summary: "Live browser sessions s domain guardrails a approval flow.",
    howItWorks: " `/agents/browser-sessions` API, critical action approve.",
    value: "Web automation bez slepej dôvery v agenta.",
    competitiveEdge: "Explicit approval pred kritickými akciami — nie headless free-for-all.",
    routes: ["/agents"],
    stack: { backend: ["agent_sessions.py"] },
  },
  {
    id: "ballroom",
    section: "Ballroom",
    name: "Realtime Ballroom",
    status: "live",
    summary: "Voice + text session s orchestrátorom cez WebSocket.",
    howItWorks: "WS stream, Grok live voice, chat history slider, quick prompts.",
    value: "Operačný kanál počas incidentov a deploy flowov.",
    competitiveEdge: "Multimodal lane prepojená na supervisor sessions — nie izolovaný chatbot.",
    routes: ["/ballroom"],
    stack: { frontend: ["ballroom-panel.tsx"], backend: ["realtime_ballroom.py"] },
  },
  {
    id: "simulations",
    section: "Platform",
    name: "Simulation sandbox",
    status: "flagged",
    summary: "Docker-isolated verification pred reportom výsledku userovi.",
    howItWorks: "256MB, no network, 30s timeout — len verified outputs uniknú von.",
    value: "Filozofia hive: nikdy raw LLM output bez simulácie.",
    competitiveEdge: "Hard sandbox enforcement vs. „trust the model“ konkurencia.",
    routes: ["/simulations"],
    stack: { backend: ["simulations.py"] },
  },
  {
    id: "audit-digest",
    section: "Settings",
    name: "Supervisor audit & digest",
    status: "live",
    summary: "Session audit trail, CSV/JSON export, email/Slack/Discord/Teams digest.",
    howItWorks: "Audit logs + schedule v Settings → Audit, Command Center rollup.",
    value: "Compliance a incident forensics bez externého SIEM.",
    competitiveEdge: "Realtime audit WS + playbook auto-save do recipes.",
    routes: ["/settings/audit"],
    stack: { backend: ["realtime_supervisor_audit.py"] },
  },
  {
    id: "platform-matrix",
    section: "Settings",
    name: "Platform feature matrix",
    status: "live",
    summary: "Internal vs commercial tier kill-switches pre každú sekciu.",
    howItWorks: "Admin UI `/settings/platform`, overrides v DB, route guards.",
    value: "Jeden deploy — viac produktových režimov.",
    competitiveEdge: "Feature matrix per tenant tier bez forkovania kódu.",
    routes: ["/settings/platform"],
    stack: { frontend: ["platform-features-settings-panel.tsx"], backend: ["platform_features_admin.py"] },
  },
  {
    id: "command-center",
    section: "Settings",
    name: "Command Center",
    status: "live",
    summary: "Disk/memory/container health, audit rollup, recovery actions.",
    howItWorks: "Admin panel agreguje system status + cross-tenant audit.",
    value: "Operator NOC view priamo v appke.",
    competitiveEdge: "Send digest / send rollup bez SSH na host.",
    routes: ["/settings/command-center"],
    stack: { backend: ["command_center_admin.py", "system_status.py"] },
  },
  {
    id: "responsive-pwa",
    section: "Platform",
    name: "Responsive shell + PWA",
    status: "live",
    summary: "Mobile drawer, bottom nav, FAB, offline shell, install prompt.",
    howItWorks: "Breakpoints ≤1023 mobile/tablet, service worker cache busting.",
    value: "Plná operabilita z mobilu počas walkthrough a incidentov.",
    competitiveEdge: "Desktop sidebar-only IA bez duplicitných top barov.",
    routes: ["all hubs"],
    stack: { frontend: ["dashboard-shell.tsx", "hive-bottom-nav.tsx"] },
  },
  {
    id: "swarm-builder",
    section: "Swarms",
    name: "Swarm Builder wizard",
    status: "live",
    summary: "Exec Assistant, Lead Waterfall, Content Flywheel — 3 agenti + routine za ~10 min.",
    howItWorks: "POST /swarms + /agents/dynamic + /agents/routines orchestrated from `/swarms/new`.",
    value: "Non-coder time-to-value bez prompt engineeringu.",
    competitiveEdge: "Opinionated colonies vs. prázdny agent harness.",
    routes: ["/swarms/new", "/dashboard"],
    stack: { frontend: ["swarm-builder-wizard.tsx", "swarm-wizard-templates.ts"] },
  },
  {
    id: "pro-tier-gates-live",
    section: "Commercial",
    name: "Pro tier feature gates",
    status: "live",
    summary: "Commercial Free: 2 agenti, 1 swarm; Ballroom + Recipes = Pro.",
    howItWorks: "billing.assert_agent_hard_limit + platform_features min_tier + upgrade banner.",
    value: "Freemium monetizácia bez forkovania deployu.",
    competitiveEdge: "Jeden hive, viac produktových režimov.",
    routes: ["/settings/billing", "/agents/new", "/swarms/new"],
    stack: { backend: ["billing.py", "platform_features.py"], frontend: ["pro-upgrade-banner.tsx"] },
  },
  {
    id: "pro-subscription-checkout",
    section: "Commercial",
    name: "Pro subscription checkout",
    status: "live",
    summary: "Stripe Checkout pre Pro tier — self-serve upgrade z /settings/billing.",
    howItWorks: "POST /billing/pro-checkout → webhook checkout.session.completed (queenswarm_checkout=pro_tier) → tier=pro.",
    value: "Commercial Free → Pro bez operátora (po STRIPE_PRO_PRICE_ID).",
    competitiveEdge: "Subscription aj skill checkout v jednom hive billing routeri.",
    routes: ["/settings/billing"],
    stack: {
      backend: ["pro_subscription_checkout.py", "billing.py"],
      frontend: ["pro-upgrade-checkout-button.tsx", "billing-settings-panel.tsx"],
    },
  },
  {
    id: "capabilities-atlas",
    section: "Settings",
    name: "Capabilities Atlas",
    status: "live",
    summary: "Live features, architektúra BE/FE, phased roadmap, export PDF/MD/TXT.",
    howItWorks: "Katalóg v platform-capabilities-catalog.ts, UI `/settings/capabilities`.",
    value: "Jeden zdroj pravdy pre operátora aj produkt.",
    competitiveEdge: "Transparentný stack + roadmap priamo v appke.",
    routes: ["/settings/capabilities"],
    stack: { frontend: ["settings-capabilities-panel.tsx"] },
  },
  {
    id: "rapid-loop-widget",
    section: "Dashboard",
    name: "Rapid learning loop widget",
    status: "live",
    summary: "Scrape → reflect → simulate → reward s SLA metrikami na dashboarde.",
    howItWorks: "GET /dashboard/rapid-loop + `rapid-loop-widget.tsx`, poll každých ~30s.",
    value: "Viditeľný self-improvement loop — nie black box.",
    competitiveEdge: "Merateľný <60s verified cycle priamo v UI.",
    routes: ["/dashboard"],
    stack: { backend: ["dashboard_rapid_loop.py"], frontend: ["rapid-loop-widget.tsx"] },
  },
  {
    id: "dreaming-nightly-summary-live",
    section: "Dashboard",
    name: "Dreaming nightly summary",
    status: "live",
    summary: "Posledný dreaming cyklus + stav na dashboarde, plné ovládanie v Knowledge.",
    howItWorks: "GET /dreaming/settings + /dreaming/cycles — `dreaming-summary-card.tsx`.",
    value: "Produktový „wow“ moment pre nightly memory consolidation.",
    competitiveEdge: "Daily hive consolidation viditeľná operátorovi.",
    routes: ["/dashboard", "/knowledge"],
    stack: { frontend: ["dreaming-summary-card.tsx"] },
  },
  {
    id: "foragers-launch-live",
    section: "Agents",
    name: "Foragers production launch",
    status: "live",
    summary: "YouTube/RSS/API ingest workers — internal + commercial Pro tier.",
    howItWorks: "platform_features foragers min_tier=pro (commercial), route `/foragers`.",
    value: "Ingest → HiveMind → spawn agent v jednom loop-e.",
    competitiveEdge: "Natívny ingest bez externého ETL.",
    routes: ["/foragers"],
    stack: { backend: ["platform_features.py", "foragers.py"], frontend: ["foragers-page-client.tsx"] },
  },
  {
    id: "builtin-plugin-persist-live",
    section: "Integrations",
    name: "Built-in plugin persistent toggle",
    status: "live",
    summary: "HiveSwitch v Integrations → Plugins persistuje enabled flag cez PATCH.",
    howItWorks: "PATCH /plugins/{id} → plugin_hub manifest overlay + reload generation.",
    value: "Operator kontrola lattice bez redeploy.",
    competitiveEdge: "Perzistentné built-in toggles na disk.",
    routes: ["/integrations?tab=plugins"],
    stack: {
      backend: ["plugins_catalog.py", "plugin_hub.py"],
      frontend: ["integrations-page-client.tsx"],
    },
  },
  {
    id: "swarm-builder-entry-live",
    section: "Dashboard",
    name: "Swarm Builder dashboard entry",
    status: "live",
    summary: "CTA karta s deep linkmi na Exec Assistant, Lead Waterfall, Content Flywheel.",
    howItWorks: "`swarm-builder-entry-card.tsx` na dashboarde, linky `/swarms/new?template=…`.",
    value: "Time-to-value bez hľadania wizardu v menu.",
    competitiveEdge: "Opinionated onboarding priamo v colony view.",
    routes: ["/dashboard", "/swarms/new"],
    stack: { frontend: ["swarm-builder-entry-card.tsx"] },
  },
  {
    id: "time-saved-roi-live",
    section: "Dashboard",
    name: "Time saved ROI analytics",
    status: "live",
    summary: "Verified workflow hours saved by template — „koľko si ušetril“ panel.",
    howItWorks: "GET /dashboard/time-saved + `time-saved-panel.tsx` on dashboard.",
    value: "Konkrétne ROI číslo pre Pro upgrade a marketing.",
    competitiveEdge: "Merateľný benefit namiesto vague AI productivity.",
    routes: ["/dashboard"],
    stack: { backend: ["dashboard_time_saved.py"], frontend: ["time-saved-panel.tsx"] },
  },
  {
    id: "recipe-cosine-match-live",
    section: "Knowledge",
    name: "Recipe cosine matching UI (0.85)",
    status: "live",
    summary: "Transparentný imitation match score v Recipes, Learning a New Task.",
    howItWorks: "GET /recipes/match-config + `recipe-cosine-match-panel.tsx`.",
    value: "Operátor vidí prečo sa recept matchol — dôvera v imitation engine.",
    competitiveEdge: "Hybrid scoring viditeľný v UI — nie black box.",
    routes: ["/recipes", "/learning"],
    stack: { backend: ["recipe_match_config.py"], frontend: ["recipe-cosine-match-panel.tsx"] },
  },
  {
    id: "skill-marketplace-ugc-live",
    section: "Integrations",
    name: "Skill marketplace UGC",
    status: "live",
    summary: "Tenant-submitted listings, curator queue, 25% platform cut on checkout.",
    howItWorks: "POST /recipes/marketplace/listings + `skill-marketplace-ugc-panel.tsx`.",
    value: "Druhý revenue stream + community verified workflows.",
    competitiveEdge: "UGC marketplace + imitation v jednom hive.",
    routes: ["/integrations?tab=skills"],
    stack: {
      backend: ["skill_marketplace_ugc.py", "skill_marketplace_listing.py"],
      frontend: ["skill-marketplace-ugc-panel.tsx"],
    },
  },
  {
    id: "ugc-lead-magnets-live",
    section: "Dashboard",
    name: "UGC lead magnets",
    status: "live",
    summary: "Share cards + public `/magnet/[templateId]` landing pages.",
    howItWorks: "marketing router + `lead-magnet-panel.tsx` + public magnet pages.",
    value: "Organický acquisition z verified swarm templates.",
    competitiveEdge: "Swarm output → shareable artifact, nie chat screenshot.",
    routes: ["/dashboard", "/magnet"],
    stack: { backend: ["ugc_content_engine.py"], frontend: ["lead-magnet-panel.tsx"] },
  },
  {
    id: "sub-swarm-mind-live",
    section: "Swarms",
    name: "Sub-swarm local hive mind UI",
    status: "live",
    summary: "Lokálna koordinácia 5–10 včiel + sync progress bar každých 5 min.",
    howItWorks: "GET /swarms/{id}/local-mind + `sub-swarm-local-mind-panel.tsx`.",
    value: "Decentralizácia viditeľná operátorovi — nie central bottleneck.",
    competitiveEdge: "Bee-hive sync bez monolitického coordinator UI.",
    routes: ["/swarms", "/dashboard"],
    stack: { backend: ["sub_swarm_local_mind.py"], frontend: ["sub-swarm-local-mind-panel.tsx"] },
  },
  {
    id: "bee-gamification-live",
    section: "Leaderboard",
    name: "Bee badges & gamification",
    status: "live",
    summary: "Verified-workflow badges, leaderboard chips, dashboard panel.",
    howItWorks: "GET /learning/bee-badges + `bee-badges-panel.tsx`.",
    value: "Virálny prestige layer na simulation-verified pollen.",
    competitiveEdge: "Playful hive vs. sterile enterprise AI tools.",
    routes: ["/leaderboard", "/dashboard"],
    stack: { backend: ["bee_gamification.py"], frontend: ["bee-badges-panel.tsx"] },
  },
  {
    id: "enterprise-workspace-live",
    section: "Settings",
    name: "White-label + enterprise compliance",
    status: "live",
    summary: "Branding overrides, compliance export bundle, HA profile readout.",
    howItWorks: "GET/PATCH /settings/enterprise/config + shell branding via /auth/me.",
    value: "Enterprise sales story — audit export bez vendor lock-in.",
    competitiveEdge: "Decentralized hive + compliance bundle v jednom produkte.",
    routes: ["/settings/enterprise"],
    stack: {
      backend: ["enterprise_workspace.py", "settings_enterprise.py", "dr_drill_evidence.py"],
      frontend: ["enterprise-settings-panel.tsx", "hive-brand-mark.tsx"],
    },
  },
  {
    id: "enterprise-subscription-checkout",
    section: "Commercial",
    name: "Enterprise subscription checkout",
    status: "live",
    summary: "Self-serve Pro → Enterprise upgrade cez Stripe Checkout.",
    howItWorks: "POST /billing/enterprise-checkout (Pro required) → webhook enterprise_tier → tier=enterprise.",
    value: "Commercial matrix — seat upgrade bez operátora.",
    competitiveEdge: "Pro aj Enterprise checkout v jednom billing routeri.",
    routes: ["/settings/billing", "/settings/enterprise"],
    stack: {
      backend: ["enterprise_subscription_checkout.py", "billing.py"],
      frontend: ["enterprise-upgrade-checkout-button.tsx", "billing-settings-panel.tsx"],
    },
  },
  {
    id: "ha-chaos-evidence-live",
    section: "Ops",
    name: "HA chaos drill evidence",
    status: "live",
    summary: "ha-chaos-smoke.sh writes JSON; Enterprise panel shows Redis outage/recovery proof.",
    howItWorks: "Quarterly ./scripts/ha-chaos-smoke.sh → reports/ha/*.json → build_ha_profile_status().ha_chaos.",
    value: "Chaos readiness visible in-app (+5 readiness when passed).",
    competitiveEdge: "DR + chaos evidence bez SSH — enterprise audit trail.",
    routes: ["/settings/enterprise"],
    stack: { backend: ["ha_chaos_evidence.py"], frontend: ["enterprise-settings-panel.tsx"] },
  },
  {
    id: "ha-dr-drill-evidence-live",
    section: "Ops",
    name: "HA + DR drill evidence",
    status: "live",
    summary: "dr-drill.sh writes JSON+MD; Enterprise panel shows latest evidence.",
    howItWorks: "Mount reports/dr → build_ha_profile_status().dr_drill in enterprise config API.",
    value: "Quarterly DR drill visible bez SSH — audit-ready.",
    competitiveEdge: "Ops evidence in-app, nie len shell skripty.",
    routes: ["/settings/enterprise"],
    stack: { backend: ["dr_drill_evidence.py"], frontend: ["enterprise-settings-panel.tsx"] },
  },
  {
    id: "cockpit-telemetry-bundle-live",
    section: "Dashboard",
    name: "Cockpit telemetry bundle",
    status: "live",
    summary: "Single GET /dashboard/cockpit — agents, tasks, summary, lite system gauges.",
    howItWorks: "`CockpitTelemetryProvider` + `dashboard_cockpit.py` replace 4 parallel polls.",
    value: "Binance-style dashboard — fewer boot bursts, bounded payloads.",
    competitiveEdge: "One round-trip colony hydration vs. chatbot poll storms.",
    routes: ["/dashboard"],
    stack: {
      backend: ["dashboard_cockpit.py"],
      frontend: ["cockpit-telemetry-provider.tsx", "cockpit-performance-budget.ts"],
    },
  },
  {
    id: "cockpit-ws-delta-live",
    section: "Dashboard",
    name: "Cockpit WS delta feed",
    status: "live",
    summary: "hive.snapshot patches agent/task KPIs without full HTTP refetch.",
    howItWorks: "`hive_live_pulse.py` → `applyCockpitWsDelta` + `applyTaskQueueWsDelta` on /ws/live.",
    value: "Live colony feel with 60s poll fallback when socket connected.",
    competitiveEdge: "Push-first telemetry like trading terminals — not blind polling.",
    routes: ["/dashboard"],
    stack: {
      backend: ["hive_live_pulse.py"],
      frontend: ["cockpit-ws-delta.ts", "use-cockpit-live-pulse.ts"],
    },
  },
  {
    id: "agents-virtual-roster-live",
    section: "Agents",
    name: "Virtual agent roster (list + grid cap)",
    status: "live",
    summary: "TanStack virtual list + honeycomb cap on /agents at 200 bees.",
    howItWorks: "`AgentsVirtualList` + `COCKPIT_PERF.gridInitialRender` on full roster page.",
    value: "Smooth scroll at scale — main thread stays under budget.",
    competitiveEdge: "Heavy rosters without jank — eToro/Binance list UX pattern.",
    routes: ["/agents"],
    stack: { frontend: ["agents-virtual-list.tsx", "agents-live-section.tsx"] },
  },
];

export const PLANNED_PLATFORM_CAPABILITIES: PlannedCapability[] = [
  {
    id: "stripe-live",
    name: "Stripe live checkout",
    priority: "P0",
    impact: "high",
    rolloutPhase: "phase0",
    week: 1,
    owner: "operator",
    auditGate: "./scripts/finish-stripe-setup.sh",
    summary: "Produkčné platby — Pro + Enterprise subscription + premium skills checkout.",
    rationale: "Revenue blocker — checkout implementované; operátor doplní STRIPE_* + STRIPE_PRO_PRICE_ID + STRIPE_ENTERPRISE_PRICE_ID v .env.prod.",
    competitiveEdge: "Natívny billing v hive, nie externý portal.",
    hints: "Stripe Dashboard webhook → checkout.session.completed na /api/v1/billing/stripe/webhook.",
    targetPhase: "Commercial",
  },
  {
    id: "prod-walkthrough-signoff",
    name: "Authenticated prod walkthrough sign-off",
    priority: "P1",
    impact: "high",
    rolloutPhase: "phase0",
    week: 1,
    owner: "operator",
    auditGate: "docs/AUTHENTICATED_PROD_WALKTHROUGH.md",
    summary: "Operátor dokončí manuálny QA checklist na produkcii.",
    rationale: "Confidence gate pred marketing launchom — žiadne raw outputs bez simulácie.",
    competitiveEdge: "Verified-only UX je diferenciátor oproti krehkým single-agent harnessom.",
    targetPhase: "Quality",
  },
  {
    id: "hetzner-abuse-closure",
    name: "Hetzner abuse ticket closure",
    priority: "P0",
    impact: "medium",
    rolloutPhase: "ops",
    owner: "operator",
    auditGate: "./scripts/hetzner-abuse-reply.sh",
    summary: "Uzavrieť AbuseID 11B0286:23 s abuse@hetzner.com.",
    rationale: "Infra risk — odpoveď pripravená v skripte.",
    competitiveEdge: "—",
    targetPhase: "Ops",
  },
];

/** Group live capabilities by section for rendering. */
export function groupCapabilitiesBySection(
  items: PlatformCapability[],
): { section: string; items: PlatformCapability[] }[] {
  const map = new Map<string, PlatformCapability[]>();
  for (const item of items) {
    const list = map.get(item.section) ?? [];
    list.push(item);
    map.set(item.section, list);
  }
  return Array.from(map.entries()).map(([section, grouped]) => ({ section, items: grouped }));
}

const ROLLOUT_PHASE_ORDER: RolloutPhase[] = ["phase0", "phase1", "phase2", "phase3", "ops"];

/** Group planned roadmap items by rollout phase (stable order). */
export function groupPlannedByRolloutPhase(
  items: PlannedCapability[],
): { phase: RolloutPhase; label: string; items: PlannedCapability[] }[] {
  const map = new Map<RolloutPhase, PlannedCapability[]>();
  for (const item of items) {
    const list = map.get(item.rolloutPhase) ?? [];
    list.push(item);
    map.set(item.rolloutPhase, list);
  }
  return ROLLOUT_PHASE_ORDER.filter((phase) => map.has(phase)).map((phase) => ({
    phase,
    label: ROLLOUT_PHASE_LABELS[phase],
    items: (map.get(phase) ?? []).sort((a, b) => {
      const pa = a.priority.localeCompare(b.priority);
      if (pa !== 0) {
        return pa;
      }
      return (a.week ?? 99) - (b.week ?? 99);
    }),
  }));
}
