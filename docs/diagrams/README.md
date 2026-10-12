# Architecture diagrams

Eleven draw.io diagrams with Google's official Google Cloud icons, built from the Python
sources in `src/` by `python3 docs/diagrams/build.py` and checked by the
`gcp-architecture-diagram` skill's validator (`tests/test_gcp_diagrams.py`). Each `.drawio`
opens in draw.io; each `.png` is the 2x export. Edit the source, not the `.drawio`.

| # | Diagram | Scope | Numbers and their source |
|---|---|---|---|
| 01 | [System overview](01_system_overview.png) | What `scripts/deploy_gcp.sh` creates: IAP, the Cloud Run console and four jobs, Scheduler, Firestore, BigQuery, Cloud Storage, Vertex AI, Secret Manager | Schedules 02:00 and 02:30 UTC: `scripts/deploy_gcp.sh` |
| 02 | [Triage request path](02_triage_request_path.png) | One case through token counting, the budget reservation, the three configs, the decision policy, and settlement | 8,000 input and 256 output tokens, 30 s, 2 attempts: `configs/triage_configs.yaml`, `backend/control_plane/contracts.py`; policy rules: `backend/control_plane/triage/policy.py` |
| 03 | [Registry lifecycle](03_registry_lifecycle.png) | The nine stages, gate rules by risk tier, and the managed versus external branch | 30 words, 180 days: `configs/lifecycle.yaml` |
| 04 | [Identity and access](04_identity_and_access.png) | IAP assertion checks, roles from Firestore, and every service account grant | Grants: `scripts/deploy_gcp.sh`; checks: `backend/control_plane/iap.py`, docs/decisions.md D33 and D35 |
| 05 | [Budget ledger](05_budget_ledger.png) | Reserve, send, settle, unknown hold, release, overrun pause, reconcile | $6 per app per day, $10 experiment and total: docs/decisions.md D11 and D19; the 1.10 factor: `backend/control_plane/budget.py` |
| 06 | [Experiment to release](06_experiment_to_release.png) | Dev tuning, frozen evaluation, scorecard gates, shadow replay, the recorded decision | 1,540 cases: `docs/experiment_report.md`; 3 of 10, 5 of 10, 4 of 6, 85.5%, $1.65, 14 days: `docs/release_recommendation.md`; gate thresholds: `configs/release_gates.yaml` |
| 07 | [Analytics pipeline](07_analytics_pipeline.png) | JSONL export, staging load, MERGE deduplication, report queries | 100 MB and 180 days: `backend/control_plane/analytics/queries.py`; idempotent export: docs/decisions.md D37 |
| 08 | [Monitoring and incident](08_monitoring_and_incident.png) | Daily signals, the frozen alert policy, detection, pause, rollback, resume | 0.2177 against 0.2172, day 10, day 13, 0.0006, 40 cases: `docs/incident_report.md`; days 1 to 7 and 10%: `configs/release_gates.yaml` |
| 09 | [Delivery](09_delivery.png) | CI checks, Cloud Build, Artifact Registry, deploy, smoke checks, teardown, GitHub Pages | Smoke checks: `scripts/smoke_gcp.sh` |
| 10 | [Local development](10_local_development.png) | Fixture identity, store backends, the Firestore emulator, the fixture provider | none |
| 11 | [Public demo](11_public_demo.png) | The GitHub Pages console running the unchanged backend in the browser | 78 requests: `tests/fixtures/demo_parity.json`, docs/decisions.md D38 |
