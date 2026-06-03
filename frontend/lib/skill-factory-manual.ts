/** Skill Factory operator manual — steps, hints, and recommendations (in-app Guide tab). */

import { MANUAL_HREFS } from "@/lib/manual-routes";

export interface SkillFactoryManualStep {
  id: string;
  phase: number;
  title: string;
  summary: string;
  hint: string;
  actions: string[];
  link?: { href: string; label: string };
  optional?: boolean;
}

export interface SkillFactoryPrerequisite {
  id: string;
  label: string;
  detail: string;
  href?: string;
}

export interface SkillFactoryRecommendation {
  id: string;
  title: string;
  body: string;
}

export interface SkillFactoryGapItem {
  id: string;
  label: string;
  status: "done" | "operator" | "planned";
  detail: string;
}

export const SKILL_FACTORY_PREREQUISITES: SkillFactoryPrerequisite[] = [
  {
    id: "llm-keys",
    label: "LLM keys configured",
    detail: "Settings → AI · LLM keys — at least one provider (Grok recommended). Factory sessions call researcher + coder + critic bees.",
    href: MANUAL_HREFS.settingsLlmKeys,
  },
  {
    id: "auto-approve",
    label: "Auto-approve ON (solo)",
    detail: "Agents → Sessions — enable auto-approve so factory sub-steps do not stall on every micro-approval.",
    href: MANUAL_HREFS.agentsSessions,
  },
  {
    id: "skill-factory-flag",
    label: "Skill Factory enabled",
    detail: "Feature flag skill_factory ON (solo default). Settings tab → Factory enabled.",
  },
  {
    id: "celery",
    label: "Celery worker healthy",
    detail: "Weekly research cron and async workflow runs need celery-worker + beat. Check /health/ready on deploy.",
  },
  {
    id: "hivemind",
    label: "HiveMind populated (recommended)",
    detail: "Run Foragers or Ingest URL so research scores real demand signals — empty HiveMind still works with default niches.",
    href: MANUAL_HREFS.foragers,
  },
];

export const SKILL_FACTORY_STEPS: SkillFactoryManualStep[] = [
  {
    id: "settings-seeds",
    phase: 1,
    title: "1. Nastav niche seeds (Settings)",
    summary: "Definuj 3–8 tém, kde chceš vyrábať skills — napr. newsletter automation, SEO blog pipeline, Cursor agent packs.",
    hint: "Prázdne seeds = 8 default niches (newsletter, SEO, crypto alerts…). Ulož policy po úprave.",
    actions: [
      "Apps & Tools → Skill Factory → Settings",
      "Pridaj niche seeds relevantné pre tvoj biznis",
      "Nastav max builds/week (cost guard, odporúčame 2–3)",
      "Save policy",
    ],
  },
  {
    id: "settings-auto",
    phase: 1,
    title: "1b. Auto-build (voliteľné)",
    summary: "Keď score ≥ threshold, systém sám spustí factory session — vhodné až keď máš overený flow.",
    hint: "Začni s auto-build OFF. Zapni až po prvom úspešnom manuálnom skille. Threshold 0.72 je dobrý štart.",
    actions: [
      "Auto-build OFF pre prvý mesiac",
      "Min score 0.72–0.78",
      "Research cron nechaj ON (pondelok ráno)",
    ],
    optional: true,
  },
  {
    id: "research-run",
    phase: 2,
    title: "2. Spusti Research",
    summary: "HiveMind + Skill Market Intel skóruje príležitosti podľa demand, competition a buildability.",
    hint: "Composite ≥72% = auto-build eligible. Rationale ukazuje HiveMind hits a intel signály. Dismiss slabé niche.",
    actions: [
      "Tab Research → Run research now",
      "Prečítaj rationale pri každej karte",
      "Porovnaj suggested price (€9 / €19 / €29 anchor)",
      "Dismiss niche mimo tvojej expertízy",
    ],
  },
  {
    id: "build-start",
    phase: 3,
    title: "3. Build skill",
    summary: "Spustí supervisor session s factory goal — researcher → coder → critic → simulate.",
    hint: "Jeden build = jedna session. Nespúšťaj 5 naraz — cost guard a kvalita klesajú.",
    actions: [
      "Klikni Build skill na vybranej príležitosti",
      "Presuň sa na Queue tab — status building",
      "Otvor Agents → Sessions a sleduj beh",
    ],
    link: { href: "/agents#sessions", label: "Agents → Sessions" },
  },
  {
    id: "monitor-session",
    phase: 4,
    title: "4. Sleduj factory session",
    summary: "Bees produkujú SKILL.md draft podľa skill-authoring-template. Critic musí APPROVE pred operátor review.",
    hint: "Info report ukáže resolved skills + pattern badges. Pri fail — nová session s upresneným goal, nie retry raw output.",
    actions: [
      "Sessions — nájdi goal obsahujúci „Skill Factory“ alebo niche",
      "Počkaj na status completed / needs_input",
      "Ak needs_input — doplň chýbajúci kontext v odpovedi",
    ],
    link: { href: "/agents#sessions", label: "Open Sessions" },
  },
  {
    id: "approve-forge",
    phase: 5,
    title: "5. Schváľ verified_skill_forge",
    summary: "Po verify critic navrhne forge proposal — approve uloží skill do tenant registry + Recipe Library.",
    hint: "Bez approve sa skill neobjaví v Library ani v skill pickeri. Reject ak SKILL.md nie je production-ready.",
    actions: [
      "Agents → Suggestions (alebo Execution Studio codebase lane)",
      "Nájdi proposal_type verified_skill_forge",
      "Approve — tenant skill + recipe sa vytvoria automaticky",
    ],
    link: { href: "/agents", label: "Agents → Suggestions" },
  },
  {
    id: "library-export",
    phase: 6,
    title: "6. Export GitHub pack",
    summary: "Stiahni bundle: SKILL.md + README.md + LISTING.md + meta.json — pripravené na repo alebo Gumroad.",
    hint: "LISTING.md je copy pre predajný listing. GitHub push je manuálny (zatiaľ bez auto-PR).",
    actions: [
      "Tab Library → Download GitHub pack",
      "Rozbaľ zip, skontroluj SKILL.md",
      "Push do public/private repo podľa stratégie",
    ],
  },
  {
    id: "use-runtime",
    phase: 7,
    title: "7. Použi skill v hive",
    summary: "Tenant skills sa mergujú do SkillLibrary — agenti ich vidia automaticky alebo cez explicit picker.",
    hint: "Prázdny picker = auto match z goal. Pripni factory slug keď chceš vynútiť konkrétny skill.",
    actions: [
      "Agents → Sessions — Skills override chips pod goal",
      "Mission Kanban — chips pri triage/dispatch",
      "Tasks → New task — chips pri operator intake",
    ],
    link: { href: MANUAL_HREFS.agentsSessions, label: "Sessions skill picker" },
  },
  {
    id: "external-sales",
    phase: 8,
    title: "8. Predaj mimo apky (voliteľné)",
    summary: "Apka nepredáva — export ide na GitHub (open/free) alebo Gumroad (€9–49). Marketing je na tebe.",
    hint: "Primary ROI = interné skills pre rýchlejší hive. Externý predaj = cherry-pick top 1–2 / mesiac.",
    actions: [
      "GitHub — README + topics (cursor-skill, agent-skill)",
      "Gumroad — LISTING.md ako popis produktu",
      "Nepoužívaj in-app marketplace (vypnutý zámerne)",
    ],
    optional: true,
  },
];

