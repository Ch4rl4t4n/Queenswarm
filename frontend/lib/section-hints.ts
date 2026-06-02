/** Central registry — every section/tool header hint (title → description → inline i). */

export interface SectionHint {
  title: string;
  description: string;
  options: string[];
  manualHref?: string;
}

export const SECTION_HINTS = {
  // —— Page-level (HivePageHeader) ——
  settings: {
    title: "Settings hub",
    description:
      "Everything that configures how your tenant hive behaves: who can access it, which AI keys and channels are active, spend limits, and audit exports.",
    options: [
      "Account & security — 2FA, team RBAC, public sharing, notification channels, audit log.",
      "Hive & AI — LLM/voice keys, harness behavioral memory, capabilities atlas, external API keys.",
      "Ops & billing — plan usage, cost cockpit, enterprise workspace policy.",
      "Admin (internal tenants) — platform feature matrix, accounts CMS, command center.",
    ],
    manualHref: "/manual#settings",
  },
  knowledge: {
    title: "Knowledge plane",
    description:
      "Unified retrieval surface: HiveMind graph, verified outputs archive, recipes, dreaming cycles, curated memory, Wiki Layer (Karpathy hot/cold tiers), and goal tracking.",
    options: [
      "HiveMind tab — graphify, project shape, selective recall, Ingest URL (YouTube/web), explorer search, memory evolution.",
      "Wiki Layer tab — 3 zones (raw / wiki / instructions), Gardener bee, retrieval tier, Obsidian export.",
      "Outputs — Ballroom deliverables and archive with interactive replay.",
      "Recipes & dreaming — verified workflows and overnight consolidation loops.",
    ],
    manualHref: "/manual#knowledge",
  },
  cockpit: {
    title: "Agentic OS (optional — not the first step)",
    description:
      "Advanced automation: Innovation Lab, Four Lanes digests, Hotline. Start each day in Agents, not here.",
    options: [
      "Four Lanes — cron digests (optional)",
      "Innovation Lab — tech proposals → PR",
      "Manual: /manual#background-automation",
    ],
    manualHref: "/manual#background-automation",
  },
  appsTools: {
    title: "Apps & Tools",
    description:
      "Modular domain workspaces — marketing, trading, content factory, MCP ops, and browser automation — each isolated by capability contracts.",
    options: [
      "Module index — policy packs, risk tiers, and live/beta status per workspace.",
      "Deep links — open a module without losing Integrations or Agentic OS context.",
      "Factory & Foragers — reachable from index or mobile More menu, not primary rail.",
    ],
    manualHref: "/manual#apps-tools",
  },
  agents: {
    title: "Agents — primary control",
    description:
      "Launch all work here: New supervisor session → structured PROJECT goal → durable → Info report. Swarms and Agentic OS are not the start.",
    options: [
      "Session goal — Goal → Context → Constraints → Done",
      "Auto-approve ON for solo · durable for large projects",
      "Info → PDF report when completed",
      "Manual: /manual#canonical-workflow",
    ],
    manualHref: "/manual#canonical-workflow",
  },
  integrations: {
    title: "Integrations hub",
    description:
      "Connectors, MCP servers, tools marketplace, external projects, execution studio, and plugin lattice for outbound actions.",
    options: [
      "MCP hub — model context protocol servers and vault secrets.",
      "Execution Studio — workflows, skills forge, innovation lab.",
      "External projects — webhook lanes and publish connectors.",
    ],
    manualHref: "/manual#integrations",
  },
  ballroom: {
    title: "Ballroom",
    description:
      "Realtime voice and chat lane tied to supervisor sessions — waggle transcripts, live swarm orchestration, and dump/sleep cycles.",
    options: [
      "Voice + chat — multi-bee dialogue with verified publish guardrails.",
      "Supervisor tie-in — sessions mirror Agents control plane.",
      "Dump & sleep — overnight consolidation before morning publish.",
    ],
    manualHref: "/manual#ballroom",
  },
  swarms: {
    title: "Swarms",
    description:
      "Colony control plane for decentralized sub-hives: local hive memory, lane binding, immune status, and periodic global sync.",
    options: [
      "Colony cards — active routines, autopilot, pause/resume.",
      "Swarm Builder — compose bees + lanes from templates.",
      "Hive sync ACK — acknowledge sub-swarm → global hive mind sync.",
    ],
    manualHref: "/manual#swarms",
  },
  factory: {
    title: "Micro-SaaS Factory",
    description:
      "Simulate-first pipeline: scope → landing → auth → billing → deploy for solo-operator mini apps.",
    options: [
      "Blueprint phases — stack presets and disclaimer before live spend.",
      "Spawn factory swarm — binds marketing + deploy bees.",
      "Execution Studio — full workflow in Integrations → Factory tab.",
    ],
    manualHref: "/manual#factory",
  },
  tasks: {
    title: "Tasks",
    description:
      "Mission queue for async jobs, workflow lanes, Celery depth, and verified completions before user-facing output.",
    options: [
      "Queue lanes — pending, running, blocked, completed today.",
      "Workflows DAG — visual factory chains from Tasks tab.",
      "Sync — poll Redis/Celery-backed queue without blocking UI.",
    ],
    manualHref: "/manual#tasks",
  },
  dashboard: {
    title: "Queen Dashboard",
    description:
      "At-a-glance hive health: agent counts, swarm signals, pollen KPIs, waggle feed, and rapid learning loop status.",
    options: [
      "KPI tiles — agents, tasks, pollen, sync freshness.",
      "Swarm builder entry — quick path to new colony.",
      "Section density — toggle comfortable vs compact in layout gear.",
    ],
    manualHref: "/manual#dashboard",
  },
  manual: {
    title: "Operator manual",
    description:
      "Single canonical workflow step-by-step plus settings reference. Start at section 0.",
    options: [
      "0. Canonical workflow — Agents → session",
      "5. Settings reference",
      "docs/OPERATOR_CANONICAL_WORKFLOW.md",
    ],
    manualHref: "/manual#canonical-workflow",
  },

  // —— Cockpit cards ——
  overview: {
    title: "Operator overview",
    description:
      "Your daily command surface: prioritized actions from overnight dump, publish queue, trading halt, and onboarding gaps.",
    options: [
      "Start day — triggers My 3 Bees trio cycle (Life OS + bound lanes).",
      "Trust Autopilot — Telegram pings only after simulated/verified outcomes.",
      "Proof-of-Hive — shareable HMAC receipts after publish simulate approval.",
      "Refresh — reloads core snapshot without heavy futurist modules.",
    ],
    manualHref: "/manual#cockpit-overview",
  },
  fourLanes: {
    title: "Four Lanes (optional)",
    description:
      "Background cron digests — open via Agentic OS → Show advanced tools → Lanes. Not your daily start; use Agents → Sessions for projects.",
    options: [
      "Lane A — Najman marketing digest (Po/St/Pi) + competitor forager.",
      "Lane B — Tech SCV daily upgrades → Innovation Lab → Queen Maintainer PR.",
      "Lane C — E-shop research (Ut/Št) for beebrdy.cz benchmark + SEO.",
      "Lane D — Automation factory: manual trigger after you approve digests.",
      "Bootstrap lanes — pauses non-lane routines; safe to re-run (idempotent).",
    ],
    manualHref: "/manual#four-lanes",
  },
  fourLaneDigestInbox: {
    title: "Digest Inbox",
    description:
      "Unified queue of four-lane digest sessions. Review excerpt, open session, or promote marketing/e-shop digests to Tasks in one click.",
    options: [
      "→ Task — approves session + creates backlog row with digest excerpt (simulate-first).",
      "Tech SCV lane — use Innovation tab for upgrade proposals, not task promote.",
      "Pending count — sessions in needs_input or completed without linked task.",
      "Full loop doc: /manual#digest-inbox",
    ],
    manualHref: "/manual#digest-inbox",
  },
  command: {
    title: "Command lane",
    description:
      "Three operator entry points: natural-language routing (Hotline), structured intent → swarm plan (Crystallizer), and Telegram Zero-UI when web is optional.",
    options: [
      "Hotline — one sentence → Queen goal with bee routing.",
      "Crystallizer — preview trust lane + templates before launch.",
      "Zero-UI — configure bot token in Execution Studio notifications.",
    ],
    manualHref: "/manual#cockpit-command",
  },
  beeHotline: {
    title: "Bee Hotline",
    description:
      "Type what you need in plain language. The operator gateway routes to the correct bee/swarm lane and opens a Queen goal — no manual navigation.",
    options: [
      "Example: “Approve publish queue and draft LinkedIn post from last brief”.",
      "Runs server-side via POST /operator/act action=hotline.",
      "Use when you know the outcome but not which panel to open.",
    ],
    manualHref: "/manual#bee-hotline",
  },
  intentCrystallizer: {
    title: "Intent Crystallizer",
    description:
      "Turns free text into a structured plan: suggested Factory/swarm templates, trust lane (auto/simulate/live), and deep links. Preview before spending tokens on a full Queen run.",
    options: [
      "Preview — shows title, trust lane, template labels, primary href.",
      "Launch — creates Queen goal with crystallized plan.",
      "Best for net-new work: research, landing pages, publish briefs.",
    ],
    manualHref: "/manual#intent-crystallizer",
  },
  zeroUi: {
    title: "Zero-UI Hive Mode",
    description:
      "Operate the hive from Telegram: /day, /status, /hotline, /factory, /crystal. Web UI becomes optional once bot token, chat id, and webhook secret are set.",
    options: [
      "Configure in Integrations → Execution Studio → notifications.",
      "Webhook URL must be reachable from Telegram (HTTPS).",
      "Commands mirror Cockpit actions — same verify-first guardrails.",
    ],
    manualHref: "/manual#zero-ui-hive",
  },
  icm: {
    title: "ICM tools",
    description:
      "Intent Capture Module — quick automations, URL brief ingest, and dialogue extract without opening the swarm builder. Outputs can land in Harness, Knowledge, or Recipe draft.",
    options: [
      "Quick Automations — one-click verified presets.",
      "Link Drop — fetch URL → structured brief → optional Knowledge save.",
      "Dialogue Extract — transcript → goals, constraints, decisions, next steps.",
    ],
    manualHref: "/manual#icm-tools",
  },
  icmQuickAutomations: {
    title: "Quick Automations",
    description:
      "One-click verified presets — morning check, summarize link, publish brief, and more. No builder; each action runs through simulate-first guardrails.",
    options: [
      "Presets call POST /operator/icm/quick with a preset id.",
      "Hover a pill for the preset detail tooltip.",
      "Outputs route to Cockpit toast + optional Knowledge/Recipe side effects.",
    ],
    manualHref: "/manual#icm-tools",
  },
  icmLinkDrop: {
    title: "Link Drop",
    description:
      "Paste a URL → read-only fetch → structured brief (title, summary, bullets). Preview before saving to Knowledge.",
    options: [
      "Preview — fetch + parse without persisting.",
      "Save to Knowledge — embeds brief into HiveMind vault.",
      "Read-only fetch — no auth cookies, sandboxed outbound.",
    ],
    manualHref: "/manual#icm-tools",
  },
  icmDialogueExtract: {
    title: "Dialogue Extract",
    description:
      "Paste a transcript (Ballroom, Dump & Sleep, meeting notes) → goals, constraints, decisions, next steps. Route to Harness, Knowledge, or Recipe draft.",
    options: [
      "Extract — preview structured fields only.",
      "→ Harness — appends to behavioral / curated memory.",
      "→ Knowledge — saves excerpt + metadata to vault.",
    ],
    manualHref: "/manual#icm-tools",
  },
  fleet: {
    title: "Swarm Fleet",
    description:
      "Always-on supervisor routines with Trust Autopilot scheduling. Pause/resume without losing bees. Immune system marks watch/quarantine after failure streaks.",
    options: [
      "Pause — stops cron/autopilot for a routine.",
      "Resume — re-enables schedule without re-binding lanes.",
      "Immune status — healthy / watch / quarantine from failure telemetry.",
    ],
    manualHref: "/manual#swarm-fleet",
  },
  modules: {
    title: "Futurist modules",
    description:
      "Lazy-loaded experimental capabilities (Regret Simulator, Context Teleport, Ambient Forager, Parallel Hive, Evolutionary Recipes). Compose-only — they reuse existing bees, never duplicate swarms.",
    options: [
      "Loaded on demand — keeps Cockpit core fast.",
      "Evolutionary Recipes — ranks variants after 3+ verified outcomes.",
      "Regret Simulator — scores “what if we waited” before live actions.",
    ],
    manualHref: "/manual#cockpit-modules",
  },
  innovation: {
    title: "Innovation Lab",
    description:
      "Brainstorm new product features. Approved proposals queue Queen Maintainer for PR-only implementation — never direct writes to main.",
    options: [
      "Brainstorm — creates pending proposal with risk + module tags.",
      "Approve / Reject — human gate before any code changes.",
      "Implement — triggers Maintainer agent (PR workflow).",
      "Open full workflow in Execution Studio → Innovation tab.",
    ],
    manualHref: "/manual#innovation-lab",
  },
  oracle: {
    title: "Hive Oracle",
    description:
      "Predictive warnings from fleet telemetry, publish lane, and trio heuristics. Verify-first — every warning includes a Fix route. Optional LLM synthesis for a cheap operator brief.",
    options: [
      "Warnings — severity + confidence from overnight signals and publish queue.",
      "Predictions — short horizon (today / week) likelihood estimates.",
      "Synthesis — enable HIVE_ORACLE_LLM_SYNTHESIS_ENABLED for LLM-light brief.",
    ],
    manualHref: "/manual#hive-oracle",
  },
  oraclePredictions: {
    title: "Oracle predictions",
    description: "Short-horizon forward view — today and week likelihood estimates from fleet heuristics. Treat as signals, not commands.",
    options: [
      "Likelihood % — heuristic confidence, not LLM certainty.",
      "Pair with warnings tab before taking live action.",
      "Refresh reloads telemetry without LLM synthesis cost.",
    ],
    manualHref: "/manual#hive-oracle",
  },

  // —— Agents ecosystem ——
  agentsRoles: {
    title: "Bee role types",
    description:
      "Eleven archetype templates (researcher, critic, publisher, …). Clone or extend to spawn custom bees with guardrails and pollen rewards baked in.",
    options: [
      "New template — opens /agents/new with role preset.",
      "Edit / delete — admin-only on tenant templates.",
      "Each role maps to BaseAgent subclass + default workflow steps.",
    ],
    manualHref: "/manual#bee-roles",
  },
  agentsRuntime: {
    title: "Hybrid runtime",
    description: "Live status of LangGraph runners, Celery workers, and session locks across the tenant.",
    options: [
      "Green — worker healthy and accepting tasks.",
      "Amber — degraded or backlog pressure.",
      "Open session — jumps to Supervisor tab.",
    ],
    manualHref: "/manual#agents",
  },
  agentsContext: {
    title: "Context graph",
    description: "Neo4j-backed semantic links between sessions, recipes, outputs, and curated memory nodes.",
    options: [
      "Strip view — recent edges from active sessions.",
      "Expand — full graph panel with filter chips.",
      "Used by Queen for retrieval-aware prompting.",
    ],
    manualHref: "/manual#context-graph",
  },
  agentsLearning: {
    title: "Learning loop",
    description: "Rapid loop telemetry: scrape → reflect → simulate → reward → recipe save under 60s when feasible.",
    options: [
      "Pollen — awarded only after verified simulation.",
      "Imitation engine — top performers copied by neighbors.",
      "Recipe cosine match threshold 0.85 for auto-reuse.",
    ],
    manualHref: "/manual#learning-loop",
  },
  agentsSessions: {
    title: "Supervisor sessions",
    description: "Live and historical Queen/supervisor runs — approve merges, kill stuck agents, export session reports.",
    options: [
      "Session search — filter by goal, status, swarm.",
      "Merge ready — human approve before publish lane.",
      "Report dialog — Session → Recipe when verified.",
    ],
    manualHref: "/manual#supervisor",
  },
  agentsRoster: {
    title: "Active roster",
    description: "Currently running bees with swarm binding, pollen totals, and last task outcome.",
    options: [
      "Pause bee — stops new tasks without deleting config.",
      "Pollen glow — proportional to verified outcomes.",
      "Click row — opens agent detail / session tie-in.",
    ],
    manualHref: "/manual#agents",
  },
  agentsHierarchy: {
    title: "Hierarchy graph",
    description: "Swarm ↔ bee topology — decentralized sub-hives with local memory and ~5 min global sync.",
    options: [
      "Collapsible — large graphs stay performant on mobile.",
      "Edge types — reports-to, shares-recipe, sync-lane.",
      "Does not mutate swarms — read-only topology.",
    ],
    manualHref: "/manual#hierarchy",
  },

  // —— Knowledge ——
  knowledgeRetrievalContract: {
    title: "Retrieval contract",
    description:
      "Queen bootstrap context: curated memory prefix, Wiki Layer block (when enabled), customer history, policy snippets, and last tasks injected on every new mission.",
    options: [
      "wiki_only — hot tier only: curated prefix + Gardener wiki pages (default, lowest token cost).",
      "deep_raw — hot + cold: adds HiveMind raw RAG chunks for deep recall (higher cost).",
      "Purple block — active retrieval contract string in selective recall preview.",
      "Gold block — skill pack preset (context + decide + tdd + diagnose).",
    ],
    manualHref: "/manual#wiki-layer",
  },
  knowledgeExplorer: {
    title: "HiveMind explorer",
    description: "Neo4j semantic graph with ChromaDB vector fallback — search, ingest shortcuts, and retrieval-aware prompts.",
    options: [
      "Quick ingest task — /tasks/new with vault hook.",
      "Quick ingest supervisor — /agents#sessions.",
      "Graph + vault unified in one search surface.",
    ],
    manualHref: "/manual#hivemind",
  },
  knowledgeOutputs: {
    title: "Outputs archive",
    description: "Verified deliverables from Ballroom and publish lane — semantic search, regenerate, PDF/markdown export.",
    options: [
      "Interactive replay — step through verified workflow.",
      "Regenerate — re-run simulate-first pipeline.",
      "Export — PDF or markdown with proof metadata.",
    ],
    manualHref: "/manual#outputs",
  },
  knowledgeWikiLayer: {
    title: "Wiki Layer (Karpathy tiers)",
    description:
      "Hot/cold memory split: curated instructions + Gardener-maintained wiki pages go to the Queen prompt; raw HiveMind chunks stay in the cold zone unless you switch to deep_raw.",
    options: [
      "3 zones — raw (cold vault), wiki (Gardener pages), instructions (curated behavioral memory).",
      "Default tier wiki_only — fastest prompts, ~fewer tokens; deep_raw adds raw RAG when you need full recall.",
      "Auto Gardener — Celery sweep every 5 min consolidates verified outputs into wiki pages.",
      "Manual: /manual#wiki-layer",
    ],
    manualHref: "/manual#wiki-layer",
  },
  knowledgeWikiZones: {
    title: "Three memory zones",
    description:
      "Visual breakdown of what the Queen sees vs what stays in cold storage. Char counts update after each Gardener run.",
    options: [
      "Raw zone — unfiltered HiveMind chunks, forager dumps, session logs (cold; skipped when wiki_only).",
      "Wiki zone — four Gardener pages: operator-context, project-briefs, forager-insights, verified-recipes.",
      "Instructions zone — Settings → AI · harness curated memory (always injected first).",
    ],
    manualHref: "/manual#wiki-layer",
  },
  knowledgeWikiRetrievalTier: {
    title: "Retrieval tier switch",
    description:
      "Controls how much context is injected into every new Queen session. Change takes effect on the next session bootstrap.",
    options: [
      "wiki_only — curated prefix + wiki pages only; HiveMind raw RAG is skipped (recommended solo default).",
      "deep_raw — wiki_only content plus full HiveMind vector/graph retrieval for complex cross-project recall.",
      "Telemetry row — last prompt char counts for curated, wiki, and raw blocks.",
    ],
    manualHref: "/manual#wiki-layer",
  },
  knowledgeWikiGardener: {
    title: "Wiki Gardener bee",
    description:
      "Background bee that sweeps verified outputs, recipes, and forager intel into consolidated wiki pages. Runs automatically every 5 minutes via Celery beat.",
    options: [
      "Run Gardener now — immediate sweep without waiting for the 5 min tick.",
      "Pollen reward — Gardener earns pollen when pages are updated with verified content.",
      "First session — if no wiki pages exist, Queen auto-triggers one Gardener run before prompt assembly.",
    ],
    manualHref: "/manual#wiki-layer",
  },
  knowledgeWikiObsidian: {
    title: "Obsidian export",
    description:
      "Download the current wiki pages as a Markdown vault zip — compatible with Obsidian, Logseq, or any local note app.",
    options: [
      "Includes all four Gardener pages with frontmatter (slug, version, updated_at).",
      "Read-only export — does not sync changes back to Queenswarm.",
      "Use for offline review, sharing briefs, or backup before major curated memory edits.",
    ],
    manualHref: "/manual#wiki-layer",
  },
  knowledgeWikiTelemetry: {
    title: "Prompt token telemetry",
    description:
      "Live char counts from the last Queen bootstrap — shows how much each zone contributed to the assembled prompt.",
    options: [
      "curated_prefix_chars — behavioral instructions from Settings harness.",
      "wiki_chars — combined Gardener wiki pages injected in hot tier.",
      "raw_chars — cold-zone RAG only counted when retrieval_tier is deep_raw.",
    ],
    manualHref: "/manual#wiki-layer",
  },
  knowledgeIngestRouter: {
    title: "Ingest Router + Research Bee",
    description:
      "Unified ingest lane: YouTube URL → transcript bee, https article → Research Bee fetch, paste → structured brief. Never injects raw transcript into Queen prompt — persist goes to HiveMind raw, Gardener compiles wiki.",
    options: [
      "YouTube — auto-detect watch/youtu.be/shorts URLs, fetch captions (no Data API quota).",
      "Web URL — public https only; SSRF-safe HTML text extract.",
      "Persist + Run Gardener — optional immediate forager-insights wiki refresh.",
      "Manual: /manual#ingest-router",
    ],
    manualHref: "/manual#ingest-router",
  },
  knowledgeYouTubeIngest: {
    title: "YouTube transcript ingest",
    description:
      "Drop any public YouTube link — YouTubeTranscriptBee pulls captions/auto-transcript, Research Bee structures summary + key points.",
    options: [
      "Requires captions or auto-generated transcript on the video.",
      "Tags: forager:youtube, youtube_transcript — Gardener picks up in forager-insights.",
      "Pair with wiki_only tier — hot wiki, cold raw until deep_raw.",
    ],
    manualHref: "/manual#ingest-router",
  },
  knowledgeSkillHotTier: {
    title: "Skill Hot Tier (Karpathy)",
    description:
      "On each new Queen session, only verified recipes that token-match the session goal are injected — never the full Recipe Library dump.",
    options: [
      "SKILL_HOT_TIER_ENABLED — default on; max 3 recipes per session.",
      "Complements Wiki Layer verified-recipes page (static compile) with dynamic goal match.",
      "Inspired by Karpathy modular skills — our skills = verified recipes + harness.",
      "Manual: /manual#skill-hot-tier",
    ],
    manualHref: "/manual#skill-hot-tier",
  },

  // —— Integrations ——
  integrationsActive: {
    title: "Active integrations",
    description: "Unified health snapshot across MCP hub rows, OAuth bridges, and plugin lattice connectors.",
    options: [
      "Healthy count badge — probes last 24h success rate.",
      "Retry — re-runs connection test for error cards.",
      "Open — jumps to hub, studio, or marketplace tab.",
    ],
    manualHref: "/manual#integrations",
  },
  integrationsHub: {
    title: "Connector hub",
    description: "Phase 3 MCP hub: OAuth consent, provision templates, vault secrets, and connection testing.",
    options: [
      "Unified Tool Hub — roster + probe in one panel.",
      "Connectors console — add slug, base URL, auth type.",
      "Vault sync — ciphertext never echoes in JSON responses.",
    ],
    manualHref: "/manual#mcp-hub",
  },
  integrationsHubTools: {
    title: "Unified Tool Hub",
    description: "Orchestrated MCP registry ranked by goal overlap — cost and latency hints for supervisor lane routing.",
    options: [
      "Goal filter — rank tools by mission text.",
      "Featured preset — Venice MCP one-click install.",
      "Collector deck — All / Ranked / Low cost / Fast tabs.",
    ],
    manualHref: "/manual#mcp-hub",
  },
  integrationsHubOAuth: {
    title: "OAuth connect",
    description: "Hosted consent for Gmail, Calendar, GitHub, Slack, Meta, X, and TikTok — pairs with Phase 3 templates.",
    options: [
      "Connect — redirects to vendor OAuth then seals token in vault.",
      "Callback — returns to hub with success/error toast.",
      "Use before provisioning social publish templates.",
    ],
    manualHref: "/manual#mcp-hub",
  },
  integrationsHubVault: {
    title: "Vault secrets",
    description: "Seal API keys and OAuth tokens — ping handshake and egress probe before bees call upstream.",
    options: [
      "Vendor presets — quick-fill slug + token fields.",
      "Rotate OAuth — refresh token without re-provisioning.",
      "Probe — GET egress test with sealed credentials.",
    ],
    manualHref: "/manual#mcp-hub",
  },
  integrationsHubTemplates: {
    title: "Phase 3 templates",
    description: "Curated MCP manifests by category — full-width grid with pagination; provision or prefill the add form.",
    options: [
      "Category bubbles — email, comms, devtools, billing, …",
      "Provision — instantiates hub row from template.",
      "Prefill — copies manifest into Add new connector form.",
    ],
    manualHref: "/manual#marketplace",
  },
  integrationsHubRoster: {
    title: "Roster & add",
    description: "Combined dynamic hub rows plus manual connector form — test, enable/disable, remove custom rows.",
    options: [
      "Add new connector — seal manifest + secrets once.",
      "Combined roster — paginated hub rows from API.",
      "Test · 2500ms — outbound probe per connector.",
    ],
    manualHref: "/manual#mcp-hub",
  },
  integrationsHubObsidian: {
    title: "Obsidian vault",
    description: "Markdown mirror under HIVE_MIND_VAULT_ROOT embeds into Chroma when watch mode is on.",
    options: [
      "Watch mode — poll interval from env.",
      "Force embedding pass — manual sync trigger.",
      "Pairs with Knowledge HiveMind recall.",
    ],
    manualHref: "/manual#knowledge",
  },
  integrationsMarketplace: {
    title: "Tools marketplace",
    description: "Curated MCP templates — provision or prefill connector form from category grid.",
    options: [
      "Phase 3 categories — billing, comms, devtools, etc.",
      "Provision — instantiates hub row from template.",
      "Paginated grid — switch pages at the bottom of each category.",
    ],
    manualHref: "/manual#marketplace",
  },
  integrationsStudio: {
    title: "Execution Studio",
    description: "Workflow builder, skills forge, social publish, trading cockpit, innovation lab, and morning pipeline.",
    options: [
      "Sub-panels lazy-load — keeps Integrations tab fast.",
      "Publish lane — simulate-first until OAuth + approve.",
      "Innovation — full brainstorm flow also in Cockpit.",
    ],
    manualHref: "/manual#execution-studio",
  },
  integrationsExternal: {
    title: "External projects",
    description: "Webhook bridges to operator-owned repos and vaults — mint secrets once, external side stays yours.",
    options: [
      "Register bridge — one-time secret display.",
      "Registry — active bridges for this dashboard session.",
      "No inbound code execution — verify-first payloads only.",
    ],
    manualHref: "/manual#external-projects",
  },

  // —— Swarms page cards ——
  swarmsColonies: {
    title: "Colonies",
    description:
      "Each card is a decentralized SubSwarm with local LangGraph memory; Maynard-Cross pollen rewards apply on verified outcomes.",
    options: [
      "Pause / wake — local hive keeps state.",
      "Expand row — lane detail + immune status.",
      "Global sync ACK — confirms 5 min hive mind merge.",
    ],
    manualHref: "/manual#swarms",
  },
  swarmsImmune: {
    title: "Swarm immune system",
    description: "Failure streak telemetry — healthy, watch, or quarantine before autopilot spreads bad recipes.",
    options: [
      "Watch — elevated failure rate, still running.",
      "Quarantine — autopilot paused until operator review.",
      "Recommendation text — suggested fix route per routine.",
    ],
    manualHref: "/manual#swarm-fleet",
  },

  // —— Settings panels (representative) ——
  settingsHarness: {
    title: "AI harness",
    description: "Behavioral memory, skill lattice, MCP tool grid, and intelligence scan proposals for Queen prompts.",
    options: [
      "Behavioral instructions — injected as === BEHAVIORAL INSTRUCTIONS ===.",
      "Intelligence scan — proposes harness patches (human approve).",
      "Solo trio + Slack trainer — optional operator loops.",
    ],
    manualHref: "/manual#harness",
  },
  harnessRulesOverview: {
    title: "Harness visibility",
    description: "Live counts for skills, MCP tools, tech health, and supervisor feature flags.",
    options: [
      "Tech health — composite score from harness freshness checks.",
      "Pattern Router — supervisor lane picks agentic design patterns.",
      "Forced reflection — post-task learning loop gate.",
    ],
    manualHref: "/manual#harness",
  },
  harnessRulesMonitoring: {
    title: "Pattern monitoring",
    description: "Prometheus alert rules, Alertmanager routing, and 24h pattern success telemetry.",
    options: [
      "Slack webhook — routes critical pattern alerts.",
      "Top patterns grid — success rate per agentic pattern id.",
      "Grafana dashboard uid — linked from smoke script footer.",
    ],
    manualHref: "/manual#harness",
  },
  harnessRulesFiles: {
    title: "Layered harness files",
    description: "Root .cursorrules plus scoped .cursor/rules — lean global context for agents.",
    options: [
      "Scope — global vs path-scoped rule files.",
      "Bytes — file size for context budget planning.",
      "Edit in repo — changes sync on next deploy.",
    ],
    manualHref: "/manual#harness",
  },
  harnessRulesTools: {
    title: "MCP tool catalog",
    description: "Active connector tools discoverable by supervisor lanes and Queen prompts.",
    options: [
      "Count badge — total MCP tools in tenant snapshot.",
      "Grid — tool id, connector, and capability tags.",
      "Refresh harness snapshot after connector changes.",
    ],
    manualHref: "/manual#harness",
  },
  harnessRulesSkills: {
    title: "Skills & memory",
    description: "Active skill lattice plus tenant behavioral instructions for Queen prompts.",
    options: [
      "Skill lattice — markdown skills selected by SkillLibrary.",
      "Behavioral memory — injected as === BEHAVIORAL INSTRUCTIONS ===.",
      "Reference-mode skills — lazy-fetched on first use.",
    ],
    manualHref: "/manual#harness",
  },
  harnessRulesLoops: {
    title: "Operator loops",
    description: "Solo trio, Slack trainer, LSP bridge, rubrics, maintainer webhook, patterns, and Forager scan.",
    options: [
      "Solo trio — three-bee operator micro-swarm.",
      "Queen Maintainer — PR-only self-maintenance webhook.",
      "Intelligence scan — read-only harness patch proposals.",
    ],
    manualHref: "/manual#harness",
  },
  settingsLlmKeys: {
    title: "LLM & voice keys",
    description: "Tenant-scoped API keys for Grok, Claude, OpenAI, Deepgram, ElevenLabs — never logged or sent to LLM prompts raw.",
    options: [
      "Primary router — LiteLLM with fallback chain.",
      "Voice readiness gate — STT/TTS flags on deploy.",
      "Rotate keys quarterly — audit log records changes.",
    ],
    manualHref: "/manual#llm-keys",
  },
  settingsBilling: {
    title: "Billing & usage",
    description: "Plan limits, usage health, and tier feature matrix.",
    options: [
      "Soft limit — warnings before hard block.",
      "Plan comparison — feature flags per tier.",
      "Cost cockpit link — /settings/costs for LLM spend.",
    ],
    manualHref: "/manual#billing",
  },
  settingsSecurity: {
    title: "Security",
    description: "2FA, password change, session policy, and tenant security posture.",
    options: [
      "TOTP 2FA — required for admin actions when enabled.",
      "Hive password — change without email round-trip.",
      "Session policy — idle timeout and concurrent limits.",
    ],
    manualHref: "/manual#security",
  },
  settingsTeam: {
    title: "Team access",
    description: "Invite members, assign tenant roles, and manage pending invite tokens.",
    options: [
      "Roles — owner, admin, operator, viewer.",
      "Invites expire — re-send from pending list.",
      "RBAC — JWT carries role on every API call.",
    ],
    manualHref: "/manual#team",
  },
  settingsNotifications: {
    title: "Notifications",
    description: "Email, SMS, Slack, Telegram channels — Trust Autopilot uses these for verified-outcome pings only.",
    options: [
      "Channel cards — accordion tabs per provider.",
      "Test ping — simulate-first before live.",
      "Zero-UI — Telegram bot token configured here or Studio.",
    ],
    manualHref: "/manual#notifications",
  },
  settingsCapabilities: {
    title: "Capabilities atlas",
    description: "Platform feature matrix — what is live, beta, or simulate-only on this deployment.",
    options: [
      "Compose-only flags — never duplicate swarms.",
      "Competitive edge notes — why each capability exists.",
      "Admin platform tab — internal tenant overrides.",
    ],
    manualHref: "/manual#capabilities",
  },

  // —— Ballroom ——
  dumpSleep: {
    title: "Dump & Sleep",
    description: "Upload voice/text dump before overnight consolidation — feeds dreaming cycle and morning publish pipeline.",
    options: [
      "Pro+ feature — check usePlatform().hasFeature('dump_sleep').",
      "Transcript lands in Knowledge + ICM dialogue extract.",
      "Pair with Cockpit Start day for trio cycle.",
    ],
    manualHref: "/manual#dump-sleep",
  },

  // —— Tasks ——
  tasksQueue: {
    title: "Task queue",
    description: "Async mission queue backed by Celery — pending, running, blocked, and completed today lanes.",
    options: [
      "Sync — polls without blocking UI thread.",
      "New task — /tasks/new with simulate preview.",
      "Workflows tab — DAG view of factory chains.",
    ],
    manualHref: "/manual#tasks",
  },
  tasksRecent: {
    title: "Recent tasks",
    description: "Latest rows from /api/v1/tasks — quick status scan without opening full queue.",
    options: [
      "Shows last 6 rows by updated_at.",
      "Click through to task detail when available.",
      "Pair with queue section for full lanes.",
    ],
    manualHref: "/manual#tasks",
  },

  agentsWorkflows: {
    title: "Workflows",
    description: "DAG executions auto-decomposed from tasks — visualize factory chains and step completion status.",
    options: [
      "Each node — bee step with guardrails + evaluation criteria.",
      "Failed steps — blocked until simulate retry passes.",
      "Open from Tasks tab or Cockpit priority queue.",
    ],
    manualHref: "/manual#workflows",
  },
  swarmsWaggleFeed: {
    title: "Waggle dance feed",
    description: "Realtime cross-swarm signals from the hive tasks topic — handoffs between decentralized sub-hives.",
    options: [
      "Purple badge — live feed when WebSocket connected.",
      "Lane chips — source → destination swarm routing.",
      "Empty state — run a workflow or enqueue tasks first.",
    ],
    manualHref: "/manual#swarms",
  },
  integrationsSkills: {
    title: "Skills marketplace",
    description: "Browse premium skills or export verified SKILL.md bundles for GitHub and Gumroad.",
    options: [
      "Revenue factory — swarm → verify → export bundle.",
      "Premium unlock — external checkout lane when enabled.",
      "Skills attach to harness lattice after verify.",
    ],
    manualHref: "/manual#skills",
  },
  integrationsPlugins: {
    title: "Plugin catalog",
    description: "Built-in modules and operator uploads — inspect status and reload generation per plugin row.",
    options: [
      "User uploader — zip manifest with guardrails.",
      "Reload generation badge — hot-reload counter.",
      "Disabled plugins — hidden from bee tool router.",
    ],
    manualHref: "/manual#plugins",
  },

  teamInvite: {
    title: "Invite member",
    description: "Send an email invite with a tenant role — token expires if not accepted.",
    options: ["Roles — owner, admin, member, viewer, guest.", "Invite link — single-use token.", "Resend from pending list."],
    manualHref: "/manual#team",
  },
  teamMembers: {
    title: "Members",
    description: "Active tenant memberships — change role or remove access without deleting hive data.",
    options: ["Owner — full tenant control.", "Viewer — read-only cockpit.", "RBAC enforced on every API call."],
    manualHref: "/manual#team",
  },
  teamPendingInvites: {
    title: "Pending invites",
    description: "Outstanding invite tokens awaiting acceptance — revoke to invalidate link immediately.",
    options: ["Shows email + role + created date.", "Expired invites auto-hidden.", "No duplicate active invites per email."],
    manualHref: "/manual#team",
  },
  billingLimits: {
    title: "Soft/Hard limits",
    description: "Usage health against tier soft and hard caps — amber before block, red at hard stop.",
    options: ["Soft — warnings in Cockpit + email.", "Hard — new tasks/agents blocked.", "Upgrade link when Pro/Enterprise needed."],
    manualHref: "/manual#billing",
  },
  billingPlans: {
    title: "Plan comparison",
    description: "Tier limits and enabled features side-by-side — compose-only flags never duplicate swarms.",
    options: ["Free — 2 agents, 1 swarm.", "Pro — Swarm Builder templates + dump/sleep.", "Enterprise — white-label + compliance bundle."],
    manualHref: "/manual#billing",
  },
  tasksPerformanceTier: {
    title: "Performance by tier",
    description: "Share of agents in the hive by performance tier — API summary for pollen-weighted roster health.",
    options: ["Bar rows — relative share per tier.", "Pair with queue for live task depth.", "Refreshes on Tasks page load."],
    manualHref: "/manual#tasks",
  },
} as const satisfies Record<string, SectionHint>;

export type SectionHintKey = keyof typeof SECTION_HINTS;

export function sectionHintProps(key: SectionHintKey): SectionHint {
  return SECTION_HINTS[key];
}
