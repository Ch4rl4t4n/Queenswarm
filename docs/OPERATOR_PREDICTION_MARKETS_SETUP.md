# Operator — Polymarket (prediction markets)

Príprava **Connector Hub** konektorov pre trading botov na **Polymarket**. Social OAuth môžeš dokončiť samostatne — tento návod je nezávislý.

**Filozofia:** simulate-first · jeden bot = jeden bee · live obchodovanie až po operator schválení.

---

## Prehľad konektorov

| Marketplace template | Slug | Auth | Účel |
|---------------------|------|------|------|
| Polymarket · Gamma | `polymarket_gamma` | none | Verejné markets/events (research) |
| Polymarket · CLOB | `polymarket_clob` | L2 HMAC | Order book, orders, trading |

---

## 1. Polymarket

### Gamma (bez kľúčov)
1. **Integrations → Marketplace** → **Polymarket · Gamma**
2. Install → **Connector Hub → Test** (probe: `/markets?limit=1`)

### CLOB (trading)
1. Vytvor / import Polygon wallet na [Polymarket](https://polymarket.com)
2. Odvoľ L2 API credentials (apiKey, secret, passphrase) — [Authentication docs](https://docs.polymarket.com/api-reference/authentication)
3. **Marketplace** → **Polymarket · CLOB** → Install
4. **Connector Vault** — seal tieto polia (nie do `.env` commit):
   - `polymarket_api_key`
   - `polymarket_api_secret`
   - `polymarket_api_passphrase`
   - `polymarket_wallet_address`
5. **Test connection** — probe `GET /data/orders`

**Poznámka:** Samotné `order_post` vyžaduje EIP-712 podpis order payloadu — to rieši tvoj **trading bot** (external project), Queenswarm proxyuje podpísané REST hlavičky.

---

## 2. Trading bot (External Project)

Keď pridáš bota neskôr:

```json
{
  "project_kind": "trading",
  "settings": {
    "trading_mode": "paper",
    "venue": "polymarket",
    "connector_slug": "polymarket_clob",
    "watchlist": ["BTC", "ETH"],
    "max_order_usd": 500
  }
}
```

**Paper trading** už existuje (`PAPER_TRADING_ENABLED`) — bot môže bežať v sim režime pred live.

Live orders: `PREDICTION_MARKETS_LIVE_TRADING_ENABLED=true` v `.env.prod` (default **false**).

```bash
APPLY=1 ./scripts/operator-live-trading-prep.sh
```

---

## 3. Real money — Polymarket example

Bot musí poslať **EIP-712 signed order** (Queenswarm neukladá private key walletu):

```json
{
  "action": "execute_trade",
  "payload": {
    "signed_order": { "...": "from your bot CLOB client" },
    "human_approval_confirmed": true,
    "human_approval_ticket": "operator-approve-polymarket-001"
  }
}
```

Vault: L2 creds (`polymarket_api_key`, `secret`, `passphrase`, `wallet_address`).

---

## 4. Guardrails (real money)

| Guard | Popis |
|-------|--------|
| `PREDICTION_MARKETS_LIVE_TRADING_ENABLED` | Globálny kill switch (default off) |
| `trading:live` API key scope | Bez scope → 403 |
| `human_approval_confirmed` + ticket | Každý live order |
| `max_order_usd` | Per-project notional cap |
| Rate limits | 20/venue/deň · 50 celkom/deň (default) |

Status API: `GET /api/v1/prediction-markets/status`

**Trading Cockpit** zobrazuje **Polymarket prep** checklist (Gamma → CLOB → live flag → fund).

---

## 5. Overenie

```bash
./scripts/operator-prediction-markets-prep.sh
./scripts/audit-prediction-markets-gate.sh
./scripts/operator-live-trading-prep.sh   # dry-run; APPLY=1 keď creds + bot ready
```

---

## Súvisiace

- [`OPERATOR_TRADING_COCKPIT_MANUAL.md`](OPERATOR_TRADING_COCKPIT_MANUAL.md)
- [`SOLO_OPERATOR_TRIO_GUIDE.md`](SOLO_OPERATOR_TRIO_GUIDE.md)
- External Projects UI → `/external-projects`
- Paper trading API → `/api/v1/paper-trading`
