# Checkpoint: M5 Shadow, activation, monitoring complete (2026-10-12)

Plan: ~/.claude/plans/enterprise-ai-control-temporal-magpie.md. Console spec: docs/spec/console_spec.md. Next: M6 (GCP deployment with IAP, Cloud Run Jobs, Scheduler, BigQuery export, Flow from BigQuery, executive report). LLM spend: $6.60 of the $10 cap.

## M5 outcome (real results only; the owner declined a FIXTURE demo)
- Gates (MEASURED, frozen set): gemini-3.8-flash 5/10 full, 4/6 for the spec's cohort; gemini-3.1-flash-lite 3/10 full, 3/5 cohort. No activation passes.
- Decisions: flash-lite REJECT (dominated); 3.8 Flash WITHHOLD after shadow (docs/release_recommendation.md).
- Shadow replay (SIMULATED, 14 days, 1,540 cases, $1.65 MEASURED): 85.5% label agreement, classifier 90.2% vs candidate 88.7% accuracy, cohort +$151 net value over 14 days (ASSUMPTION).
- Monitoring on classifier_v1 (production): alert policy frozen from days 1 to 7 before the drill. Drill (40 FIXTURE drift cases, days 10 to 12): incident opened day 10 (0-day delay), automation paused and rolled back to human review, resumed day 13; detection margin only 0.0006 (D32). 3.8 Flash labeled 20/20 out-of-domain drift cases out_of_scope.
- Console: Shadow, Release (recorded releases, decision form, proposals), Monitoring (alert lines, incident marker), working cohort editor with gate previews, routed-case reviews; snapshot strips case text.

## Evidence
- Backend 198 tests; emulator 117; ruff and mypy clean
- Playwright: 10 scenarios pass; 14 visual baselines pass (release baselines re-recorded after the tab changed)
- Artifacts: artifacts/releases, artifacts/shadow, artifacts/monitoring, artifacts/incidents; reports docs/release_recommendation.md and docs/incident_report.md

## Owner to-dos
- Approve visual baselines (frontend/e2e/baselines/)
- Rotate the keys pasted in chat; review risk-suite and drift-case labels
