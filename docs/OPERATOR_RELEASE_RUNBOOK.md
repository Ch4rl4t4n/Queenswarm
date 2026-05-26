# Operator Release Runbook — solo + audit gates

Checklist pred každým prod release a týždenný audit. **Bez Stripe** (solo mode).

---

## Pred deployom (dev)

```bash
cd /root/Queenswarm
chmod +x scripts/audit-solo-trio-gate.sh scripts/audit-publish-pack-gate.sh scripts/operator-release-gate.sh

# Backend unit (ak máš pytest v containeri alebo venv)
docker exec queenswarm_prod-backend-1 python -m pytest \
  tests/test_publish_pack_unit.py \
  tests/test_solo_operator_trio_unit.py \
  tests/test_hivemind_verify_unit.py -q
```

---

## Deploy

```bash
./scripts/deploy-prod.sh
# alebo:
docker compose -p queenswarm_prod \
  -f docker-compose.base.yml -f docker-compose.prod.yml \
  --env-file .env.prod build backend frontend celery-worker
docker compose -p queenswarm_prod \
  -f docker-compose.base.yml -f docker-compose.prod.yml \
  --env-file .env.prod up -d backend frontend celery-worker
```

---

## Po deployi — automated gates

```bash
./scripts/operator-release-gate.sh
./scripts/operator-pending-status.sh | jq .
```

Očakávané: **OPERATOR RELEASE GATE: PASS** (health, API routes, exposure audit).

---

## Po deployi — manuálny checklist (15 min)

| # | Akcia | Kde | Prečo |
|---|-------|-----|-------|
| 1 | Vyplniť **Brain Pack** (SOUL/MEMORY/USER) | Knowledge → Memory | Queen kontext |
| 2 | Skontrolovať **3/3 lanes bound** | Settings → AI harness | Trio orchestrácia |
| 3 | **Run today's cycle** (raz) | Settings harness | Overí LLM + critic |
| 4 | **Morning brief** | Settings harness | Digest funguje |
| 5 | **Session search** `sentinel` | Knowledge → Memory | Pamäť swarmu |
| 6 | **SCV approve** | Integrations → Execution Studio | Operator P0 |
| 7 | **Ready to publish** filter | Knowledge → Outputs | Phase A packs (simulate) |

---

## Týždenný audit (pondelok)

```bash
./scripts/operator-release-gate.sh
./scripts/mission-readiness-audit.sh
./scripts/audit-disk-cleanup.sh          # dry-run
./scripts/audit-host-exposure.sh
```

V app:

- HiveMind compliance ≥ 70 % (Knowledge → HiveMind)
- Tech health ≥ 70 % (Settings harness)
- Aspoň 1 completed sentinel session / týždeň
- Queen Maintainer weekly (SCV) — pending proposals review

---

## Phase A publish pack — quality gate

Pred prechodom na Phase B (approval inbox):

```bash
./scripts/audit-publish-pack-gate.sh
```

**Manuálne kritériá:**

- [ ] ≥ 3 verified publish packs v Outputs (`ready_to_publish`)
- [ ] Všetky majú tag `simulate_only`
- [ ] Žiadny pack bez critic APPROVED (tag `publish-pack-verified`)
- [ ] Copy skontrolovaný operátorom (kvalita, nie len LLM)

---

## Bezpečnostné invarianty (nikdy neobchádzať)

1. **simulate_only=true** na publish pack JSON — live bez Phase C
2. **Critic APPROVED** pred tagom `publish-pack-verified`
3. **JWT** na všetky `/outputs`, `/solo-operator/*`
4. **Execution Studio live** len s `operator_confirmed` + throttle
5. **Secrets** nikdy v pack body — validátor rejectne `sk-*` pattern

---

## Ďalšie fázy (referencia)

| Fáza | Doc | Trigger |
|------|-----|---------|
| A simulate pack | `docs/PRODUCTION_AUTOMATION_PHASES.md` | ✅ teraz |
| B approval inbox | same | ≥ 3 verified packs |
| C Instagram API | same | B stabilné 2 týždne |

---

## Súvisiace

- `docs/SOLO_OPERATOR_TRIO_GUIDE.md`
- `docs/SOLO_OPERATOR_MODE.md`
- `docs/OPERATOR_QUICKSTART.md`
