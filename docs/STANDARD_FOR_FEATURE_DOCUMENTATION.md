# Standard for Feature Documentation

This document defines the mandatory documentation and UX baseline for every new feature in Queenswarm.

## Purpose

Every feature must be understandable and usable by:
- advanced operators,
- team admins,
- complete beginners.

If a user cannot understand **what it is**, **how to use it**, and **what result to expect**, the feature is not considered complete.

## Mandatory requirements for every new feature

### 1) UI info hints (required)

Every important control in the UI must have contextual guidance using:
- `frontend/components/hive/info-hint.tsx`

At minimum, hints are required for:
- activation controls (enable/disable),
- scheduling/frequency inputs,
- manual trigger actions,
- output/result sections.

Each hint must explain in beginner-friendly language:
- what this control does,
- when to use it,
- what happens after clicking/changing it.

### 2) Detailed manual in SK + EN (required)

Every new feature must be documented in:
- Slovak (SK),
- English (EN).

The documentation should be added to the relevant user manual file (typically `docs/QUICK_START_AND_BEST_PRACTICES.md`) or a dedicated feature guide when needed.

Minimum structure:
1. What the feature is and why it exists
2. How to enable/configure it step by step
3. What it affects in the app
4. Expected outcomes (with practical examples)
5. Performance/resource impact
6. How it works with Supervisor/Routines/related systems
7. Troubleshooting (common issues + clear fixes)

### 3) Beginner explanation (required)

Each feature must include a plain-language explanation answering:
- **What** is this?
- **How** do I use it?
- **Why** should I use it?
- **What result** should I expect?

Rule: explain as if the reader is using the app for the first time.

## Completion checklist (Definition of Done extension)

A feature is documentation-complete only when all points are true:

- [ ] UI includes `InfoHint` on all key controls
- [ ] SK manual section exists and is beginner-friendly
- [ ] EN manual section exists and is beginner-friendly
- [ ] Manual includes examples and troubleshooting
- [ ] `CHANGELOG.md` contains the documentation/hints update
- [ ] `AUDIT_REPORT.md` reflects the documentation baseline compliance

## Notes for developers

- Keep wording simple and action-oriented.
- Prefer numbered steps over abstract descriptions.
- Include safe defaults where possible.
- Keep terms consistent with UI labels to avoid confusion.
