export interface ManualSection {
  id: string;
  title: string;
  paragraphs: string[];
  checklist?: string[];
}

export interface FunctionInfoItem {
  id: string;
  label: string;
  description: string;
  options: string[];
}

export interface FunctionInfoGroup {
  id: string;
  title: string;
  items: FunctionInfoItem[];
}

export const APP_MANUAL_SECTIONS: ManualSection[] = [
  {
    id: "quick-start",
    title: "1. Quick Start",
    paragraphs: [
      "Po prihlásení začni v {HOME_LABEL}, skontroluj stav aplikácie a až potom spúšťaj nové sessions.",
      "Prvý Supervisor flow štandardne spúšťaj cez Agents a viaž ho na konkrétny cieľ, obmedzenia a jasný výsledok.",
    ],
    checklist: [
      "Prihlás sa cez /login a potvrď, že si na {HOME_ROUTE}.",
      "Otvor Agents a spusti prvú Supervisor session s jedným cieľom.",
      "V Tasks založ súvisiaci task, aby bol výsledok trackovaný.",
      "V Knowledge over existujúce výstupy (retrieval-first).",
      "Ak ide o incident, otvor Ballroom a koordinuj rozhodnutia realtime.",
    ],
  },
  {
    id: "main-sections",
    title: "2. Hlavné sekcie",
    paragraphs: [
      "{HOME_LABEL} je command center, Agents riadi Supervisor a sessions, Tasks pokrýva execution/routines, Knowledge drží kontext a výstupy, Integrations spravuje konektory a Ballroom je realtime operačný kanál.",
      "Foragers sekcia slúži na správu dátových zberačov (YouTube/RSS/API), ich periodicitu, ingest do HiveMind a spawn agentov z forager konfigurácie.",
      "Settings obsahuje bezpečnostné, tímové, billing a integračné nastavenia pre tenant.",
    ],
  },
  {
    id: "best-practices",
    title: "3. Najlepšie praktiky",
    paragraphs: [
      "Prompty píš v tvare Goal → Context → Constraints → Done.",
      "Najprv hľadaj v Knowledge, potom spúšťaj nový výpočet. Ušetríš tokeny aj čas.",
      "Používaj routines iba pre opakované procesy a začínaj konzervatívnou frekvenciou.",
    ],
  },
  {
    id: "scenarios",
    title: "4. Bežné scenáre",
    paragraphs: [
      "Ranný check: {HOME_LABEL} → Agents needs_input → Tasks priority → Integrations stav → Knowledge posledné outputs.",
      "Produkčný incident: potvrď symptóm, spusti Supervisor session, koordinuj v Ballroom, záver zapíš do Knowledge.",
    ],
  },
  {
    id: "troubleshooting",
    title: "5. Troubleshooting",
    paragraphs: [
      "Redirect na login často znamená expirovanú session cookie alebo chýbajúci auth token.",
      "401 je autentifikácia, 403 je RBAC/permission guard, 404 býva route/proxy drift.",
      "Pri routine failoch najprv over active flag, interval, worker/beat zdravie a posledný error detail.",
    ],
  },
  {
    id: "four-lanes",
    title: "7. Four Lanes (solo operator)",
    paragraphs: [
      "SK: Štyri paralelné misie nahradzujú Virtual Company chaos: Najman marketing, Tech SCV, E-shop research, Automation factory.",
      "EN: Four parallel missions replace Virtual Company sprawl: Najman marketing, Tech SCV, E-shop research, Automation factory.",
      "SK: Otvor Agentic OS → Lanes, raz spusti Bootstrap lanes (pozastaví legacy rutiny), potom denne len Approve digestov.",
      "EN: Open Agentic OS → Lanes, run Bootstrap lanes once (pauses legacy routines), then daily Approve digests only.",
    ],
    checklist: [
      "SK: Lane A — Po/St/Pi marketing digest + competitor forager → Agents → Approve.",
      "EN: Lane A — Mon/Wed/Fri marketing digest + competitor forager → Agents → Approve.",
      "SK: Lane B — denne Tech SCV → Innovation Lab → Implement → GitHub PR merge.",
      "EN: Lane B — daily Tech SCV → Innovation Lab → Implement → merge GitHub PR.",
      "SK: Lane C — Ut/Št e-shop research pre beebrdy.cz → Knowledge / redesign brief.",
      "EN: Lane C — Tue/Thu e-shop research for beebrdy.cz → Knowledge / redesign brief.",
      "SK: Lane D — Automation: manuálne po schválení A/B/C → Tasks / rutiny.",
      "EN: Lane D — Automation: manual after A/B/C approval → Tasks / routines.",
      "SK: Full doc: docs/SOLO_OPERATOR_FOUR_LANE.md",
      "EN: Full doc: docs/SOLO_OPERATOR_FOUR_LANE.md",
    ],
  },
  {
    id: "digest-inbox",
    title: "7b. Digest Inbox (approve → task)",
    paragraphs: [
      "SK: V Agentic OS → Lanes nájdeš Digest Inbox — zoznam digestov z lane A/C bez prepojeného tasku.",
      "EN: In Agentic OS → Lanes, Digest Inbox lists lane A/C digests without a linked task yet.",
      "SK: Tlačidlo → Task schváli session a vytvorí položku v Tasks s excerptom (simulate-first).",
      "EN: The → Task button approves the session and creates a Tasks row with the excerpt (simulate-first).",
      "SK: Tech SCV (lane B) riešiš cez Innovation Lab, nie cez task promote.",
      "EN: Tech SCV (lane B) is handled via Innovation Lab, not task promote.",
    ],
    checklist: [
      "SK: API GET /solo-operator/four-lanes/digest-inbox",
      "EN: API GET /solo-operator/four-lanes/digest-inbox",
      "SK: API POST /solo-operator/four-lanes/digest-inbox/{session_id}/promote",
      "EN: API POST /solo-operator/four-lanes/digest-inbox/{session_id}/promote",
    ],
  },
  {
    id: "voice-providers",
    title: "6. Voice providers (SK/EN)",
    paragraphs: [
      "SK: V Settings -> AI + Voice keys vies ulozit Grok/Deepgram/OpenAI (STT) a Grok/ElevenLabs/OpenAI (TTS) kluce priamo v aplikacii bez hardcode v deploy suboroch.",
      "SK: V bloku Preferred voice provider nastavis prioritu STT a TTS (Auto alebo explicitny provider). Pri chybe sa automaticky pouzije server fallback.",
      "EN: In Settings -> AI + Voice keys you can store Grok/Deepgram/OpenAI (STT) and Grok/ElevenLabs/OpenAI (TTS) keys directly in the app without hardcoding deploy files.",
      "EN: In Preferred voice provider, choose STT/TTS priority (Auto or explicit provider). On failures, server-side fallback is applied automatically.",
      "SK: V Advanced voice nastaveniach upravis VAD threshold (citlivost zachytenia hlasu), Silence duration (kedy sa veta odosle po tichu) a Voice profile/tone/language pre Grok TTS.",
      "EN: In Advanced voice settings you can tune VAD threshold (speech detection sensitivity), Silence duration (when utterance is committed), and Voice profile/tone/language for Grok TTS.",
      "SK: V Ballroom chate su quick templates (Brainstorm/Code review/Daily sync) a @AgentName mention pre cielenie odpovede na konkretneho agenta.",
      "EN: Ballroom chat now includes quick templates (Brainstorm/Code review/Daily sync) and @AgentName mentions to target specific agents.",
      "SK: Voice panel zobrazuje cas nahravania + orientacny odhad voice costu s varovanim pri dlhej relacii.",
      "EN: Voice panel now shows capture time + rough voice cost estimate with a long-session warning.",
      "SK: Voice ma hard cap pre jednu session (auto-stop), aby sa drzal nizky load a plynuly chat.",
      "EN: Voice has a per-session hard cap (auto-stop) to keep load low and chat responsive.",
    ],
    checklist: [
      "SK: Ulož API kľúče, otestuj provider tlačidlom Test, potom nastav preferenciu STT/TTS.",
      "SK: Over v Ballroom, že hlasový vstup ide cez server a odpoveď Orchestratora príde aj ako audio.",
      "EN: Save API keys, test each provider with Test, then select STT/TTS preference.",
      "EN: Verify in Ballroom that voice input is processed server-side and Orchestrator replies as audio.",
      "SK: Ak je odozva pomala, prepni Response mode na Fast, zníž Silence duration (napr. 400-600 ms) a jemne zníž VAD threshold.",
      "EN: If responses feel slow, switch Response mode to Fast, reduce Silence duration (e.g. 400-600 ms), and slightly lower VAD threshold.",
    ],
  },
];

