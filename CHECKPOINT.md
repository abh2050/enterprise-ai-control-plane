# Checkpoint: M7 and M8 site complete (2026-10-12)

Live site layout (GitHub Pages from main, root): `index.html` explainer at `/`, the interactive app at `/console/` (real backend in the browser, D38, D40). Next: README (owner will have Codex write it), push to GitHub and enable Pages, owner to-dos below.

## Since M6
- Interactive app: unchanged FastAPI backend in Pyodide; parity test 78 requests; runtime vendored with SHA-256 checks; warms from the explainer; first-visit guide.
- Diagrams: 11 draw.io diagrams with draw.io's own GCP icons (`.claude/skills/gcp-architecture-diagram`, `docs/diagrams/`).
- Videos (Codex, brag + Hyperframes): teaser 21 s, architecture overview 58 s, demo 4:00, README GIF; captions in `media/captions/`.
- Explainer: `index.html` with Higgsfield atmosphere images (`configs/visual_assets.yaml`, `scripts/generate_assets.py`, about 0.04 USD).
- Checks: 240 backend tests; 30 Playwright (6 demo, 10 scenarios, 14 visual).


Plan: ~/.claude/plans/enterprise-ai-control-temporal-magpie.md. Console spec: docs/spec/console_spec.md. Next: M7 (GitHub Pages console with an interactive in-browser demo mode, final docs, provenance audit, snapshot test). LLM spend: about $6.60 of the $10 cap (smoke calls add $0.0001 each).

## M6 outcome
- Deployed to project spheric-bloom-350617 (Cloud Run behind IAP, Firestore, BigQuery `control_plane`, four Cloud Run jobs, two nightly Scheduler jobs, least-privilege service accounts), verified, recorded, and torn down the same day (D36). `scripts/deploy_gcp.sh` rebuilds it; `scripts/iap_oauth.sh` attaches the IAP OAuth client (D35).
- Smoke checks (all passed across the final runs): unauthenticated 302 at the edge; forged header 302 at the edge; deployed backend rejects forged, missing, and fixture assertions; executive viewer authenticated through IAP and cannot write (403); submitter cannot approve own gate (403); live triage call settled its cost; export idempotent (6,400 rows on both runs). Two repeat-run bugs in the smoke script were fixed (D37).
- Owner signed in through the browser (custom OAuth client, Testing status).
- Executive report generated from BigQuery: docs/executive_report.md.
- Teardown: every created resource removed, including the Cloud Build source bucket. Enabled APIs stay on (no charge).

## Raw footage (gitignored, used in M8)
- media/live/: 24 screenshots (12 pages, dark and light, 1920x1080) and 12 dark-mode recordings, captured through IAP (frontend/scripts/capture_live.mjs).
- media/claude-browser/: 100 frames from the Claude in Chrome walkthrough.
- video/Untitled - 1 of 1.mov: the owner's 4 min 32 s screen recording (3010x1512).

## Evidence
- Backend 211 tests; ruff and mypy clean
- Playwright: 10 scenarios and 14 visual baselines (M4/M5)

## Owner to-dos
- Delete the "AI Control Plane IAP" OAuth client (its secret was pasted in chat) and the downloaded client_secret_*.json
- Approve visual baselines (frontend/e2e/baselines/)
- Rotate the keys pasted in chat earlier; review risk-suite and drift-case labels
