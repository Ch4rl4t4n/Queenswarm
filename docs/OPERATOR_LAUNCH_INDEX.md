# Operator launch index

Dev backlog **complete**. Automated gates **green**. Two human steps remain.

**Fastest path:** [`docs/OPERATOR_QUICKSTART.md`](OPERATOR_QUICKSTART.md)

## Start here

```bash
./scripts/operator-next.sh          # single next human action
./scripts/operator-p0-prep-all.sh     # full status dump
```

## P0 checklist (human order)

| # | Task | Command / doc |
|---|------|----------------|
| 1 | Status snapshot | `./scripts/operator-launch-checklist.sh` |
| 2 | **Hetzner email** | `docs/OPERATOR_HETZNER_SEND.md` → `./scripts/operator-hetzner-copy-email.sh` |
| 4 | Harness webhook | `docs/OPERATOR_HARNESS_WEBHOOK_SETUP.md` |
| 3 | **Verify launch** | `./scripts/operator-post-p0-verify.sh` |

## Quick reference

| Need | Script |
|------|--------|
| All prep at once | `./scripts/operator-p0-prep-all.sh` |
| Tenant UUID | `./scripts/operator-resolve-tenant-id.sh` |
| GitHub webhook env | `./scripts/operator-github-webhook-prep.sh` |
| Hetzner email body | `./scripts/operator-hetzner-copy-email.sh` |
| Next action (one command) | `./scripts/operator-next.sh` |
| Pending JSON | `./scripts/operator-pending-status.sh` |

## Current blockers (typical)

- Hetzner reply not yet sent (draft ready in `reports/hetzner/`)
- Harness webhook env optional until Maintainer automation needed

## References

- `docs/OPERATOR_P0_CLOSE.md`
- `docs/TOMORROW_OPERATOR_RUNBOOK.md`
- `docs/MISSION_EXECUTION_BACKLOG.md`
