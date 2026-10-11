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

## D11. Model spend capped at $10 in total (M3)
- The spec defaults are $40 per experiment and $60 in total. The owner capped all LLM spend at $10 across every milestone. The ledger enforces this as the total allowance and per-experiment limit, measured at list prices. The $5 per app per day limit is unchanged.

## D12. Vertex AI on the global endpoint (M3)
- Alternatives: Gemini Developer API free tier (considered, then dropped by the owner); regional Vertex endpoints.
- Reason: results must come from the paid production path the spec names. The Vertex pricing page lists the Global endpoint about 10 percent below regional ("Non-global") prices, so `VERTEX_LOCATION=global`.
- Price cards use the standard table (not Priority or Flex/Batch), the <= 200K input token tier, and the price in effect on the fetch date. Promotional credits-back offers are ignored, so recorded costs are an upper bound.

## D13. Error responses release the reservation (M3)
- The Vertex pricing page states that only requests returning HTTP 200 are charged; 4xx and 5xx responses are not. Any error response therefore releases the reservation. Only a lost response (timeout or dropped connection) is marked unknown and keeps its reservation.

## D14. Thinking set to minimal, output capped at 256 tokens (M3)
- Both models think by default, and thinking tokens bill as output. Triage needs one label and a rationale of at most 300 characters, so thinking is set to its minimum and the output cap (which also sizes each reservation) is 256 tokens, inside the spec's 1,024 maximum. Thinking tokens are measured and reported.

## D15. LLM agreement threshold tuned on dev minus prompt examples (M3)
- Dev rows used as prompt examples are excluded from tuning, since the model sees their answers in the prompt. The target dev auto precision (0.95, ASSUMPTION) matches the classifier's.

## D16. Durable file store for local paid runs (M3)
- The in-memory store forgets between commands, so it cannot enforce a cumulative cap. Paid commands refuse to run on it. A file-locked JSON store (`STORE_BACKEND=file`) keeps the ledger across runs on one machine; Firestore is used once deployed.

## D17. No stand-in model tests of the LLM pipeline (M3)
- At the owner's direction, the LLM pipeline is verified with real Vertex calls (the pilot is the integration check). Ledger tests still simulate timeouts and error responses, which cannot be triggered on demand.
