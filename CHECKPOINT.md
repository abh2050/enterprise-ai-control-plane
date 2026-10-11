# Checkpoint: M2 Data and classifier complete

Plan: ~/.claude/plans/enterprise-ai-control-temporal-magpie.md. Next: M3 (Vertex provider, preflight, pricecheck, budget ledger, LLM configs, business model). M3 needs gcloud installed and a GCP project.

## M2 delivered
- triage/dataset.py: pinned Banking77 commit 57ec275d, SHA256 checks, header and 77-label checks, sensitive intent validation, seed-42 splits (dev 770, classifier_train 9226, frozen_eval 1540, shadow_pool 1540 in 14 days of 110)
- Dropped 7 train rows whose text duplicates test.csv (docs/decisions.md D4)
- triage/classifier.py: TF-IDF word and char n-grams plus logistic regression, sigmoid calibration on dev with a frozen estimator
- triage/policy.py: full six-rule deterministic policy and dev threshold tuning
- triage/scorecard.py: all ten Section 6.5 metrics, paired bootstrap
- triage/evaluate.py: train, freeze (create-only policy and config), single frozen run with rerun guard
- triage/llm.py: prompt builder with the leakage guard (model calls are M3)
- triage/report.py and `cp experiment-report` → docs/experiment_report.md
- data/risk_suite.jsonl (60 AUTHORED cases) and data/risk_suite.meta.json (single-rater disclosure)
- docs/decisions.md D1 to D10

## Exit evidence (2026-10-11)
- Classifier scorecard on the frozen set, all MEASURED: macro F1 0.913, auto precision 0.944, coverage 86.2%, p95 2 ms. Four sensitive intents are below 0.95 label recall.
- Leakage test passes: no frozen row in any prompt; dev, train, and test splits share no text; the risk suite shares no text with Banking77
- ruff and mypy clean, pytest 91 passed
- A second `cp freeze` and a second `cp evaluate` both refuse (exit 1)
- No Banking77 text in any committed file

## Known gaps carried forward
- Model binary (27 MB) is gitignored; a fresh clone must `cp train`, and the retrained hash will not match the frozen config (decisions D9; M6 publishes the binary to GCS)
- Total cost per correctly handled case and bootstrap intervals wait for M3
- The risk suite was drafted by Claude; the owner should review its labels
- Experiments are written to artifacts/ files; syncing them into Firestore comes with M3/M4 API work
