# Projekt: Queenswarm - Agentic OS / Agentic Swarm

## Hlavný cieľ
Vytvoriť vysoko efektívny, sebavylepšujúci agentic operačný systém / swarm, ktorý funguje ako inteligentný "včelí úľ" — všetky komponenty spolupracujú, minimalizujú redundanciu a maximalizujú výkon, bezpečnosť a rýchlosť.

## Kľúčové princípy (najvyššia priorita)
- **Maximálna kvalita kódu**, čitateľnosť a maintainability
- **Bezpečnosť** na prvom mieste (security best practices, minimal attack surface)
- **Performance & efektivita** — nízka latencia, nízka spotreba zdrojov
- Neustále sebavylepšovanie (self-improvement loops)
- Modularita, skalovateľnosť a robustnosť
- Všetky zmeny musia byť premyslené, s dobrým error handlingom a testovateľnosťou

## Aktuálny stav
- Control Plane refactor dokončený (compose-only vrstva, bez mazania existujúceho swarmu)
- Solo UX: `/` → `/cockpit`, zjednodušená navigácia (Cockpit · Agents · Knowledge · Integrations · Ballroom)
- Settings keep-alive shell (`/settings/[[...section]]`) + lazy panely
- Execution Studio rozdelený na lazy-loaded sub-panely (scroll perf)
- Všetkých 14 CP modulov live/beta (vrátane Swarm Immune + Evolutionary Recipes)
- Backend: 1195 testov PASS · mission-readiness + operator-release gate green · E2E responsive-shell 69/69

## Štýl práce
Grok Build má pomáhať ako inteligentný spolupracovník — vždy navrhovať plán + diff pred zmenami.
