# Operator harness — GitHub post-merge webhook setup

Copy-paste guide for Queen Maintainer automation after merge to `main`.

## Prerequisites

- Prod deploy healthy: `curl -sS https://queenswarm.love/health`
- Dashboard admin access
- GitHub repo admin (webhooks)

## Quick prep scripts

```bash
./scripts/operator-resolve-tenant-id.sh      # tenant UUID for .env.prod
./scripts/operator-github-webhook-prep.sh    # full checklist + sample secret
./scripts/operator-harness-env-prep.sh        # validate all harness keys
```

## 1. Tenant UUID

```bash
./scripts/operator-resolve-tenant-id.sh
```

Copy the suggested `QUEEN_MAINTAINER_POST_MERGE_TENANT_ID` into `.env.prod`.

## 2. Generate webhook secret

```bash
openssl rand -hex 32
```

Use the **same** value in:

1. `.env.prod` → `QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET`
2. GitHub webhook → **Secret**

## 3. `.env.prod` block

```bash
QUEEN_MAINTAINER_ENABLED=true
QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED=true
QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET=<openssl-output>
QUEEN_MAINTAINER_POST_MERGE_TENANT_ID=<tenant-uuid>
QUEEN_MAINTAINER_GITHUB_OWNER=Queenswarm
QUEEN_MAINTAINER_GITHUB_REPO=Queenswarm
```

Optional daily Forager scan:

```bash
FORAGER_INTELLIGENCE_LOOP_ENABLED=true
FORAGER_INTELLIGENCE_CRON_HOUR=6
FORAGER_INTELLIGENCE_CRON_MINUTE=0
```

## 4. GitHub webhook

**Repository → Settings → Webhooks → Add webhook**

| Field | Value |
|-------|--------|
| Payload URL | `https://queenswarm.love/api/v1/queen-maintainer/github-webhook` |
| Content type | `application/json` |
| Secret | same as `QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET` |
| Events | **Pull requests** (required for merge trigger) |
| Active | ✓ |

After save, GitHub sends a **ping**. In **Recent Deliveries**, expect HTTP **200** from Queenswarm.

## 5. Deploy

```bash
ENV_FILE=.env.prod ./scripts/deploy-prod.sh
```

## 6. Verify

```bash
# Health
curl -sS -o /dev/null -w "health:%{http_code}\n" https://queenswarm.love/health

# Webhook without signature → 401/403 after secret configured (not 503)
curl -sS -o /dev/null -w "webhook:%{http_code}\n" \
  -X POST https://queenswarm.love/api/v1/queen-maintainer/github-webhook \
  -H "Content-Type: application/json" -d '{}'

# UI
open https://queenswarm.love/settings/harness
```

## 7. Test merge flow

1. Open a PR in `Queenswarm/Queenswarm`
2. Merge to `main`
3. Check GitHub webhook delivery → 200
4. Queen Maintainer supervisor session should spawn (PR-only workflow)

## References

- `docs/OPERATOR_P0_CLOSE.md`
- `backend/app/application/services/queen_maintainer/post_merge_webhook.py`
- Settings harness → **Post-merge GitHub trigger** panel
