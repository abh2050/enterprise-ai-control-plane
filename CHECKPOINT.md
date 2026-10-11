# Checkpoint: M1 Scaffold complete

Plan: ~/.claude/plans/enterprise-ai-control-temporal-magpie.md (M1 to M8, approved). Next: M2 (data and classifier).

## M1 delivered
- Packaging: pyproject.toml, uv.lock, frontend/package-lock.json, Dockerfile, docker-compose.yml (Firestore emulator), Makefile, .env.example
- CI: .github/workflows/ci.yml (ruff, format, mypy, pytest, emulator job, forbidden-dependency scope check, frontend typecheck and build)
- .github/copilot-instructions.md (Section 0 verbatim)
- Backend: settings, contracts (Metric with mandatory provenance), store (memory and Firestore, create-only enforcement, transactions), auth (fixture identity loopback-only, IAP fails closed, role/action matrix), fixtures, api, cli (serve, seed-fixture, milestone stubs), fixture and Vertex-stub providers, Section 3 module stubs
- Frontend: six pages (Portfolio, Pipeline, Flow, AppDetail with seven tabs, Reviews, Incidents), data-mode banner, provenance badges, MetricTile, StatusPill (icon and text), empty states, fixture identity switcher, light/dark/system theme
- Config placeholders: configs/*.yaml, data/manifest.json, imports/example_mapping.yaml

## Exit evidence (2026-10-11)
- Clean checkout, no GCP env or gcloud config: ruff clean, 35 files formatted, mypy clean (26 files), pytest 40 passed, npm typecheck and build pass
- Firestore emulator (docker compose): immutability suite 35 passed
- `cp serve --host 0.0.0.0` with fixture identity exits 1 with a refusal
- Playwright: six pages at 1440 light, 1440 dark, and 390 light all show the FIXTURE banner, no console errors, no horizontal page scroll

## Known gaps carried forward
- The `frontend-design` skill is not installed; design follows the spec's rules directly
- IAP JWT verification is M6; IAP mode rejects every request until then
- Starlette warns that httpx with TestClient is deprecated (harmless)
