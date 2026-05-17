# Production Readiness Audit

Date: 2026-05-17

## Summary

Queenswarm is aligned to a production-only deployment model. The repository and runtime no longer depend on a staging environment, and all critical operational paths were updated to prevent stale references.

## Completed checks

- Production deploy script readiness: `scripts/deploy-prod.sh`
- Production health probe script readiness: `scripts/health-check.sh`
- Production smoke script readiness: `scripts/smoke-edge.sh`
- TLS issuance script readiness: `scripts/issue-letsencrypt.sh`
- HA chaos smoke defaults aligned to production compose: `scripts/ha-chaos-smoke.sh`
- Final hardening orchestration script added: `scripts/final-150-gates.sh`
- Security gate script added: `scripts/security-gates.sh`
- SLO/soak scripts added: `scripts/slo-check.sh`, `scripts/soak-check.sh`
- DR/rehearsal scripts added: `scripts/dr-drill.sh`, `scripts/release-rehearsal.sh`
- CI strict security enforcement enabled for dependency gate (`SECURITY_STRICT=1`).
- Deep validation workflow includes strict security gate execution from final-150 flow.

## BE/FE compatibility checks

- `cd backend && ./venv/bin/pytest --no-cov` -> `382 passed`
- `cd frontend && npm run lint && npm run typecheck && npm run test -- --run` -> pass
- `./scripts/phase70-gates.sh` -> pass
- `./scripts/phase120-gates.sh` -> pass
- `cd frontend && npm run typecheck` -> pass
- `backend/.venv/bin/pytest backend/tests/test_phase52_scripts_exist.py -q` -> pass
- Shell syntax validation for updated scripts -> pass
- `./scripts/security-gates.sh` -> pass, no known vulnerabilities (`pip=0`, `npm=0`)
- `./scripts/final-150-gates.sh` -> pass after final dependency remediation

## Functional policy

- Development: local only.
- Deployment target: production only.
- Mandatory post-deploy validation:
  - `./scripts/health-check.sh`
  - `./scripts/smoke-edge.sh`
- Recommended hardening pass before release:
  - `./scripts/final-150-gates.sh`
  - `./scripts/security-gates.sh`
  - `./scripts/slo-check.sh`
  - `DURATION_MIN=30 ./scripts/soak-check.sh`
  - `./scripts/dr-drill.sh`

## Verdict

**GO** — repository and operations are consistent with production-only workflow, with no remaining hard references to removed staging infrastructure, and dependency security baseline is currently clean.
