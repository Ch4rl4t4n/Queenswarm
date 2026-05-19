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
      "Po prihlásení začni v Dashboarde, skontroluj stav aplikácie a až potom spúšťaj nové sessions.",
      "Prvý Supervisor flow štandardne spúšťaj cez Agents a viaž ho na konkrétny cieľ, obmedzenia a jasný výsledok.",
    ],
    checklist: [
      "Prihlás sa cez /login a potvrď, že si na /dashboard.",
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
      "Dashboard je command center, Agents riadi Supervisor a sessions, Tasks pokrýva execution/routines, Knowledge drží kontext a výstupy, Integrations spravuje konektory a Ballroom je realtime operačný kanál.",
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
      "Ranný check: Dashboard → Agents needs_input → Tasks priority → Integrations stav → Knowledge posledné outputs.",
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
        id: "dashboard-overview",
        label: "Live dashboard",
        description: "Realtime prehľad stavu swarmu, health signálov a aktívnych tokov.",
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
    id: "ballroom",
    title: "Ballroom",
    items: [
      {
        id: "ballroom-realtime",
        label: "Realtime lane",
        description: "Živá koordinácia počas incidentov a kritických deploy flowov.",
        options: ["Rýchla operatíva", "Prepojenie na Supervisor sessions"],
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

