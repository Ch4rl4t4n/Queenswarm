# Operator — Trading Cockpit

Unified control for **paper crypto simulation** and **Polymarket real-money** trading agents.

## Modes

| Mode | Venue | Capital |
|------|-------|---------|
| **Paper** | Paper · crypto simulation | Virtual USD — deposit in-app |
| **Real** | Polymarket | Fund USDC on polymarket.com — Queenswarm proxies signed orders |

## Setup (real money)

1. **Execution Studio → Trading Cockpit** — set venue to **Polymarket**
2. Follow **Polymarket prep** checklist in panel:
   - Install **Gamma** (research)
   - Vault **CLOB** L2 credentials
   - Enable `PREDICTION_MARKETS_LIVE_TRADING_ENABLED` after review
   - Fund wallet on polymarket.com
3. Configure agent principles, watchlist, risk limits
4. External project API for bot execution

## Daily use

- **Paper:** Deposit → Run paper tick → review fills + P&L
- **Real:** Monitor prep checklist → bot sends signed orders via External Project API
- **Operator Loop** surfaces paper P&L + halt status each morning

## Flags

```bash
TRADING_COCKPIT_ENABLED=true
PAPER_TRADING_ENABLED=true
PREDICTION_MARKETS_ENABLED=true
PREDICTION_MARKETS_LIVE_TRADING_ENABLED=false   # operator enables when ready
TRADING_COCKPIT_TELEGRAM_NOTIFY_ON_FILL=true
```

## Gate

```bash
./scripts/audit-trading-cockpit-gate.sh
```

## Related

- [`OPERATOR_PREDICTION_MARKETS_SETUP.md`](OPERATOR_PREDICTION_MARKETS_SETUP.md)
- [`OPERATOR_LOOP_MANUAL.md`](OPERATOR_LOOP_MANUAL.md)
