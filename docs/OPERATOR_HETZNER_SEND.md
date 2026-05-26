# Operator — Hetzner abuse reply (AbuseID 11B0286:23)

Manual step — Queenswarm cannot send email on your behalf. Use the draft below.

## One command — fresh draft + copy-paste

```bash
./scripts/operator-hetzner-copy-email.sh
```

This refreshes the reply with **latest host exposure audit** and prints the full email body.

## Mail client fields

| Field | Value |
|-------|--------|
| **To** | `abuse@hetzner.com` |
| **Subject** | `Re: AbuseID 11B0286:23 — remediation completed` |
| **Body** | Output of `./scripts/operator-hetzner-copy-email.sh` |

Use plain text. Include the audit evidence section at the bottom (script adds it automatically).

## What was fixed

- Redis/Postgres/Neo4j/Prometheus/Grafana/backend/frontend **no longer bound to 0.0.0.0**
- Redis **requirepass** enabled; broker URLs synchronized
- UFW **DENY** on data-plane ports (6379, 5432, 7474, 7687, 9090, 3030, 8000, 3000)
- Only **nginx** on 80/443 for `queenswarm.love`

## Verify before sending

```bash
./scripts/audit-host-exposure.sh   # must exit 0
./scripts/operator-hetzner-send-prep.sh
```

## After send

```bash
./scripts/operator-mark-hetzner-sent.sh
./scripts/operator-pending-status.sh
```

## Regenerate draft only

```bash
./scripts/hetzner-abuse-reply.sh
# → reports/hetzner/hetzner-reply-*.txt
```

## References

- `docs/OPERATOR_P0_CLOSE.md`
- `scripts/audit-host-exposure.sh`
- `scripts/harden-prod-firewall.sh`
