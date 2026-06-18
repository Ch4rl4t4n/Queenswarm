# Roadmap excellence recommendations

Updated: 2026-06-11 (Track Q — Mission Home & Guided UX)

Canonical rationale for **P10 — Excellence & competitive moat** in [`ROADMAP.md`](ROADMAP.md).

Use this doc when evaluating external posts (X threads, YouTube, competitor launches). Each signal maps to a track below.

## Processed signals log

| Date | Source | Track | Roadmap IDs |
|------|--------|-------|-------------|
| Jun 2026 | [Rahul — AI agents 2026](https://x.com/sairahul1/status/2064988918630736353) | A | AL1–AL4 |
| Jun 2026 | [Pikachin — Data Goldmine Engine](https://x.com/pikach_in/status/2064450336589242818) | I | DG1–DG8 |
| Jun 2026 | Obsidian / second-brain (CyrilXBT thread) | B | SB1 ✅, SB2–SB4 |
| Jun 2026 | [Simon Scrapes — Memory beats Hermes](https://www.youtube.com/watch?v=H9BUkgDf5Y4) | J | MEM1–MEM5 |
| Jun 2026 | [Greg Isenberg — Agent loop hype vs closed loops](https://www.youtube.com/watch?v=7clJ8IH784Q) | K | LOOP1–LOOP5 |
| Jun 2026 | [OpenAI — Codex for data science](https://www.youtube.com/watch?v=Lvk_VZOppIY) | L | DA1–DA12 |
| Jun 2026 | [David Ondrej — Unsloth Studio local fine-tune](https://www.youtube.com/watch?v=BFH9D05UFvM) | M | LOC1–LOC14 |
| Jun 2026 | Operator batch — 18× YouTube + [Riverflow](https://x.com/riverflow_ai) | N | NP1–NP8 |
| Jun 2026 | [CyrilXBT — Obsidian trading journal](https://x.com/cyrilXBT/status/2064928168105136433) | O | TJ1–TJ7 |
| Jun 2026 | [Ryan Doser — Robinhood AI agent MCP](https://www.youtube.com/watch?v=w4QrQdulH0g) | P | RA1–RA5 |
| Jun 2026 | [Julian Goldie — Hermes Agent OS Mission Control](https://www.youtube.com/watch?v=egeUmkhdcM4) | Q | UX0–UX10 |
| Jun 2026 | X batch — Jarvis/Obsidian · Boris loops · NotebookLM analyst · weak signals · research project | H | POS-H1–H7 |
| Jun 2026 | [CyrilXBT — Personal AI infra smarter every week](https://x.com/cyrilXBT/status/2065618897089253592) · Gabriel Chua email loop · Eliana faceless cut | J | POS-J1–J5 |

_Next link from operator → run [Evaluation template](#evaluation-template-for-new-links) → add row here + item to [`ROADMAP.md`](ROADMAP.md) P10 if 🔴 gap._

## Evaluation template (for new links)

When the operator sends a link or idea, score Queenswarm vs signal:

| Dimension | Question | Our moat |
|-----------|----------|----------|
| **Goal** | Does it decompose goals or one-shot prompts? | Supervisor session, Mission Kanban, CBO |
| **Think** | Visible planning / reflection / critic? | Pattern Router, meta-reasoning, self-healing |
| **Tools** | Real MCP/tool loop or text-only? | MCP hub, Forager, dynamic install |
| **Verify** | Simulate before user sees output? | Simulation gate, critic, pollen |
| **Memory** | Persistent context across days? | Hive Mind, Obsidian, episodic, Brain Pack |
| **Learn** | Improves from outcomes? | Recipes, imitation, Skill Factory |
| **Trust** | Operator approve on money/publish? | HITL, publish queue, trading preflight |
| **Sell** | Can we productize it? | letagentscook.org + Gumroad |

**Verdict buckets:** ✅ ahead · 🟡 parity (UX gap) · 🔴 gap (roadmap item) · ⛔ skip (anti-pattern: central SPOF, no verify, hype-only)

---

## Track A — Agent loop transparency

**Signal:** [Rahul — How To Build AI Agents in 2026](https://x.com/sairahul1/status/2064988918630736353) — Goal → Think → Use Tools (not Prompt → Answer).

**Gap:** Architecture is agentic; **product story** still feels like a power-user harness. Event log exists but is not the primary narrative.

| ID | Item | Why |
|----|------|-----|
| AL1 | **Agent Loop Timeline** — session UI: Goal → Plan → Tool → Verify steps | Makes “real agent” obvious to operator and Gumroad buyers |
| AL2 | **Tool Outcome Panel** at `needs_input` / approve | Evidence before live publish/trade |
| AL3 | **Goal progress strip** on Mission Kanban lineage | Links kanban visibility to execution engine |
| AL4 | **Pattern + tool explainer** chip per session step | “Why this tool” without reading raw JSON events |

---

## Track B — Second brain & wiki layer

**Signal:** Obsidian / second-brain threads (capture → connect → reuse).

**Shipped (Jun 2026):** `second_brain_capture.py`, Wiki Layer capture panel, MOC + connection intelligence pages.

| ID | Item | Why |
|----|------|-----|
| SB1 | Second-brain structured capture API + UI | ✅ Shipped |
| SB2 | Weekly **connection-intelligence** Celery tick | Keeps MOC fresh without manual Gardener |
| SB3 | Capture → approve → auto wikilink in vault export | Closes loop from idea to Obsidian |
| SB4 | Wiki-layer hits in ⌘K mission search | Recall at point of dispatch |

---

## Track C — Revenue & buyer proof

**Signal:** Indie hacker + “verified before buy” positioning (letagentscook.org).

| ID | Item | Why |
|----|------|-----|
| MK6 | 50+ scorecard-clean listings | Catalog depth — see `MARKETING_LETAGENTSCOOK_ROADMAP.md` |
| MK7 | Gumroad URL sync + purchase webhook unlock | Closes buy → use loop |
| REV1 | Post-purchase onboarding email + simulate proof PDF | Reduces refund / “doesn’t work” support |
| REV2 | Public **Eval-as-a-Service** on `/skills/eval` | Lead magnet; proves simulate-first |
| REV3 | Listing **scorecard badge** component on every product page | Marketing = product truth |

---

## Track D — Operator trust & factory SLOs

**Signal:** Operator fatigue when queues stall or outputs look “chatbotty”.

| ID | Item | Why |
|----|------|-----|
| TR1 | **Injection guard coverage** dashboard (checkpoint hits by tool) | OW15–17 hardening made visible |
| TR2 | **Simulation pass rate** trend in CBO snapshot | Single KPI for harness health |
| TR3 | **Rubric score** in session report before approve | Subjective quality (copy/design) |
| TR4 | **Skill Factory queue SLO** panel (awaiting_forge, critic rate, weekly cap) | Prevents repeat of Jun 2026 queue incident |

---

## Track E — Long-running & durable sessions

**Signal:** Anthropic long-running agents, Ralph loop, checkpoints.

**Backend largely shipped** — gap is operator-facing resume/progress.

| ID | Item | Why |
|----|------|-----|
| LR1 | **Checkpoint resume** CTA on session row (not buried in harness) | Durable sessions usable daily |
| LR2 | **Progress %** on Mission Kanban lineage from durable steps | Multi-day projects visible |
| LR3 | Worker crash → auto-resume + mission feed notify | Reliability without silent failure |

---

## Track F — Product depth (P7 carry-forward)

Items referenced in P7 but not yet shipped as UX.

| ID | Item | Why |
|----|------|-----|
| FP1 | **Recipe cosine matching UI** on dispatch | “Use what worked before” one click |
| FP2 | **Rapid loop dashboard widget** on solo home | 60s loop visibility |
| FP3 | **Sub-swarm local hive mind UI** | Bee-hive philosophy made tangible |
| FP4 | **Commercial tier self-serve** (billing + limits) | Scale beyond solo operator |

---

## Track G — Competitive signal pipeline

For operator-fed links (next step in conversation).

| ID | Item | Why |
|----|------|-----|
| SIG1 | **Competitive triage** runbook — link → template → roadmap delta | This doc + operator paste workflow |
| SIG2 | Social Intel → **quarterly roadmap refresh** ticket (Tech SCV lane) | Automated weak signal → human prioritize |
| SIG3 | **Capabilities Atlas diff** — auto-highlight 🟡 rows after synthesis | Single pane for “what changed externally” |

---

## Track H — Platform & ops (unchanged)

See ROADMAP **P3** — HA drill, DR restore, secret rotation, Grafana review. Quarterly, not feature work.

---

## Track I — Data goldmine engine (Pikachin / Claude Code pattern)

**Signal:** [Pikachin — Claude Code as Data Goldmine Engine](https://x.com/pikach_in/status/2064450336589242818) — turn **raw public data** into structured, repeatable intelligence (not one-shot chat). Typical stack in the wild: discover → scrape on schedule → LLM enrich → store → alert on delta → learn from feedback → monetize.

**Queenswarm today:** Foragers (RSS/YouTube/X) · Social Intel delta cursors · HiveMind embed · `competitor-scrape-analyze` · Tavily/Serper/Apify · promote digest → Mission Kanban → session · Skill Factory from market intel.

**Gap:** Pipeline exists in pieces; operator must wire foragers manually. Missing **monitor-anything wizard**, **change alerts**, **structured row export**, and **feedback-tuned filters**.

| ID | Item | Why |
|----|------|-----|
| DG1 | **Data Monitor wizard** — „track jobs/prices/listings/news“ → auto forager + schema | One sentence → scheduled goldmine (Pikachin UX) |
| DG2 | **Structured extract templates** — jobs, prices, events, repos, listings JSON schema | Enrichment layer, not raw text blobs |
| DG3 | **Delta alert inbox** — „new since last run“ matching operator rules | Actionable signal, not only HiveMind bury |
| DG4 | **Forager feedback loop** — 👍/👎 on hits → filter_config tuning | Community data-scraper-agent pattern |
| DG5 | **Export lane** — approved rows → Notion DB / Google Sheet / CSV vault | Work output where operator already lives |
| DG6 | **Discovery-first scrape** — Serper/Tavily finds URLs, then forager binds | No hand-curated URL lists |
| DG7 | **Goldmine → dispatch** — alert row → one-click Mission Kanban + skill bundle | Closes intel → work loop |
| DG8 | **Goldmine → product** — recurring niche monitor → Skill Factory / content pack seed | Revenue from same data pipe |

**Verdict vs Pikachin:** 🟡 **parity on harness**, 🔴 **gap on operator UX + alerts + structured export**. We are **ahead** on verify/simulate, Hive Mind graph, and sellable recipes.

---

## Track J — Memory excellence (Simon Scrapes / Hermes stack)

**Signal:** [I Built The Best Claude Memory System (Beats Hermes)](https://www.youtube.com/watch?v=H9BUkgDf5Y4) — three jobs: **storage**, **injection**, **recall**. Cherry-picks MemSearch (auto summarized capture), Hermes (capped frozen injection ~1.3k tokens), GBrain (rerank + cited answer + „I don't know“).

**Queenswarm today:** Brain Pack · selective recall · hybrid mission search (OW21) · Hive Mind graph · episodic API · verify-first morning brief.

**Gap:** No auto capture every turn; recall returns chunks not cited prose; injection budget not visible; client/project scoping not first-class.

| ID | Item | Why |
|----|------|-----|
| MEM1 | Auto episodic capture → daily summarized log | MemSearch storage — nothing leaky |
| MEM2 | Cited recall panel + „not in memory“ | GBrain recall UX |
| MEM3 | Tier-0 injection strip before deep search | Hermes frozen snapshot visibility |
| MEM4 | Token budget meter on Brain Pack | Hermes ~1300 cap surfaced |
| MEM5 | Client/project tags + recall filter | GBrain company brain slice |

**Do not:** clone full MemSearch/Hermes/GBrain into Claude Code — extend Hive Mind + verify.

**Verdict:** Architecture ✅ ahead · Recall/injection UX 🔴.

---

## Track K — Closed agent loops (Greg Isenberg / Rasmic)

**Signal:** [WTF Is an AI Agent Loop?](https://www.youtube.com/watch?v=7clJ8IH784Q) — **HITL is the best loop today**; wide-open `/goal` loops = token slop unless unlimited budget; **closed loops** with fixed feedback (Greptile 4/5 score, max 5 turns) work for code review, SEO bulk, binary tasks.

**Queenswarm today:** simulate-first · critic · self-healing · Queen Maintainer PR-only · CostGovernor · `needs_input`.

| ID | Item | Why |
|----|------|-----|
| LOOP1 | Closed Review Loop skill (score → fix → re-run) | „Grep loop“ / Greptile daily win |
| LOOP2 | Loop guardrails panel (max turns, min score, cost cap) | Video token-burn warning |
| LOOP3 | Agent Loop Timeline | Same as **AL1** — one build |
| LOOP4 | Mid-flight checkpoint UX | Missing „road trip stop“ for builders |
| LOOP5 | Closed-loop presets (Factory · social intel · SEO bulk) | Ship scored loops without new harness |

**⛔ Anti-patterns:** whole-product `/goal` without operator · loop without rubric · >1k LOC single slice.

**Verdict:** Philosophy ✅ aligned · Productize closed loops 🔴.

---

## Track L — Business Data Analytics OS (OpenAI Codex pattern)

**Signal:** [Codex for data science](https://www.youtube.com/watch?v=Lvk_VZOppIY) — plugin with skills + data sources; agentic analyst; editable report; lineage; Slides export.

**Queenswarm approach:** **Supervisor session template** (5 bees max) + **Apps & Tools** module — **not** a new persistent swarm colony.

**Canonical doc:** [`BUSINESS_DATA_ANALYTICS_OS.md`](BUSINESS_DATA_ANALYTICS_OS.md)

| ID | Item | Why |
|----|------|-----|
| DA1 | Template `business-analytics-report` | One-click Codex-like team in one session |
| DA2 | Skill `business-analytics-playbook` | Guardrails + connector workflow |
| DA3 | Analytics Workspace module | `/apps-tools/analytics` home |
| DA4 | Business Question wizard | Question → dispatch (operator entry) |
| DA5 | Live report artifact panel | Edit report like Codex artifact |
| DA6 | Data lineage strip | Transparency — which query powered which chart |
| DA7 | Connector profile GA4/Sheets/warehouse | Multi-source like Databricks demo |
| DA8 | Export Notion + Slides simulate | Leadership templates · HITL |
| DA9 | Weekly analytics routine | Recurring deck without manual setup |
| DA10 | Report critic closed loop | LOOP5 · ≥4/5 before export |
| DA11 | Snapshot API | Perf guardrail — one BE read |
| DA12 | E2E + operator manual | Ship proof |

**Verdict:** Connectors + verify ✅ ahead · Unified analytics workspace UX 🔴.

---

## Track M — Local Sovereign LLM OS (Unsloth / air-gap)

**Signal:** [Unsloth Studio — fine-tune locally](https://www.youtube.com/watch?v=BFH9D05UFvM) — QLoRA · PDF recipes · GGUF/Ollama · local chat; video also shows optional OpenRouter teacher for datasets (we gate that behind HITL).

**Queenswarm approach:** Extend **LiteLLM router** — do **not** rebuild harness. **Swarm/session unchanged**; bees call local Ollama when `local_sovereign` mode active.

| ID | Item | Why |
|----|------|-----|
| LOC1 | Ollama/vLLM in LiteLLM | Local inference path |
| LOC2 | `local_sovereign` + `LLM_AIRGAP` | Zero external LLM |
| LOC3 | Docker `local-llm` profile | PC + server deploy |
| LOC4 | Local Inference settings UI | Operator control |
| LOC5 | Verified JSONL export | Dataset from critic-approved outputs |
| LOC6 | Dataset Recipe wizard (local only) | PDF→Q&A without cloud default |
| LOC7 | Unsloth bridge script | Import GGUF/LoRA to Ollama |
| LOC8 | Adapter registry | Tenant custom models |
| LOC9 | GPU fine-tune queue | Optional training lane |
| LOC10 | Hardware preflight | Right-size models |
| LOC11 | $0 local cost metrics | CostGovernor |
| LOC12 | E2E air-gap smoke | Proof |
| LOC13 | DA + local mode | Analytics offline |
| LOC14 | Recipe `local-adapter` tags | Reuse proven flows |

**Verdict vs video:** Fine-tune UX 🔴 gap · Harness + verify ✅ ahead · **No second app** — sovereign mode inside queenswarm.

---

## Track N — Operator vertical packs (Moneta · Marketing · Trading)

**Signals:** Jun 2026 operator batch — full triage in [`OPERATOR_VERTICAL_PACKS.md`](OPERATOR_VERTICAL_PACKS.md).

| Video / link | Takeaway | Verdict |
|--------------|----------|---------|
| [grill-me](https://www.youtube.com/watch?v=c0kaKxM2pHg) | Interview → knowledge doc | 🟡 skill ✅ · wizard 🔴 **NP1** |
| [brand context](https://www.youtube.com/watch?v=yh_fZZVbNwc) | Injectable brand files | 🟡 **NP3** |
| [Riverflow](https://x.com/riverflow_ai) | Operator-controlled scoring rubric | 🟡 **NP2** — not image API |
| [Koah probabilities](https://www.youtube.com/watch?v=SC4hr_U8298) | Thesis before bet | 🟡 **NP5** |
| [Listen Labs](https://www.youtube.com/watch?v=Rumft-rsEu4) | AI customer interviews at scale | ⛔ platform · **NP1** internal only |
| [Hermes+Ollama](https://www.youtube.com/watch?v=yaMcm3sQswc) | Private OS | ✅ **LOC** |
| [Jerry Liu context](https://www.youtube.com/watch?v=PJ-3hXAUotI) | Document layer | ✅ Hive Mind + **DA** |
| [40 PRs/day](https://www.youtube.com/watch?v=88B6DimMD2g) | Parallel agents + review | ✅ **LOOP1** · ⛔ Treehouse |
| [Pi agent](https://www.youtube.com/watch?v=FJxgz5pN4wU) | Minimal hooks harness | ⛔ skip |
| [Rasmic plan mode](https://www.youtube.com/watch?v=MyRs5hdE7vo) | Closed loops | ✅ **Track K** |
| [Austin Marchese](https://www.youtube.com/watch?v=faPA8odcjpY) | Build right thing first | 🟡 **NP4** brief |
| Remaining (Ng app, Karpathy, Marina skills, tier lists, Pietro agents) | Generic / commentary | ⛔ or use today |

| ID | Item | Why |
|----|------|-----|
| NP1 | Stakeholder Grill wizard | Moneta PM + internal validation without Listen Labs |
| NP2 | Creative rubric presets | Riverflow-style score before publish |
| NP3 | Brand Context Pack | External marketing consistency |
| NP4 | Investment brief template | Daily PO artifact — anonymized |
| NP5 | Trading thesis brief | Koah calibrated-belief gate |
| NP6 | Campaign launch wizard | One chain: brand → rubric → simulate |
| NP7 | AOS1 `investments` profile | One-click Moneta mode |
| NP8 | Video URL batch brief | Operator intel from link dumps |

**Verdict vs batch:** Harness architecture ✅ ahead · **Vertical wizards** 🔴 · Full third-party platforms ⛔.

---

## Track P — Broker Agent Lane (Ryan Doser / Robinhood MCP)

**Signal:** [Robinhood AI trading agent with Claude](https://www.youtube.com/watch?v=w4QrQdulH0g) — MCP endpoint · OAuth Agentic account · NL portfolio/orders · guardrails before live ([Robinhood overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)).

| Video step | Queenswarm today | Minmax add (Track P) |
|------------|------------------|----------------------|
| Add Robinhood MCP URL | Dynamic Connector Hub ✅ | **RA1** preset + wizard |
| OAuth + Agentic account | Manual outside app | **RA2** Cockpit tab (status + steps) |
| NL trade in Claude | Supervisor + tools ✅ | **RA4** read-only session first |
| No guardrails in hype demos | `real-money-risk-gate` ✅ | **RA3** unified caps UI |
| Instant live orders | HITL publish/trade ✅ | **RA5** order approve queue |

| ID | Item | Why minmax |
|----|------|------------|
| RA3 | Broker guardrails pack | One settings block for all venues |
| RA4 | Read-only broker session | Same as video “confirm connection first” |
| RA5 | HITL order queue | Our moat vs raw MCP — mandatory |
| RA1 | Robinhood MCP preset | Config only — no custom Robinhood SDK |
| RA2 | Broker MCP Cockpit tab | Small UI — no new Apps module |

**⛔ Skip:** autonomous 24/7 loop · second Claude harness.

**Verdict:** Polymarket path ✅ ahead · Robinhood MCP 🟡 · HITL broker UX 🔴.

---

## Track Q — Mission Home & Guided Operator UX (Hermes clarity)

**Signal:** [Claude Agent OS Is INSANE](https://www.youtube.com/watch?v=egeUmkhdcM4) — single Mission Control · Kanban + memory + agents · 5-min first win ([Hermes OS pattern](https://aiprofitboardroom.com/blog/hermes-agent-os/)).

**2026 UX research applied:** progressive disclosure · process-first IA · mobile 3–5 card home · 8px grid · 44px touch · contextual microcopy ([SaaS dashboard guide 2026](https://f1studioz.com/blog/smart-saas-dashboard-design/) · [progressive disclosure](https://www.sanjaydey.com/ui-ux-design-trends-2026/)).

**Canonical doc:** [`OPERATOR_MISSION_HOME_UX.md`](OPERATOR_MISSION_HOME_UX.md)

**Process rail:** `Setup → Plan → Work → Verify → Learn → Done`

| ID | Item | Why |
|----|------|-----|
| UX0 | UX research lock | Task flows before pixels |
| UX1 | Process Rail | Every user knows “where am I” |
| UX2 | Mission Home snapshot | Hermes single home · our verify moat |
| UX3 | First-run capability story | First visit = instant “what this app does” |
| UX4 | Progressive solo nav | 4 daily links · rest Advanced |
| UX5 | Memory strip | Hermes SOUL/MEMORY/USER visible |
| UX6 | Responsive + spacing | Mobile/tablet/desktop rules · no desktop regress |
| UX7 | Process-linked studios | Factory/Trading from rail step |
| UX8 | Route microcopy | One-line purpose per route |
| UX9 | E2E first-run 3 viewports | CI proof |
| UX10 | Session progress on Home | Same as AL1 |

**⛔ Skip:** Rebuild Hermes · remove verify · desktop shell changes.

**Verdict:** Product depth ✅ · Guided process UX 🔴 · Hermes shell worth copying selectively.

---

## Recommended execution order

1. **UX clarity:** **UX0 → UX1 → UX2 → UX3 → UX6** (Mission Home + Process Rail + responsive)  
2. **Cash:** MK6 → MK7 → REV1–3  
3. **Sovereign MVP:** **LOC1 → LOC4 + LOC11–12**  
4. **Vertical MVP:** **NP7 → NP4 → NP1**  
5. **Trust:** TR4 + LOOP2 + AL1/UX10 + AL2  
6. **Analytics:** DA1 → DA4 + DA11  
7. **Studios:** NP2–3/6 · RA3–5 · TJ4+  
8. **Work intel / depth:** DG · MEM · SB · FP · SIG  

All items: simulate-first, feature flag until gate green — [`FEATURE_IMPLEMENTATION_GUARDRAILS.md`](FEATURE_IMPLEMENTATION_GUARDRAILS.md).
