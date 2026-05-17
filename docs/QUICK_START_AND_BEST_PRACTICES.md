# Queenswarm - Quick Start + Best Practices

Toto je praktický manuál pre teba ako hlavného používateľa Queenswarm. Je zameraný na rýchly štart, stabilnú prevádzku a konzistentné výsledky.

## 1. Quick Start

### Prihlásenie a prvé kroky

1. Otvor `https://queenswarm.love/login` a prihlás sa.
2. Po logine začni v `Dashboard`.
3. Skontroluj hornú navigáciu: `Dashboard`, `Agents`, `Tasks`, `Knowledge`, `Integrations`, `Ballroom`, `Settings`.

### Ako spustiť prvý Supervisor

1. Prejdi do `Agents`.
2. Otvor panel pre Supervisor session.
3. Zadaj cieľ jednou vetou (napr. „Analyze failing connector flow and propose safe fix“).
4. Doplň obmedzenia: „no breaking changes“, „include rollback“, „verify on staging first“.
5. Spusť session a sleduj stav (`running`, `needs_input`, `completed`).

### Základné ovládanie (denný rytmus)

1. `Dashboard`: rýchly prehľad stavu.
2. `Agents`: otvorené sessions, hlavne `needs_input`.
3. `Tasks`: priority a rozpracované úlohy.
4. `Knowledge`: predchádzajúce výsledky a kontext.
5. `Integrations`: stav kritických konektorov.
6. `Ballroom`: realtime koordinácia pri incidente.

## 2. Hlavné sekcie

### Dashboard

- Používaj ako centrálny prehľad pred každým väčším rozhodnutím.
- Sleduj, či všetky kľúčové časti aplikácie reagujú bez chýb.

### Agents + Supervisor

- Zakladaj Supervisor sessions pre komplexné úlohy.
- Pri stave `needs_input` reaguj rýchlo a jednoznačne.
- Každá session má mať jasný cieľ a očakávaný výstup.

Odporúčaný formát zadania:
- cieľ,
- kontext,
- obmedzenia,
- definícia hotového výsledku.

### Tasks + Routines

- `Tasks` používaj na jednorazové alebo projektové úlohy.
- `Routines` používaj na opakované procesy (denné/periodické kontroly).
- Ak sa proces opakuje aspoň 3x týždenne, presuň ho do routine.

### Knowledge

- Využívaj ako „retrieval-first“ vrstvu pred novým promptom.
- Over, či podobný výstup už neexistuje.
- Ukladaj sem finálne rozhodnutia, aby sa dali znovu použiť.

### Integrations

- Kontroluj dostupnosť a autorizáciu konektorov.
- Pri problémoch najprv testuj read-only operácie.
- Write operácie spúšťaj až po potvrdení zdravého stavu.

### Ballroom

- Používaj na realtime koordináciu počas incidentov a critical flowov.
- Drž komunikáciu stručnú: problém, rozhodnutie, ďalší krok.

## 3. Najlepšie praktiky

### Ako písať dobré prompty

Používaj štruktúru:
- **Goal**: čo presne má byť výsledok,
- **Context**: len podstatné fakty,
- **Constraints**: čo je zakázané alebo rizikové,
- **Done**: ako overíš, že výsledok je správny.

Príklad:
`Investigate 403 errors in consolidated sections, apply the safest fix without breaking auth flow, and include staging+production verification steps.`

### Ako šetriť zdroje

- Nepúšťaj viac náročných sessions naraz bez priority.
- Pri routines začni konzervatívnym intervalom a postupne dolaď.
- Pred novým výpočtom vždy skontroluj `Knowledge`.
- Pri zvýšenej záťaži zníž paralelizmus a uprednostni kritické workflow.

### Skills & retrieval

- Skill voľ podľa typu úlohy (debug, plan, review, execute).
- Najprv retrieval (`Knowledge`), až potom nový prompt.
- Po významnej zmene vždy over staging smoke/gates pred produkciou.

### Supervisor tipy

- Pri `needs_input` odpovedz jedným jasným rozhodnutím.
- Nemiešaj nesúvisiace témy do jednej session.
- Každú session uzavri konkrétnym výstupom (akčný plán/checklist/rozhodnutie).

## 4. Bežné scenáre

### Scenár A: Ranný 10-minútový startup

1. `Dashboard`: celkový stav.
2. `Agents`: otvorené sessions a `needs_input`.
3. `Tasks`: top priority na dnes.
4. `Integrations`: kritické konektory.
5. `Knowledge`: posledné relevantné outputs.

### Scenár B: Nový problém v produkcii

Use case: chyba v jednej sekcii po deployi.

1. V `Agents` založ Supervisor session s cieľom diagnostiky.
2. Pridaj obmedzenia: bez breaking changes, rollback povinný.
3. V `Tasks` založ task na implementáciu fixu.
4. Výsledok a verifikáciu zapíš do `Knowledge`.

### Scenár C: Zavedenie routine

Use case: denná kontrola stability integrácií.

1. V `Tasks + Routines` vytvor routine.
2. Definuj očakávaný výstup (napr. „daily integration health summary“).
3. Sleduj prvé behy a dolaď frekvenciu.
4. Ak routine neprináša hodnotu, uprav ju alebo vypni.

### Scenár D: Incident war-room

1. Potvrď symptóm (`Dashboard` + relevantná sekcia).
2. Spusť cieľenú session v `Agents`.
3. Koordinuj rozhodnutia v `Ballroom`.
4. Ulož postmortem kroky do `Knowledge`.

## 5. Troubleshooting

### Problém: po kliknutí ma vracia na login

- Over, že login prebehol úspešne.
- Skontroluj, či session cookie existuje.
- Ak je redirect, over `next` cieľovú cestu.

### Problém: 401/403 na `/api/proxy/*`

- 401 zvyčajne znamená problém so session/tokenom.
- 403 býva RBAC/permission guard.
- Over, že si prihlásený pod správnym tenant/rolou.

### Problém: session stojí na `needs_input`

- Otvor detail session v `Agents`.
- Odpovedz explicitne (Approve/Reject + presný pokyn).
- Vyhni sa všeobecným odpovediam bez rozhodnutia.

### Problém: routine nebeží

- Over, že routine je aktívna.
- Skontroluj posledný run a chybový detail.
- Over zdravie worker/beat komponentov.

### Problém: Integrations nevracajú dáta

- Over stav konektora v `Integrations`.
- Over auth/scope.
- Spusť read-only test pred write operáciou.

### Problém: app je pomalá

- Skontroluj `health` a `health/ready`.
- Over vyťaženie backend workerov.
- Dočasne zníž počet paralelných ťažkých úloh.
