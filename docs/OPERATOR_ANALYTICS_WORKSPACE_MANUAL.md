# Operator — Analytics Workspace Manual (Track L)

Kompletný postup od **business question** po **simulate export** (Notion / Google Slides). Všetko je **read-only connectors** + **simulate-first** — live export až po critic ≥4/5 a operator approve.

**Súvisiace docs:** [`BUSINESS_DATA_ANALYTICS_OS.md`](BUSINESS_DATA_ANALYTICS_OS.md) · [`OPERATOR_LOOP_MANUAL.md`](OPERATOR_LOOP_MANUAL.md) · [`ROADMAP.md`](ROADMAP.md) P10 Track L

---

## Architektúra (bezpečnostný model)

```
Business Question wizard (DA4)
  → Supervisor session (business-analytics-report, max 5 bees)
  → Data Fetch · Analyst · Narrative · Critic bees
  → Report artifact (DA5) + lineage strip (DA6)
  → Report critic LOOP5 (DA10) — rubric ≥4/5
  → Export inbox simulate (DA8) — Notion / Slides
  → Optional: weekly routine (DA9) + CBO morning brief KPI
```

**Nikdy:** mutácia GA4/warehouse config · export bez critic score · live export bez operator OK.

---

## 1. Príprava (jednorazovo)

| Krok | Kde | Čo |
|------|-----|-----|
| Module | Apps & Tools → **Analytics Workspace** | `/apps-tools/analytics` |
| Connectors | Analytics → **Connectors** (DA7) | GA4 Data API · Google Sheets read · warehouse MCP slot |
| Integrations | Integrations → Marketplace | Aktivuj `ga4_data`, Sheets read-only |
| Swarm template | Overview → **Open template** | `business-analytics-report` v Swarm Builder |
| Skill | Skills registry | `ga4-analytics-playbook` · `business-analytics-playbook` |

Rýchly bootstrap:

```bash
./scripts/operator-analytics-workspace-prep.sh
```

Audit gate (CI + release):

```bash
./scripts/audit-analytics-workspace-gate.sh
```

---

## 2. Business question → session (DA4)

**Apps & Tools → Analytics → Question**

1. Zadaj **business question** (konkrétna, merateľná — nie „analyze everything“).
2. Vyber **date range** a **sources** (GA4 · HiveMind · Sheets).
3. **Preview** — over brief markdown + session goal (`business-analytics-report`).
4. **Dispatch** — vytvorí Mission Kanban task + supervisor session.

**Očakávaný výstup:** toast „Analytics session started“ + link na task/session.

API: `POST /api/v1/analytics-workspace/question-wizard/submit`

---

## 3. Počkaj na bees (supervisor session)

| Bee | Job |
|-----|-----|
| Data Fetch | Read-only metriky + lineage tagy |
| Analyst | Deltas, anomálie, kontext |
| Narrative | Executive markdown + chart blocks |
| Critic | Rubric self-review v session |

Sleduj progress: **Agents → Sessions** alebo task goal strip na `/tasks`.

---

## 4. Report artifact (DA5)

**Analytics → Report**

- Live **markdown** + **chart blocks** (KPI, trend, table).
- Operator môže **Edit → Save** (version bump, lineage refresh).
- Session link zobrazí stav supervisor run.

API: `GET/PATCH /api/v1/analytics-workspace/report-artifact`

---

## 5. Data lineage (DA6)

**Analytics → Lineage**

Každá sekcia musí mať: **connector · query · timestamp**.

- **Verified** = fetch bee potvrdil zdroj.
- **Gap** = chýba citation — doplniť pred exportom.

---

## 6. Report critic closed loop (DA10)

**Analytics → Report** (panel pod artifactom)

1. **Run closed loop** — LOOP5 preset `analytics_report`, rubric `business-analytics-report`.
2. Floor **≥4.0/5** (0.8) pred export staging.
3. Po PASS: badge **export ready** + score persistovaný na deliverable.

API: `GET/POST /api/v1/analytics-workspace/report-critic`

---

## 7. Export inbox (DA8)

**Analytics → Export inbox**

1. **Preview** — Notion page payload alebo Slides deck (simulate).
2. Over **critic score** ≥4/5 v preview paneli.
3. **Simulate submit** — audit záznam, žiadny live API call.
4. Live export: len po operator approve + OAuth connectors (Notion workspace, Google Slides).

API: `POST /api/v1/analytics-workspace/export-lane/preview` · `.../submit`

---

## 8. Weekly routine (DA9, voliteľné)

**Overview → Weekly routine panel** (ak enabled)

- Bootstrap: **Schedule routine** — pondelok leadership deck (UTC cron).
- **CBO morning brief** zobrazí critic score + export readiness.

```bash
# Celery beat (prod)
analytics_weekly_routine_enabled=true
```

---

## 9. Env flags (`.env.prod`)

```bash
ANALYTICS_WORKSPACE_ENABLED=true
ANALYTICS_QUESTION_WIZARD_ENABLED=true
ANALYTICS_REPORT_ARTIFACT_ENABLED=true
ANALYTICS_DATA_LINEAGE_ENABLED=true
ANALYTICS_CONNECTOR_PROFILE_ENABLED=true
ANALYTICS_EXPORT_LANE_ENABLED=true
ANALYTICS_WEEKLY_ROUTINE_ENABLED=true
ANALYTICS_REPORT_CRITIC_ENABLED=true
CLOSED_REVIEW_LOOP_ENABLED=true
CLOSED_LOOP_PRESETS_ENABLED=true
```

Safe defaults: všetko `true`; live Notion/Slides export zostáva simulate until operator enables live lane flags elsewhere.

---

## 10. E2E proof (DA12)

CI journey (mocked API, no LLM):

```bash
cd frontend && npx playwright test e2e/analytics-workspace-journey.spec.ts
```

Per-feature specs: `analytics-*.spec.ts` (DA3–DA10).

---

## 11. Troubleshooting

| Symptom | Fix |
|---------|-----|
| No artifact on Report tab | Dokonči Question dispatch; počkaj na Narrative bee |
| Critic below 4/5 | Run closed loop; edit report citations; re-run |
| Export blocked | Critic PASS + report body ≥20 chars |
| GA4 not ready | Integrations → configure property ID · test connector |
| Lineage gaps | Re-fetch alebo manuálne doplni chart `source_citation` |

---

## 12. Recipe Library (post-verify)

Po úspešnom týždennom cykle ulož verified workflow ako **Recipe** (Mission → Save as recipe) pre ďalší leadership deck.

Track L IDs **DA1–DA12** complete when this manual + journey E2E pass in `./scripts/audit-analytics-workspace-gate.sh`.
