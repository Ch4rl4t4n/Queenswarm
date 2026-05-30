# Agentic OS — Implementation Guide (Week 2+)

Updated: 2026-05-29  
Status: **Week 1–2 shipped** (gates, connectors, swarms, order sync)

Canonical reference for Queenswarm's **Agentic OS**: multi-tenant e-shop ops, marketing automation, and real-money trading with strict gates.

See also: `docs/AGENTIC_OS_APPS_BLUEPRINT.md` (Core vs Apps layer split).

---

## 1. Project structure

```
Queenswarm/
├── backend/app/
│   ├── skills/                         # Agent Skills (agentskills.io) — 30 loaded
│   │   ├── _template/SKILL.md.example
│   │   ├── operator-approval-gate.md
│   │   ├── real-money-risk-gate.md
│   │   ├── social-simulate-first.md
│   │   └── … (marketing, trading, ecommerce skills)
│   ├── application/services/
│   │   ├── agentic_gates.py
│   │   ├── commerce_webhooks.py
│   │   ├── commerce_order_sync.py
│   │   ├── execution_studio.py
│   │   ├── social_publish.py
│   │   └── supervisor/skills.py
│   ├── infrastructure/connectors/phase3/
│   └── presentation/api/routers/commerce_webhooks.py
├── frontend/lib/swarm-wizard-templates.ts
├── docs/curated_memory_templates/operator_harness_instructions.md.example
├── .cursor/skills/queenswarm-operator-gate/SKILL.md
└── scripts/audit-swarm-readiness-gate.sh
```

| Layer | Stack | Role |
|-------|-------|------|
| Policy + gates | Python FastAPI | Safety, audit, multi-tenant |
| Swarm orchestration | LangGraph supervisor | Bee handoffs, rapid loop |
| Operator UI | Next.js 15 + TS | Wizards, approval UX |
| Heavy AI / trading | Python agents | Paper discipline |

---

## 2. Skill authoring template

Scaffold: `backend/app/skills/_template/SKILL.md.example`  
Meta-skill: `backend/app/skills/skill-authoring-template.md`

After create: update `DEFAULT_ROLE_SKILLS`, run audit script + pytest.

---

## 3. Week 2 (complete)

- **Shopify + Stripe** Phase 3 presets in `catalog.py`
- **Stripe webhooks** → `commerce_order_sync` (Redis idempotent + `swarm_events` fan-out)
- **eshop-ops** + **marketing-ops** swarm wizards

---

## 4. Harness & memory

Paste `docs/curated_memory_templates/operator_harness_instructions.md.example` into Settings → Curated memory → `instructions`.

---

## 5. Gates

`agentic_gates.py`: `evaluate_live_execution_gate`, `evaluate_real_money_gate`, `evaluate_social_publish_gate`.

---

## 6. Environment

See `.env.prod.example` Agentic OS section. Keep `SOCIAL_PUBLISH_LIVE_ENABLED=false` and `COMMERCE_WEBHOOKS_ENABLED=false` until configured.

---

## 7. Testing

```bash
./scripts/audit-swarm-readiness-gate.sh
pytest backend/tests/test_agentic_gates_unit.py \
       backend/tests/test_commerce_webhooks_unit.py \
       backend/tests/test_commerce_order_sync_unit.py \
       backend/tests/test_swarm_readiness_skills_unit.py -q
```

---

## Week 3+ priorities

1. Deploy + enable audit WARN flags
2. Connector Vault → Shopify + Stripe
3. Stripe webhook URL in Dashboard
4. HiveMind UI for order events
5. Innovation Lab E2E
6. GA4 + WooCommerce connectors