export const SKILL_FACTORY_RECOMMENDATIONS: SkillFactoryRecommendation[] = [
  {
    id: "internal-first",
    title: "Interné skills pred predajom",
    body: "Najväčšia hodnota je okamžitá — factory skill, ktorý používaš v Agents sessions denne. Externý predaj až keď skill prešiel 3+ úspešnými behmi.",
  },
  {
    id: "niche-specific",
    title: "Konkrétna niche, nie generic",
    body: "„Cursor agent skill“ je preplnené. Vyhrávajú: „Newsletter growth loop pre indie SaaS“, „SEO brief pipeline s simulate-first verify“.",
  },
  {
    id: "verify-always",
    title: "Nikdy raw output operátorovi",
    body: "Schváľ len forge po critic APPROVE + simulate. Raw LLM SKILL.md bez verify patrí do draftu, nie do Library.",
  },
  {
    id: "one-at-a-time",
    title: "Jeden build naraz",
    body: "max_builds_per_week = 2–3. Kvalita researcher→coder→critic chain klesá pri paralelných factory runoch.",
  },
  {
    id: "feed-hivemind",
    title: "Krm HiveMind pred research",
    body: "Foragers + Ingest URL zvyšujú Skill Market Intel scores. Prázdny HiveMind = len default niche heuristika.",
  },
  {
    id: "no-marketplace",
    title: "Žiadny in-app checkout",
    body: "UGC marketplace a premium checkout sú vypnuté zámerne. Predaj = GitHub/Gumroad s export bundle.",
  },
];

export const SKILL_FACTORY_GAPS: SkillFactoryGapItem[] = [
  {
    id: "core-pipeline",
    label: "Research → build → forge → library → export",
    status: "done",
    detail: "Backend + UI nasadené na prod.",
  },
  {
    id: "skill-picker",
    label: "Skill picker (Sessions, Kanban, New task)",
    status: "done",
    detail: "Multi-select chips + execution_payload.skills.",
  },
  {
    id: "first-skill",
    label: "Prvý overený tenant skill v Library",
    status: "operator",
    detail: "Spusti Build → approve forge — library je zatiaľ prázdna kým neurobíš prvý celý cyklus.",
  },
  {
    id: "live-scrapers",
    label: "Live GitHub/Gumroad scrapers",
    status: "planned",
    detail: "Research používa HiveMind + Skill Market Intel, nie priame scrapovanie trhov.",
  },
  {
    id: "github-auto-push",
    label: "Auto GitHub PR / push",
    status: "planned",
    detail: "Dnes: Download GitHub pack → manuálny push. GitHub connector môže PR v budúcnosti.",
  },
  {
    id: "gumroad-api",
    label: "Gumroad API listing",
    status: "planned",
    detail: "LISTING.md pripravený — upload manuálne na gumroad.com.",
  },
  {
    id: "llm-cost",
    label: "LLM budget pre factory runs",
    status: "operator",
    detail: "Over Settings → costs a LLM keys pred bulk auto-build.",
  },
  {
    id: "forager-tags",
    label: "Forager tag skill-opportunity",
    status: "operator",
    detail: "Voliteľne taguj HiveMind ingest skill-opportunity pre lepšie research scores.",
  },
];

export const SKILL_FACTORY_MANUAL_DOC = "docs/SKILL_FACTORY_OPERATOR_MANUAL.md";
