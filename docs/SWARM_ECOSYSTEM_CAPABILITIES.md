# Swarm Ecosystem Capabilities (Phase 12.0)

Updated: 2026-05-15

## What the ecosystem can do now

Queenswarm now exposes an integrated ecosystem where operators can install tools, control browser agents, and run voice-driven swarm interactions in one loop.

- Discover and install external tools from marketplace templates.
- Run supervised browser automation with explicit approval guardrails.
- Operate Ballroom and supervisor sessions in mixed text + voice mode.
- Dynamically route newly installed tools into supervisor/sub-agent toolsets.
- Monitor tool-level usage, success/failure ratios, and latency snapshots.

## Capability map

### Browser Harness (12.1)

- Real browser sessions with action logs and snapshot previews.
- Guardrails:
  - allowed domains only,
  - private/local network blocks,
  - critical action approval flow.
- APIs:
  - `POST /api/v1/agents/browser-sessions`
  - `GET /api/v1/agents/browser-sessions`
  - `POST /api/v1/agents/browser-sessions/{id}/actions`
  - `POST /api/v1/agents/browser-sessions/{id}/approve`

### Voice + Multimodal (12.2)

- Voice input pipeline: audio chunk -> STT -> transcript.
- Voice output pipeline: text -> TTS -> playback (provider fallback supported).
- UI surfaces:
  - Ballroom voice chat mode,
  - Agents supervisor voice command panel.
- APIs:
  - `POST /api/v1/ballroom/voice/transcribe`
  - `POST /api/v1/ballroom/voice/synthesize`

### Advanced External Tools + Marketplace (12.3)

- Dynamic tool registry for discoverable MCP/custom tools.
- One-click install for curated marketplace templates.
- Supervisor runtime dynamic tool discovery by manager lane + goal.
- APIs:
  - `GET /api/v1/tools/registry`
  - `GET /api/v1/tools/registry/monitoring`
  - `GET /api/v1/tools/marketplace/catalog`
  - `POST /api/v1/tools/marketplace/install`

### Final Ecosystem Polish (12.4)

- Unified ecosystem control plane in `/integrations#ecosystem`.
- Cross-linked operator flow:
  - `/integrations` -> install tools,
  - `/agents` -> supervise browser/tool execution,
  - `/ballroom` -> multimodal collaboration.

## Security and governance posture

- Tenant RBAC on marketplace/registry APIs.
- Tool-level permission checks and manager allowlists.
- Connector and per-tool sliding-window rate limits.
- Tool-level monitoring counters persisted in Redis.
- Browser and voice guardrails preserved from prior blocks.

## Validation checklist

- Backend:
  - `./venv/bin/pytest --no-cov tests/test_ballroom_message_api_unit.py`
  - `./venv/bin/pytest --no-cov tests/test_phase12_browser_openapi_unit.py`
  - `./venv/bin/pytest --no-cov tests/test_tools_marketplace_api_unit.py tests/test_tool_marketplace_service_unit.py`
- Frontend:
  - `npm run lint`
  - `npm run typecheck`
- End-to-end:
  - `E2E_PHASE120_ECOSYSTEM=1 npm run test:e2e:phase120`

Or run the consolidated gate:

```bash
./scripts/phase120-gates.sh
E2E_PHASE120_ECOSYSTEM=1 ./scripts/phase120-gates.sh
```
