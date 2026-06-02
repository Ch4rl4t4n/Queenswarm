/** One-click skill bundles for Mission Kanban triage (Hermes-style packs). */

export interface MissionKanbanBundle {
  id: string;
  label: string;
  hint: string;
  taskText: string;
  autoDispatch: boolean;
}

export const MISSION_KANBAN_BUNDLES: MissionKanbanBundle[] = [
  {
    id: "content-week",
    label: "Content week",
    hint: "Blog + social + publish queue",
    autoDispatch: true,
    taskText: `Launch a full content week for queenswarm.love (simulate-first, English UI copy).

Deliverables:
1. Research 5 SEO blog topics aligned with AI agent swarms
2. Draft 3 blog posts (markdown, H2/H3 structure)
3. Write 1 Twitter/X thread + 2 LinkedIn posts
4. Prepare publish pack JSON for Execution Studio (simulate_only=true)

Parallel swarm: scout research, writer bees, critic verify each piece before done.`,
  },
  {
    id: "landing-page",
    label: "Landing page",
    hint: "Hero, sections, CTA, mobile-first",
    autoDispatch: true,
    taskText: `Build a landing page pack for queenswarm.love (verify-first, no live deploy).

Deliverables:
1. Competitor scan (3 agentic OS / swarm tools)
2. Hero headline + subhead + 3 value props
3. Section outline (features, how it works, pricing teaser)
4. CTA copy + meta title/description for SEO
5. Markdown wireframe the dev team can implement

Simulate only. Critic APPROVE before operator review.`,
  },
  {
    id: "competitor-research",
    label: "Research sprint",
    hint: "Competitors + gaps + recommendations",
    autoDispatch: true,
    taskText: `Competitor research sprint for AI agent orchestration platforms.

Deliverables:
1. Top 5 competitors — product, pricing signal, positioning
2. Gap analysis vs Queenswarm bee-hive model
3. 5 actionable recommendations ranked by impact
4. Executive summary (max 400 words, English)

Public sources only. Verify before delivery.`,
  },
  {
    id: "lead-gen-lane",
    label: "Lead Gen Lane",
    hint: "ICP → scout ≤10 → outreach simulate",
    autoDispatch: true,
    taskText: `Lead Gen Lane for Queenswarm (Verified recipe LEAD_GEN_LANE, simulate-first).

ICP — fill before dispatch:
- Industry: B2B SaaS / e-commerce (pick one)
- Size: 10–200 employees
- Region: EU / SK / CZ
- Signal: recent hiring, funding, or stack change

Deliverables:
1. ICP summary from curated memory + Wiki forager-insights
2. Lead Scout — max 10 qualified leads from HiveMind (never invent emails)
3. Optional: 3 public competitor intel bullets
4. Outreach Draft — max 5 personalised messages (subject + body + CTA, Gmail simulate_only)
5. Critic APPROVE + operator report (max 400 words)

No live send. Tag outreach-result in HiveMind.`,
  },
  {
    id: "marketing-campaign",
    label: "Campaign brief",
    hint: "Audience, channels, 2-week calendar",
    autoDispatch: false,
    taskText: `Marketing campaign brief for Queenswarm (simulate-first).

Deliverables:
1. Audience + positioning (1 paragraph each)
2. Channel plan (3 channels max)
3. Content calendar skeleton (2 weeks)
4. Draft publish pack JSON for simulate queue

Park in Triage for review before dispatch.`,
  },
];
