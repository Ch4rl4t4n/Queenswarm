# @queenswarm/agentic-os

TypeScript event contracts and gate preview helpers for Queenswarm Agentic OS.

Mirrors Python backend (`agentic_gates.py`, `commerce_order_sync.py`) for:

- n8n / Node webhook fan-out
- Cursor Composer tooling
- Future DAG export (Week 4+)

## Usage

```bash
cd packages/agentic-os
npm install
npm run typecheck
npm test
```

```typescript
import { isCommerceOrderSyncEvent, previewSocialPublishGate } from "@queenswarm/agentic-os";

// Redis pub/sub or webhook relay
redis.subscribe("swarm_events", (msg) => {
  const payload = JSON.parse(msg);
  if (isCommerceOrderSyncEvent(payload)) {
    // route to eshop-ops workflow
  }
});
```

**Server is source of truth** for gate enforcement — this package is for client preview and external orchestration only.
