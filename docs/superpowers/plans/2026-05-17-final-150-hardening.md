# Final 150 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production-only hardening layer (security, deep validation, soak/DR/SLO governance, release rehearsal) without breaking existing backend/frontend behavior.

**Architecture:** Keep changes additive and script-driven. Existing runtime and feature paths remain unchanged; new verification scripts and docs enforce stronger operational confidence. CI receives a dedicated security lane and optional deep validation lane.

**Tech Stack:** Bash, GitHub Actions, pytest, Vitest/Playwright, pip-audit, npm audit.

---

### Task 1: Add final validation gate orchestration

**Files:**
- Create: `scripts/final-150-gates.sh`

- [ ] Add script that runs backend full tests, frontend lint/typecheck/unit, phase70 + phase120 gates, optional full E2E and optional edge checks.

### Task 2: Add security, soak, DR, and SLO utilities

**Files:**
- Create: `scripts/security-gates.sh`
- Create: `scripts/soak-check.sh`
- Create: `scripts/dr-drill.sh`
- Create: `scripts/slo-check.sh`

- [ ] Add a security gate script for dependency audit + secret-pattern scan.
- [ ] Add soak and SLO probe scripts with machine-readable summaries.
- [ ] Add DR drill wrapper that records timing evidence.

### Task 3: Add governance docs and release hardening

**Files:**
- Create: `docs/SLO_ALERTING_GOVERNANCE.md`
- Create: `docs/RELEASE_REHEARSAL.md`
- Modify: `docs/FINAL_PRODUCTION_DEPLOY_CHECKLIST.md`
- Modify: `AUDIT_REPORT.md`
- Modify: `docs/PRODUCTION_READINESS_AUDIT.md`

- [ ] Document SLOs, alert policy, and release rehearsal process.
- [ ] Update production checklist with mandatory hardening steps.
- [ ] Refresh audit/readiness docs with new 150% hardening commands.

### Task 4: Extend CI hardening lanes

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] Add a security job that runs `scripts/security-gates.sh`.
- [ ] Add an opt-in deep validation job for full E2E + final 150 gate script.

### Task 5: Verify no regressions

**Files:**
- Modify (if needed): `frontend/lib/hive-nav-primary.test.ts`

- [ ] Run backend full tests.
- [ ] Run frontend lint/typecheck/unit.
- [ ] Run phase70 + phase120 gates.
- [ ] Fix any regressions and re-run checks.
