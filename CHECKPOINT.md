# Checkpoint: M1 Scaffold (in progress)

Plan: ~/.claude/plans/enterprise-ai-control-temporal-magpie.md (M1 to M8, approved).

## Done in M1
- Packaging: pyproject.toml (Python 3.12, `cp` script, ruff/mypy/pytest config), uv.lock
- .gitignore, .env.example, docker-compose.yml (Firestore emulator image)
- backend/control_plane/settings.py: modes, model defaults, budgets in micros, localhost bind guard
- backend/control_plane/contracts.py: Section 4 models, enums, Metric with provenance
- backend/control_plane/store.py: MemoryStore + FirestoreStore, create-only enforcement, transactions
- backend/control_plane/auth.py: fixture identity (loopback only), IAP fails closed, role/action matrix
- providers/base.py, providers/fixture.py (deterministic, FIXTURE), providers/vertex.py stub
- Section 3 module stubs (registry, budget, monitoring, triage/*, analytics/*)

## Remaining in M1
- fixtures.py (fixture users + apps), api.py, cli.py (serve, seed-fixture, milestone stubs)
- Dockerfile, Makefile, .github/copilot-instructions.md, .github/workflows/ci.yml, README stub
- configs/*.yaml stubs, data/manifest.json placeholder
- Frontend: Vite + React 19 + TS 5 + Tailwind 4 shell, six pages, ProvenanceBadge, DataModeBanner, MetricTile
- Tests: immutability (memory + emulator), bind guard, fixture identity rejection, IAP fail closed, provider determinism
- Exit checks: ruff, mypy, pytest, emulator tests, npm build, six pages render

## Not yet verified
Nothing has been run beyond `uv lock`. No lint, type check, or tests yet.
- Known follow-up: FirestoreStore transaction `create` on an existing create-only doc surfaces Google's AlreadyExists rather than ImmutableRecordError.
