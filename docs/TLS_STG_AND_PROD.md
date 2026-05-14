# TLS — Staging (`stg.queenswarm.love`) & Production (`queenswarm.love`)

Certificates live **on the Docker host** under `/etc/letsencrypt` (mounted read-only into nginx). **Issuance cannot be completed inside git**; this runbook is what operators run **once per host** (still no SSH editing of app code — only cert files + nginx reload via deploy script).

---

## 1. Verify what the edge is serving today

```bash
echo | openssl s_client -connect stg.queenswarm.love:443 -servername stg.queenswarm.love 2>/dev/null \
  | openssl x509 -noout -subject -dates -ext subjectAltName
```

- **Staging:** SAN **must** include `DNS:stg.queenswarm.love`. If you only see `queenswarm.love` / `www`, browsers and strict `curl` will fail hostname verification.
- **Production:** SAN should include `queenswarm.love` and `www.queenswarm.love` if both are served.

---

## 2. Issue or expand a certificate (examples)

Use **webroot** or **DNS-01** depending on your host; nginx in this repo already redirects HTTP → HTTPS, so **webroot** often requires a temporary `location ^~ /.well-known/acme-challenge/`** or stopping nginx for standalone — pick the method that matches your ops playbook.

**Dedicated staging cert (recommended):**

```bash
# Example only — adjust webroot / email / agree-tos for your environment
sudo certbot certonly --webroot -w /var/www/certbot \
  -d stg.queenswarm.love \
  --email ops@example.com --agree-tos --non-interactive
```

Expected output paths (see `deploy/nginx/stg.queenswarm.love.conf`):

- `/etc/letsencrypt/live/stg.queenswarm.love/fullchain.pem`
- `/etc/letsencrypt/live/stg.queenswarm.love/privkey.pem`

**Production** (typical dual name):

```bash
sudo certbot certonly --webroot -w /var/www/certbot \
  -d queenswarm.love -d www.queenswarm.love \
  --email ops@example.com --agree-tos --non-interactive
```

Paths referenced in `deploy/nginx/queenswarm.love.conf`:

- `/etc/letsencrypt/live/queenswarm.love/fullchain.pem`
- `/etc/letsencrypt/live/queenswarm.love/privkey.pem`

---

## 3. Reload nginx in Docker

From the repo root (after PEMs exist on the host):

```bash
./scripts/deploy-stg.sh
# or
./scripts/deploy-prod.sh
```

Or `docker compose … exec nginx nginx -s reload` if you only rotated certs without rebuilding.

---

## 4. Validate

```bash
TARGET=stg ./scripts/smoke-edge.sh
# production:
TARGET=prd ENV_FILE=.env.prod ./scripts/smoke-edge.sh
```

When `openssl` shows correct SAN and smoke passes **without** `SMOKE_INSECURE_TLS=1`, TLS work for that hostname is complete.
