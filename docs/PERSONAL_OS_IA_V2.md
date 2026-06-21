# Personal OS — Information Architecture V2 (SSOT)

> Single Source of Truth pre redizajn UX/IA v **Personal OS Mode** (solo operator).
> Cieľ: otvorím sekciu → vidím 3–8 jasných krokov → každý krok nakonfigurujem na mieste → bez skákania medzi sekciami.
>
> Princíp: **Mission Control = ranný checklist.** Všetko ostatné je voliteľné a schované pod „Pokročilé".

## 1. Problém (prečo V2)

Pôvodný stav (`/tasks` mal 20+ panelov):

- **Feature-first IA** — navigácia kopírovala backend featury, nie operátorov workflow.
- **Cross-link hell** — jedna úloha (napr. „nahraj produkt") vyžadovala 3–4 prepnutia sekcií.
- **Dashboard ≠ workflow** — telemetria a power-user panely zaberali priestor pred dennými akciami.
- **Legacy clutter** — Gumroad/revenue nudge zostávali aj po tom, ako ich operátor vypol.

## 2. Princípy V2

1. **Workflow-first, nie feature-first** — sekcia = cieľ operátora, nie názov služby.
2. **Progressive disclosure** — default lite; pokročilé za `<button>Zobraziť pokročilé</button>`.
3. **In-place config** — konfigurácia kroku žije v tom istom paneli, nie v inej sekcii.
4. **Process rail ako kompas** — vždy viem, v ktorom kroku som; klik = scroll na panel (nie route change).
5. **Plain language** — slovenský/ľudský jazyk, žiadny interný žargón v primárnom toku.
6. **Verify-first** — do inboxu/Jarvisa idú len simuláciou overené veci.

## 3. Personal OS Lite — Mission Control (`/tasks`)

Default viditeľné (lite):

| # | Panel | Anchor id | Účel |
|---|-------|-----------|------|
| 1 | Denný štart (guide) | `mission-step-setup` | 3-krokový ranný checklist v ľudskej reči |
| 2 | Jarvis advisor | `mission-step-plan` | max 3 prioritné kroky s „Do this" |
| 3 | Kanban board | `mission-kanban` | reálne úlohy (Najman, E-shop…) |
| 4 | Approvals (Verify) | `mission-step-verify` | schválenia po simulácii |
| — | Strategic Today (Next) | `mission-step-learn` | čo ďalej |

Schované pod **„Zobraziť pokročilé"** (lite): Agent scorecard, Rapid loop, Sub-swarm fleet,
Autopilot grid, Brain Pack, Data monitor, Discovery, Loop Guardrails, Skill Factory Harness,
Goldmine, Social Intel, Second brain, telemetry strips, AFK running (`mission-step-done`).

### Process rail (kompas)

`frontend/components/hive/process-rail.tsx` — 6 krokov `setup → plan → work → verify → learn → done`.
Klik na krok = `scrollIntoView` na anchor (viď tabuľka). **Nie** je to routovanie; ostávaš na `/tasks`.
Mapovanie: `mission-home-panel.tsx → handleSelectStep()`.

## 4. Cieľová navigácia (7 sekcií)

Každá sekcia má interný stepper (3–8 krokov), in-place config, žiadne nútené prepínanie:

| Sekcia | Cieľ operátora | Kroky (príklad) |
|--------|----------------|-----------------|
| **Mission Control** | Denná operatíva | Štart → Jarvis → Kanban → Verify → Sleep |
| **Build** (Factory) | Vyrob výstup | Brief → Generate → Simulate → Refine → Ship |
| **Knowledge** | Pamäť & recepty | Capture → Curate → Recipes → Search |
| **Swarm** | Agenti & roje | Spawn → Assign → Monitor → Imitate |
| **Insights** | Telemetria & učenie | Loop → Quality → Goldmine → Reflect |
| **Integrations** | Pripojenia & skills | Connect → Skills → Test → Enable |
| **Settings** | Konfigurácia & harness | Mode → Memory → Guardrails → Deploy |

Globálny prístup ku všetkému cez **⌘K** (command palette) — nič sa nestráca, len sa default skryje.

## 5. Čo NEROBIŤ

- Nepridávať panel na Mission Control bez gate-u `mission_home_lite` (default lite v Personal OS).
- Nevracať Gumroad/revenue nudge do Jarvisa/inboxu, kým `personal_os_revenue_approvals_enabled()` je False.
- Process rail nikdy nesmie routovať preč z `/tasks` — len scroll.
- Žiadny `HiveTopBar` / duplicitný search bar na desktope (≥1024px).

## 6. Implementačný stav

- **P0 (done):** Lite Mission Home + Gumroad off (`personal_os_revenue_approvals_enabled`,
  `mission_home_lite`, `MissionHomeDailyStartCard`).
- **P1 (done):** Process rail scroll-to-step + anchory na 6 krokov + lite Kanban.
- **P2 — Mission Control gold standard (done):** podsekčný menu bar **Dnes | Board | Schválenia |
  Výsledky** + znovupoužiteľný primitív `SectionWorkspace`. „Do this" v Jarvisovi pre **verify** kroky
  je teraz **inline akcia** (scroll na inline approval inbox v Mission Control), nie navigácia na mŕtvy
  odkaz; ostatné kroky majú čestný label **„Otvoriť"**. Inline `BusinessApprovalInbox` (reuse) schvaľuje
  priamo na mieste → po akcii `reload()` → process rail sa posunie. Nový blok **Výsledky dnes**
  (`MissionResultsPanel`). Mŕtve ciele opravené: `/innovation-lab → /agentic-os#innovation-lab`,
  `/cockpit#approvals → /tasks?tab=approvals`.
- **P3 — Knowledge + Agents deep-link hardening (done 2026-06-21):** existujúce hash subnavy
  (`HiveSectionSubnav` / `HiveSubnavRow`) sú funkčné, takže namiesto re-skinningu (riziko e2e +
  zákaz grafických zmien) sme ich **funkčne spevnili**: Knowledge číta aj `?tab=` (producer odkazy
  `/knowledge?tab=memory#cited-recall`, `?tab=wiki`, `?tab=outputs` fungujú), Agents otvorí
  **Supervisor** pri `?session=`/`?preset=`/`?tab=`. Opravený mŕtvy `#curated-memory →
  #rules-skills`, zapojený `agentsSessions` hint, doplnené hinty na 9 Knowledge panelov, odstránená
  duplicita `EpisodicMemoryPanel`.
- **P4 (next):** Build (Factory) + Integrations rovnaká funkčná deep-link/hint pasáž; potom
  konsolidácia navigácie + ⌘K coverage audit.

### Znovupoužiteľný primitív (P2)

`frontend/components/hive/section-workspace/`:

- `useSectionTab` — podsekcia synced do `?tab=` cez `router.replace({ scroll: false })` (bez route change).
- `SectionTabBar` — horizontálny menu bar v canvase (nie globálny top bar); hint `(i)` ako **sibling**
  tlačidiel (nikdy vnorený `<button>` v `<button>`).
- `SectionWorkspace` — shell: tab bar + process-rail slot + bloky + result slot.

Mission Control je prvý konzument; ďalšie sekcie ho len naplnia (`tasks-page-client.tsx` ako vzor).

## 7. Súvisiace súbory

- `backend/app/application/services/personal_os_mode.py` — flagy lite/revenue.
- `backend/app/application/services/mission_home_service.py` — `mission_home_lite`, filter approvals.
- `frontend/components/hive/mission-home-panel.tsx` — lite render + `handleSelectStep`.
- `frontend/components/hive/mission-home-daily-start-card.tsx` — denný guide.
- `frontend/components/hive/process-rail.tsx` — klikateľný kompas.
- `scripts/audit-personal-os-in-app-skills-gate.sh` — gate na lite + Gumroad-off.