export const APP_FUNCTION_GUIDE: FunctionInfoGroup[] = [
  {
    id: "dashboard",
    title: "Dashboard",
    items: [
      {
        id: "cockpit-home",
        label: "Agentic OS",
        description: "Solo Operator Control Plane — one entry for swarms, Factory, Innovation Lab, and verify-first actions.",
        options: ["Start day / Trio cycle", "Bee Hotline routing"],
      },
      {
        id: "dashboard-overview",
        label: "Live dashboard",
        description: "Advanced ColonyConsole — full Queen dashboard with agents, tasks, and live swarm network.",
        options: ["Otvorenie detailov swarms/costs/monitoring", "Rýchla orientácia pred akciou"],
      },
      {
        id: "dashboard-monitoring",
        label: "Monitoring",
        description: "Diagnostika host pressure, queues a telemetrie.",
        options: ["Sledovanie driftu výkonu", "Kontrola incident signálov"],
      },
    ],
  },
  {
    id: "agents",
    title: "Agents + Supervisor",
    items: [
      {
        id: "agents-session",
        label: "Supervisor sessions",
        description: "Riadenie session lifecycle: running, needs_input, completed.",
        options: ["Approve/Reject krokov", "Kontrola session výstupu", "Follow-up inštrukcie"],
      },
      {
        id: "agents-spawn",
        label: "Spawn agent",
        description: "Vytvorenie nového agenta v rámci swarm orchestration.",
        options: ["Definícia roly", "Zaradenie do swarm lane", "Inicializačné nastavenia"],
      },
      {
        id: "agents-foragers",
        label: "Foragers",
        description: "Dynamické ingest workers s napojením na routines, HiveMind a spawn flow.",
        options: ["CRUD foragerov", "Source/filter konfigurácia", "Manual ingest a spawn agenta"],
      },
    ],
  },
  {
    id: "tasks",
    title: "Tasks + Routines",
    items: [
      {
        id: "tasks-new",
        label: "New task",
        description: "Založenie novej úlohy pre execution pipeline.",
        options: ["Priority", "Popis a cieľ", "Priradenie k workflow/session"],
      },
      {
        id: "tasks-routines",
        label: "Routines",
        description: "Periodické automatizované task flows.",
        options: ["Interval/schedule", "Aktivácia/deaktivácia", "Kontrola posledného behu"],
      },
    ],
  },
  {
    id: "knowledge",
    title: "Knowledge",
    items: [
      {
        id: "knowledge-hivemind",
        label: "HiveMind retrieval",
        description: "Vyhľadávanie existujúceho kontextu a historických výstupov.",
        options: ["Filter podľa témy", "Reuse predchádzajúcich riešení"],
      },
      {
        id: "knowledge-outputs",
        label: "Outputs archive",
        description: "Archivácia a opakované použitie doručených výstupov.",
        options: ["Kontrola kvality výsledku", "Väzba na ďalšie tasky"],
      },
      {
        id: "knowledge-dreaming",
        label: "Memory + Dreaming",
        description: "Automatická konsolidácia lessons learned zo supervisor sessionov do HiveMind.",
        options: ["Enable/disable", "Frequency", "Manual trigger + Dream Reports"],
      },
    ],
  },
  {
    id: "integrations",
    title: "Integrations",
    items: [
      {
        id: "integrations-connectors",
        label: "Dynamic Connector Hub",
        description: "Správa konektorov, auth stavu a testovania pripojení.",
        options: ["Connector create/update", "Connection test", "Vault sync"],
      },
      {
        id: "integrations-marketplace",
        label: "Tools Marketplace",
        description: "Inštalácia API toolov a ich sprístupnenie supervisor lanes.",
        options: ["One-click install", "Katalóg dostupných nástrojov"],
      },
    ],
  },
  {
    id: "operator-cockpit",
    title: "Agentic OS",
    items: [
      {
        id: "cockpit-four-lanes",
        label: "Four Lanes",
        description:
          "Solo operator control — four parallel missions with pause/resume, bootstrap, and approve links. Replaces 16-routine Virtual Company sprawl.",
        options: [
          "Bootstrap lanes — pause legacy + bind marketing/tech/eshop/automation",
          "Pause/Resume per lane",
          "Digest Inbox — approve → task one-click",
          "Approve → Agents sessions or Innovation Lab",
        ],
      },
      {
        id: "cockpit-digest-inbox",
        label: "Digest Inbox",
        description:
          "Queue of four-lane digest sessions — review excerpt, open session, promote to Tasks (marketing/e-shop).",
        options: ["→ Task one-click", "Tech SCV → Innovation Lab"],
      },
      {
        id: "cockpit-overview",
        label: "Operator overview",
        description:
          "Daily command surface — prioritized actions, Oracle warnings, Trust Autopilot lanes, and Proof-of-Hive receipts.",
        options: ["Start day (trio cycle)", "Refresh core snapshot", "Jump to Factory / Swarms / Agents"],
      },
      {
        id: "cockpit-command",
        label: "Command lane",
        description: "Hotline, Intent Crystallizer, and Zero-UI Telegram — three ways to drive the hive without hunting panels.",
        options: ["Natural language Hotline", "Crystallizer preview/launch", "Telegram /day /status /hotline"],
      },
      {
        id: "bee-hotline",
        label: "Bee Hotline",
        description: "Plain-language request → routed Queen goal on the correct bee lane.",
        options: ["One sentence operator intent", "Server action hotline", "No manual nav required"],
      },
      {
        id: "intent-crystallizer",
        label: "Intent Crystallizer",
        description: "Free text → swarm templates, trust lane, and deep links before launching Queen.",
        options: ["Preview plan", "Launch Queen goal", "Trust lane auto/simulate/live"],
      },
      {
        id: "zero-ui-hive",
        label: "Zero-UI Hive Mode",
        description: "Telegram commands mirror Agentic OS — optional web UI after bot + webhook setup.",
        options: ["Execution Studio notifications", "Webhook URL + secret", "/help command list"],
      },
      {
        id: "icm-tools",
        label: "ICM tools",
        description: "Link drop, dialogue extract, and quick automations — capture intent without the swarm builder.",
        options: ["URL → brief → Knowledge", "Transcript → harness/knowledge/recipe", "Quick automation presets"],
      },
      {
        id: "swarm-fleet",
        label: "Swarm Fleet",
        description: "Always-on routines with pause/resume and immune watch/quarantine signals.",
        options: ["Pause/resume routine", "Autopilot schedule", "Immune system recommendations"],
      },
      {
        id: "cockpit-modules",
        label: "Futurist modules",
        description: "Lazy-loaded experimental modules — Regret, Teleport, Ambient, Parallel, Evolutionary Recipes.",
        options: ["On-demand load", "Verified outcomes for recipes", "No duplicate swarms"],
      },
      {
        id: "innovation-lab",
        label: "Innovation Lab",
        description: "Brainstorm → approve → Queen Maintainer PR-only implementation.",
        options: ["Brainstorm proposal", "Approve/reject gate", "Implement via Maintainer"],
      },
    ],
  },
  {
    id: "ballroom",
    title: "Ballroom",
    items: [
      {
        id: "ballroom-realtime",
        label: "Realtime lane",
        description: "Live coordination during incidents and critical deploy flows.",
        options: ["Fast ops lane", "Link to Supervisor sessions"],
      },
    ],
  },
  {
    id: "settings",
    title: "Settings",
    items: [
      {
        id: "settings-security",
        label: "Security",
        description: "2FA, auth guardy a bezpečnostné pravidlá účtu.",
        options: ["TOTP setup", "Session bezpečnosť", "Auth preference"],
      },
      {
        id: "settings-team",
        label: "Team RBAC",
        description: "Role-based access control pre členov tenantu.",
        options: ["Role assignment", "Permission governance", "Access revocation"],
      },
      {
        id: "settings-billing",
        label: "Billing/Usage",
        description: "Rozpočty, usage signály a nákladové limity.",
        options: ["Sledovanie spend", "Budget alerts", "Usage review"],
      },
      {
        id: "settings-voice-providers",
        label: "AI + Voice keys",
        description: "Správa API kľúčov pre LLM/STT/TTS a explicitná priorita providerov pre voice pipeline.",
        options: ["Grok/Deepgram/OpenAI pre STT", "Grok/ElevenLabs/OpenAI pre TTS", "Auto fallback pri vypadku"],
      },
    ],
  },
];

