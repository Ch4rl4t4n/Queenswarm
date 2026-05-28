# Production security checklist — Queenswarm

Use this before **every** production deploy on a public VPS (Hetzner, etc.) and after any Docker Compose change that touches ports or data stores.

Related: [PRODUCTION_SIGNOFF.md](./PRODUCTION_SIGNOFF.md) (functional QA), [OPERATOR_AUDIT.md](./OPERATOR_AUDIT.md) (operator flows).

---

## 1. Automated pre-deploy (required)

```bash
# From repo root — generates REDIS_PASSWORD if missing, updates REDIS_URL/Celery URLs
./scripts/ensure-redis-password.sh .env.prod

# Firewall: deny data-plane ports; allow only 22/80/443 (run as root)
sudo ./scripts/harden-prod-firewall.sh

# Validate prod env + security flags
./scripts/validate-prod-env.sh

# Exposure audit — must exit 0 before deploy
./scripts/audit-host-exposure.sh
```

Deploy (includes Redis password step automatically):

```bash
REQUIRE_VOICE_READY=0 POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh
```

Full sign-off:

```bash
SKIP_BACKEND_TESTS=1 PLAYWRIGHT_BASE_URL=https://queenswarm.love ./scripts/production-signoff-gate.sh
```

---

## 2. Network exposure rules (non-negotiable)

| Service | Production rule |
|---------|-----------------|
| **nginx** | Only public entry: `80`, `443` on `0.0.0.0` |
| **Redis** | **Never** publish host port; `requirepass` mandatory |
| **Postgres** | **Never** publish host port |
| **Neo4j** | **Never** publish host port |
| **Prometheus / Grafana** | **Never** publish host port; use nginx subpath if needed |
| **Backend / Frontend** | **Never** publish host port; traffic via nginx only |

Implementation: `docker-compose.prod.yml` uses `ports: !reset []` on all data-plane services. Dev/local uses `127.0.0.1:PORT` binds in `docker-compose.base.yml` only.

---

## 3. Manual verification (2 minutes)

```bash
# No data-plane listeners on the host (expect empty or "OK")
./scripts/audit-host-exposure.sh

# Docker: only nginx should show 0.0.0.0
docker ps --format '{{.Names}} {{.Ports}}' | grep -E '0.0.0.0' 
# Expected: queenswarm_prod-nginx-1 ... 0.0.0.0:80->80, 0.0.0.0:443->443

# Redis unreachable from host (Connection refused = good)
redis-cli -h 127.0.0.1 ping || true

# App health via public edge only
curl -sf https://queenswarm.love/health
curl -sf https://queenswarm.love/api/v1/health
```

UFW should show **DENY** for `6379`, `5432`, `7474`, `7687`, `9090`, `3030`, `8000`, `3000`.

---

## 4. Secrets & auth

- [ ] `.env.prod` is gitignored; never commit real secrets
- [ ] `REDIS_PASSWORD` set (64-char hex from `ensure-redis-password.sh`)
- [ ] `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` include `:password@`
- [ ] `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `SECRET_KEY` (≥64 chars in prod mode)
- [ ] `CONNECTOR_VAULT_FERNET_KEY` set
- [ ] `PRODUCTION_SECURITY_MODE=true`, `RATE_LIMIT_ENABLED=true`
- [ ] JWT auth on all API routes except `/health`, `/metrics`, `/docs`

Generate missing secrets:

```bash
./scripts/generate-env-secrets.sh >> secrets-rotate-$(date +%F).txt
# Merge manually into .env.prod — do not commit the output file
```

---

## 5. Hetzner / abuse report response

If you receive mail from `abuse@hetzner.com` (BSI CB-Report, open Redis/DB):

1. Run sections 1–3 immediately
2. Reply to abuse@hetzner.com with **AbuseID** and remediation summary:

```bash
./scripts/hetzner-abuse-reply.sh   # prints draft + audit evidence
```

Or manually:

> Redis/Postgres were publicly exposed due to Docker Compose port publishing without authentication.  
> Remediated: removed public port bindings, enabled Redis AUTH, hardened UFW, redeployed.  
> Only ports 80/443 remain publicly accessible via nginx.

3. Keep evidence: `./scripts/audit-host-exposure.sh` output + deploy timestamp

---

## 6. What went wrong (May 2026 incident)

**Root cause:** `docker-compose.base.yml` defaulted to:

```yaml
ports:
  - "${REDIS_PUBLISH_PORT:-6379}:6379"   # bound 0.0.0.0
```

Redis ran **without** `--requirepass`. BSI scanners detected open Redis on Hetzner AS24940.

**Also exposed:** Postgres `5432` (UFW ALLOW), Neo4j, Prometheus, Grafana, direct backend/frontend ports.

**Fix:** Prod overlay unpublishes ports, Redis AUTH, firewall deny rules, dev binds to `127.0.0.1` only.

---

## 7. Quarterly rotation

- [ ] Rotate `REDIS_PASSWORD` → update `.env.prod` URLs → redeploy
- [ ] Rotate `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `SECRET_KEY`, `DASHBOARD_JWT`
- [ ] Re-run `./scripts/audit-host-exposure.sh` after rotation

---

## Quick reference scripts

| Script | Purpose |
|--------|---------|
| `scripts/ensure-redis-password.sh` | Redis AUTH + URL sync in `.env.prod` |
| `scripts/harden-prod-firewall.sh` | UFW deny data-plane ports |
| `scripts/audit-host-exposure.sh` | Fail if 6379/5432/… listen on `0.0.0.0` |
| `scripts/deploy-prod.sh` | Prod deploy (calls ensure-redis-password) |
| `scripts/validate-prod-env.sh` | Security env validation |
| `scripts/production-signoff-gate.sh` | Full automated gate |
