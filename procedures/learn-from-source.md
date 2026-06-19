# HN6 — Learn from source (ST8)

Verified URL or video → intel digest → optional Kanban triage task + wiki capture.

## Steps

1. Paste **one** http(s) URL (YouTube, article, Reddit thread page for context only — not live post).
2. API: `POST /api/v1/solo-operator/learn-from-source` with `{ "url": "...", "wiki_capture": true }`.
3. Review triage task on `/tasks` — Grok cross-check runs via NP8 fetch path.
4. Promote verified insights to HiveMind via wiki gardener or manual Brain Pack edit.

## Guardrails

- No tutor HTML · no autonomous live Reddit (CE6 separate opt-in).
- Requires `LEARN_FROM_SOURCE_ENABLED=true` and NP8 wizard enabled.
- Same discipline gates as ST1 — no auto-approve on critic failure.

## Related

- NP8 batch: `POST /solo-operator/video-url-batch/submit` (multi-URL)
- Procedure `/memory-review` for curated INSTRUCTIONS after distill
