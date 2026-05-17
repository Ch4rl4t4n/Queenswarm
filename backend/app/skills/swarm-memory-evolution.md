---
version: "1.0"
priority: 0.88
roles:
  - supervisor
  - researcher
  - critic
keywords:
  - memory evolution
  - lessons learned
  - swarm learning
  - long-term memory
  - approval gate
---

# Swarm Memory Evolution

Use this skill when long-running sessions produce enough history to consolidate memory.

## Objectives

1. Convert noisy historical traces into compact, high-signal memory entries.
2. Capture both success and failure lessons to improve future swarm decisions.
3. Promote global swarm-level learning, not only session-local memory.
4. Require operator approval for high-impact memory mutations.

## Operator-safe loop

1. Aggregate history from tasks + supervisor sessions.
2. Derive lessons learned with explicit metrics (completion/failure trends).
3. Score update importance and route high-importance changes into pending approval.
4. Auto-apply only low-risk consolidations.
5. Store approved knowledge in both semantic vector lane and graph lane.
