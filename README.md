# Enterprise AI Control Plane

The control plane helps an AI product owner decide which AI applications should advance, which should stop, and what evidence supports each decision.

> Status: milestone M2. The full README arrives in M7. Console numbers are still FIXTURE placeholders; measured classifier results are in [docs/experiment_report.md](docs/experiment_report.md).

## Local quick start (no cloud credentials)

Requirements: [uv](https://docs.astral.sh/uv/), Node 20 or later, and Docker (optional, for the Firestore emulator).

```bash
uv sync
uv run cp serve                     # API on http://127.0.0.1:8000, in-memory store, fixture identity
cd frontend && npm ci && npm run dev  # console on http://127.0.0.1:5173
```

Pick a fixture identity in the console header. Fixture identity trusts a request header, so the server refuses to bind to anything except localhost and rejects non-loopback clients.

### Firestore emulator

```bash
docker compose up -d firestore
export STORE_BACKEND=firestore FIRESTORE_EMULATOR_HOST=127.0.0.1:8080
uv run cp seed-fixture
uv run cp serve
```

### Checks

```bash
uv run ruff check . && uv run mypy && uv run pytest
FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 uv run pytest   # also runs the emulator variants
cd frontend && npm run typecheck && npm run build
```

## Support Triage data and classifier

Banking77 (PolyAI, CC BY 4.0) is pinned by commit and SHA256 in `data/manifest.json`. Cite: Casanueva et al. (2020), *Efficient Intent Detection with Dual Sentence Encoders*.

```bash
uv run cp data fetch          # download and verify hashes, headers, and the 77 labels
uv run cp data split          # seed 42 splits; split files hold row ids only
uv run cp train               # TF-IDF + logistic regression, calibrated on dev
uv run cp freeze classifier_v1    # tune on dev, then create the policy and config (create only)
uv run cp evaluate classifier_v1  # one run on the frozen set; reruns need --rerun-reason
uv run cp experiment-report
```

## Record immutability

Configs, policies, reviews, and app events are create only. Application code cannot update, overwrite, or delete them, and tests enforce this on both the memory and Firestore backends. A database administrator with direct Firestore access can still alter these records.
