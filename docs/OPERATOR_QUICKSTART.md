# Operator quickstart — 3 human steps to launch

Dev backlog **100% complete**. Automated gates **green**. Two operator actions remain.

```bash
./scripts/operator-next.sh
./scripts/operator-pending-status.sh | jq .
```

---

## Step 1 — Hetzner email (~5 min)

```bash
./scripts/operator-hetzner-copy-email.sh
```

| Field | Value |
|-------|--------|
| To | `abuse@hetzner.com` |
| Subject | `Re: AbuseID 11B0286:23 — remediation completed` |
| Body | Full output from script |

After send:

```bash
./scripts/operator-mark-hetzner-sent.sh
```

Guide: `docs/OPERATOR_HETZNER_SEND.md`

---

## Step 2 — Verify launch (~10 min)

```bash
./scripts/operator-post-p0-verify.sh
```

Browser smoke:

- `https://queenswarm.love/integrations?tab=skills` → Premium unlock

Optional harness (post-launch):

```bash
./scripts/operator-github-webhook-prep.sh
./scripts/operator-harness-env-prep.sh
ENV_FILE=.env.prod ./scripts/deploy-prod.sh
```

---

## One command — full prep status

```bash
./scripts/operator-p0-prep-all.sh
```

## References

- `docs/OPERATOR_LAUNCH_INDEX.md`
- `docs/OPERATOR_P0_CLOSE.md`
