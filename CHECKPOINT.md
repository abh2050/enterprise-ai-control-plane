# Checkpoint: M4 Registry and console complete (2026-10-12)

Plan: ~/.claude/plans/enterprise-ai-control-temporal-magpie.md. Console spec: docs/spec/console_spec.md. Next: M5 (shadow replay, cohort activation, release decisions, monitoring, incidents, drill). LLM spend so far $4.89 of the $10 cap; M5's shadow replay is projected at about $2.10.

## M4 delivered
- Backend: lifecycle rules (configs/lifecycle.yaml), registry state machine with version checks (409), per-destination requirements (422 before mutation), gate approvals (submitter can never approve), undo, Governance Assist scoring and actions, governance notes (idempotent, 15-minute edit, soft delete), CSV importer (all or nothing), portfolio, catalog, and Flow aggregates, CSV export with formula escaping, product analytics events (no text), settings and roles, snapshot export
- Seed: 40 SYNTHETIC apps with 180 events and 2 incidents, authored in-session (scripts/gen_registry_seed.py), anchored to load time
- Frontend: Section 9A design system (tokens WCAG-checked; five values adjusted, D26), shell with responsive sidebar and sticky top bar, every component state, lazy charts; pages Portfolio, Pipeline (drag, keyboard, conflict drawer, undo), Flow, Applications plus app drawer with notes, App Detail (7 tabs, 3 for external apps), Reviews, Incidents, Settings; header band and empty-state slots for Section 9B
- Snapshot mode (basic; M7 finishes it): `npm run build:snapshot`

## Exit evidence
- All ten end-to-end scenarios pass (frontend/e2e/scenarios.spec.ts)
- Lifecycle tests pass on memory, file, and the Firestore emulator
- Visual validation: 14 baselines (7 pages x 2 themes, 1440x900, fixed seed and clock), 42 of 42 comparisons pass across 3 repeats. Baselines await owner approval: frontend/e2e/baselines/
- Backend 193 tests; ruff and mypy clean; tokens pass WCAG 2.2 AA; initial route JS 74.8 KB gzipped; Portfolio API p95 66 ms for 1,000 apps (in process)

## Known gaps
- Intermittent multi-minute Playwright stalls happen while the Mac sleeps or throttles; with caffeinate the full suite passed 3 of 3. `npm run e2e` now uses caffeinate.
- The Release decision form, Shadow, and Monitoring tabs show honest empty states until M5. Routed-case reviews also arrive in M5.
- Flow reads the local event store until the M6 BigQuery export. Product events are stored locally until M6.
- Higgsfield visuals are placeholders until M8.
- Still owed by the owner: rotate the pasted keys; review risk-suite labels; approve visual baselines.
