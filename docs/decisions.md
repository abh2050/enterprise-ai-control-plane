# Engineering decisions

Each entry records the decision, the alternatives considered, and the reason.

## D1. Firestore emulator through Docker, plus an in-memory store (M1)
- Alternatives: require gcloud or the Firebase CLI locally; emulator only.
- Reason: a fresh clone must run with no cloud credentials or Google tooling. Both backends share one interface, and the immutability tests run against both.

## D2. Fixture identity is loopback only (M1)
- Alternatives: a startup bind check alone.
- Reason: fixture identity trusts a request header. The server refuses non-local binds and also rejects requests from non-loopback clients, in case a proxy forwards traffic.

## D3. Schema extensions beyond Section 4 (M1)
- Apps add business_unit, monthly_spend_micros, active_users, usage_series, business_case, approvals_expire_at, last_decision, prior_stage, and stage_entered_at. `monthly_budget_usd` is stored as `monthly_budget_micros`.
- Reason: the Portfolio page needs these fields, and money must be integer micro dollars.

## D4. Drop train rows that duplicate test text (M2)
- Finding: 6 test sentences appear verbatim in train.csv (7 train rows) at the pinned commit.
- Alternatives: keep them; drop the test rows instead.
- Reason: a development example could place frozen evaluation text in a prompt, and the classifier would train on evaluation text. Dropping train rows keeps the test set and its 40 rows per label intact. The dropped ids are listed in `data/manifest.json`.

## D5. Split files store row ids, not text (M2)
- Reason: the repository never contains evaluation text, so test rows cannot drift into prompts or docs by copy and paste. `cp data fetch` re-downloads and hash-checks the source.

## D6. Deterministic policy implemented in M2 (M2)
- Alternatives: wait for M3 as Section 12 orders.
- Reason: the classifier scorecard needs routes, and routes need the policy. M3 adds the LLM agreement threshold as a new create-only policy; the classifier threshold stays frozen.

## D7. Classifier threshold target is an ASSUMPTION (M2)
- The spec says thresholds are tuned on dev but gives no criterion. The policy picks the threshold that maximizes dev coverage while dev auto precision stays at 0.95 (ASSUMPTION), with at least 50 auto cases.
- Reason: breakeven precision does not exist until the M3 business model. The release gate (breakeven plus 0.03) is checked on the frozen set separately.
- Known bias: dev also calibrates the classifier, so dev precision is optimistic. Measured frozen auto precision (0.944) came in below the dev value (0.950).

## D8. Sigmoid calibration with a frozen estimator (M2)
- Alternatives: isotonic calibration.
- Reason: dev has 10 rows per label, too few for isotonic regression without overfitting.

## D9. Experiment artifacts live in the repository; model binaries do not (M2)
- `artifacts/` holds configs, policies, experiment results (labels and routes, no text), and scorecards, all committed. `artifacts/models/*.pkl` (27 MB) is gitignored; its sha256 is committed and checked before loading.
- Consequence: a fresh clone must run `cp train` to rebuild the model. A retrained binary will not match the committed hash, so it cannot silently stand in for the frozen config. M6 will publish the frozen binary to Cloud Storage.

## D10. Frozen set used once per config (M2)
- `cp evaluate` refuses a second frozen run unless given a reason, which is recorded in `artifacts/experiments/frozen_runs.json`.
