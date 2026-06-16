# Operator — Robinhood Agentic MCP (US equities)

Príprava **Connector Hub** presetu pre Robinhood Agentic Trading MCP. SK/EU operátor primárne používa **Polymarket** + **Track O** journal — Robinhood je voliteľný US equities lane.

**Filozofia:** simulate-first · broker guardrails (RA3) · HITL order queue (RA5) · žiadny raw Claude Code loop bez schválenia.

---

## Prehľad

| Marketplace template | Slug | Auth | MCP server |
|---------------------|------|------|------------|
| Robinhood · Agentic MCP | `robinhood_agentic` | OAuth2 | `https://agent.robinhood.com/mcp/trading` |

**Oficiálna dokumentácia:** [Robinhood Agentic Trading overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/)

**Video referencia:** [Ryan Doser — Robinhood AI agent with Claude MCP](https://www.youtube.com/watch?v=w4QrQdulH0g)

---

## 1. Marketplace install (RA1)

1. **Integrations → Marketplace** → **Robinhood · Agentic MCP**
2. Klik **Install** — vytvorí dynamic connector slug `robinhood_agentic` s base URL `https://agent.robinhood.com/mcp/trading`
3. Over v **Connector Hub** že connector je **active**

Alternatíva cez API:

```bash
# POST /api/v1/tools/marketplace/install  (source=phase3_template, entry_id=robinhood_agentic_mcp)
```

---

## 2. OAuth + Agentic account

Robinhood Agentic vyžaduje **US Robinhood účet** a **ring-fenced Agentic balance** (oddelené od hlavného účtu).

1. V Robinhood app/web aktivuj **Agentic Trading** podľa oficiálneho návodu
2. Dokonči OAuth pre MCP klienta (desktop flow ako vo videu — Claude Desktop / MCP klient)
3. V **Integrations → Connector Vault** pre slug `robinhood_agentic` seal:
   - `oauth2_access_token` (povinné)
   - `oauth2_refresh_token` (odporúčané)
   - `oauth2_token_endpoint` ak Robinhood poskytne refresh URL

**Bezpečnosť:** tokeny len vo Vault — nikdy do `.env` commitu ani do LLM promptov.

---

## 3. Broker guardrails (RA3)

Pred akýmkoľvek live orderom:

1. **Apps & Tools → Trading Automation → Broker guardrails**
2. Zapni venue **robinhood**
3. Nastav **max order USD**, **daily cap**, **approve mode**
4. Kill switch musí byť **OFF**

---

## 4. Broker MCP tab (RA2)

1. **Apps & Tools → Trading Automation → Broker MCP**
2. Skontroluj checklist (install · OAuth · guardrails · probe)
3. **Run probe** — zaznamená `last_probe_at` bez live orderu
4. Keď `ready=true`, ordery idú cez **HITL queue** (RA5), nie priamo z agenta

---

## 5. HITL order queue (RA5)

Live equity orders:

1. Agent alebo operátor **navrhne** order → Approval Inbox
2. Operátor **schváli** po simulácii
3. Teprva potom MCP `place_order` (guardrails + queue gate)

---

## 6. Queenswarm vs raw MCP video

| Video flow | Queenswarm moat |
|------------|-----------------|
| Pridať MCP URL do Claude | Marketplace preset + Connector Hub |
| NL orders v Claude | Supervisor + guardrails + HITL queue |
| Žiadne guardrails | RA3 caps + kill switch |
| Žiadny audit | RA5 queue + journal (Track O) |

---

## 7. Prep script

```bash
./scripts/operator-robinhood-mcp-prep.sh
./scripts/audit-broker-robinhood-mcp-gate.sh
```

---

## EU / SK poznámka

Robinhood Agentic = **US equities only**. Pre SK operátora odporúčame primárny lane **Polymarket** (`docs/OPERATOR_PREDICTION_MARKETS_SETUP.md`) + **Trading Journal** (Track O).
