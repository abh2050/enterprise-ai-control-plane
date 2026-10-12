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

## D18. Two examples per label; explicit caching for 3.8 Flash only (M3)
- Vertex explicit caching needs at least 4,096 tokens, and it is unavailable for gemini-3.1-flash-lite (403 on the global endpoint; the model returns 404 in us-central1 and us-east5).
- Both LLM configs use the same prompt with 2 dev examples per label, a 4,850-token static prefix. That prefix is cached for gemini-3.8-flash, where cached input bills at one-tenth. flash-lite runs uncached.
- Effect (MEASURED pilots): 3.8 Flash went from $0.00283 to $0.00107 per call; flash-lite went from $0.00095 to $0.00139 because of the larger prompt. Projected M3 plus M5 fell from about $10.30 to about $7.90.
- Cache storage is charged through the ledger for each cache's full one-hour TTL.

## D19. Per-app daily limit raised to $6 (M3)
- The spec default is $5 per app per day. The owner raised it to $6 so both frozen evaluations could run on the same day. The $10 total cap is unchanged. The ledger applies the configured limit to existing daily budget documents.

## D20. Lost responses become unknown and are never re-called, even on resume (M3)
- During the 3.8 Flash frozen run, Vertex dropped a connection without a response (`RemoteProtocolError`). The provider now treats timeouts, dropped connections, and read errors after send as unknown outcomes. A connection that never opened is treated as unsent and unbilled.
- `cp ledger --reconcile` marks attempts left in `sent` by a crashed process as unknown. Their reservations stay held, because the call may have been billed.
- A resumed run never calls a case again if an earlier attempt for it in the same experiment ended unknown. The case is recorded as unknown and routes to review (Section 7, rule 5).
- Follow-up: a second dropped connection hit the free token-count call, which comes before any reservation. Token counts now retry up to three times. If they still fail, the run pauses cleanly and resumes from saved responses. Billed generate calls are still never retried after an unknown outcome.

## D21. Two stall signals, each where the console spec places it (M4)
- The spec defines stall two ways. The Pipeline card shows a warning after 30 days in a stage. The Portfolio "stalled apps" metric and the Governance Assist stage-stall signal use time in stage above 1.5 times that stage's median. Both rules live in configs/lifecycle.yaml, and each UI label names its rule.
- Stage medians come from completed stays in each stage, from the app event history.

## D22. Design system built from the console spec, without the frontend-design skill (M4)
- The spec asks for the frontend-design skill, which is not installed in this environment. The console follows Section 9A directly (tokens, type scale, spacing, states, motion, responsive rules), which is specific enough to build from.

## D23. Review rejection returns an app to business_case (M4)
- Section 5 lists no backward move. A reviewer or admin can send an app from review_gates back to business_case with a reason, so a rejected submission can be revised instead of only retired.

## D24. Provenance of registry figures (M4)
- Numbers derived from the SYNTHETIC registry seed carry FIXTURE, under a page-level SYNTHETIC banner. Estimated value always carries ASSUMPTION. Model spend from settled ledger attempts carries MEASURED. A figure that mixes sources takes the weakest label.
- The "Monthly model spend" KPI follows the spec literally: settled attempt cost this month (MEASURED, from artifacts/ledger_summary.json). Spend imported from external platforms appears separately, labeled FIXTURE.

## D25. Seed timestamps are anchored to load time (M4)
- The seed history ends on its reference date (2026-10-01). On load, every timestamp shifts so the history ends at the current time, so days in stage, stalls, and expiring approvals look the same whenever the console is opened. The snapshot and visual tests use a fixed clock.
- Production, paused, and retired are steady states, so time spent in them never counts as a stall.

## D26. WCAG adjustments to five spec tokens (M4)
- scripts/contrast.mjs checks every text pair at 4.5:1 and every control boundary at 3:1. Five values failed and were adjusted minimally, keeping hue: light accent #1F6FE0 to #1E6BD8, light status_healthy #0F8A5F to #0E7E57, light status_warning #9A6700 to #966400, and border_strong in both themes (light #C3CEDD to #858C96, dark #34425E to #697388). Each change is commented in frontend/src/styles/tokens.css with the original ratio. Card borders (`border`) are decorative and stay as specified.

## D27. Undo is a server action, limited to the mover's own latest move (M4)
- Some lifecycle moves have no backward transition, so a 10-second undo cannot be an ordinary move. `POST /apps/{id}/undo` restores the stored previous state within 15 seconds (10 in the UI plus network grace), only for the person who made the move, and writes a new `stage_change_undone` event. The original event stays in the append-only history.

## D28. Display clock, fixture reset, and an early snapshot (M4)
- The console renders relative times from a display clock. The snapshot pins it to the export time; visual tests pin it through a local override. Freezing the browser clock in Playwright stalled rendering intermittently, so it is not used.
- `POST /api/fixture/reset` reloads the seed for test isolation. It exists only with fixture identity and the memory store, which are loopback only.
- Scenario 10 needs snapshot mode in M4, so a working read-only snapshot (static JSON from the real API, client-side list filtering) is built now; M7 finishes it for GitHub Pages.

## D29. Mortgage Document Q&A is a managed app in the seed (M4)
- Scenario 1 needs a managed app at review_gates with every approval in place. The seed's Mortgage Document Q&A is managed with both high-risk gates approved.

## D30. Measured gates block every activation; the owner chose a real-only M5 path (M5)
- Frozen-set gates: gemini-3.8-flash passes 5 of 10 as a full candidate and 4 of 6 as the spec's cohort (failing sensitive intents excluded). gemini-3.1-flash-lite passes 3 of 10 and 3 of 5. The cohort still fails macro F1, and routing keys on the classifier's label, so some sensitive cases inherit classifier misses.
- Decisions: reject flash-lite (dominated: less accurate and costlier per call than 3.8 Flash with caching); withhold 3.8 Flash after the shadow replay.
- The spec's signature scenario did not occur. Per Section 6.7, docs/release_recommendation.md describes what happened. The owner declined the optional FIXTURE demo of the pattern, so no constructed candidate exists anywhere.

## D31. Shadow candidate is gemini-3.8-flash; monitoring watches the production classifier (M5)
- 3.8 Flash is the better candidate on every gate and is cheaper per call with its cached prefix, so it is the one replayed in shadow.
- With no activation, production stays on classifier_v1. Monitoring, the alert policy, and the drill apply to classifier_v1. Rollback means pausing automation: every case goes to human review until a shadow check passes every frozen threshold.
- The 40 drift cases (data/drift_cases.jsonl) were written in the build session, labeled FIXTURE, single rater, and are distinct from the risk suite.

## D32. The drill detected drift by a narrow margin (M5)
- Monitoring opened the incident on day 10, the first drift day, but the review rate cleared its frozen threshold by only 0.0006, and no other signal breached. The incident report states this, and it recommends a drift-specific signal (for example the out-of-scope rate) before relying on these alerts. The thresholds were not adjusted after the drill.

## D33. Cloud Run with IAP enabled directly; smoke checks through IAP as service accounts (M6)
- IAP is enabled on the Cloud Run service itself (`--iap`), not through a load balancer, which avoids load balancer cost. The backend still verifies every assertion: ES256 signature against Google's published keys, issuer, audience `/projects/NUMBER/locations/REGION/services/control-plane`, and expiry.
- The project has no Google Cloud organization, so the first IAP enablement goes through the console (OAuth consent screen). The deploy script says so if gcloud cannot enable it.
- Smoke checks authenticate through IAP as dedicated service accounts using self-signed JWTs (IAP's programmatic access for the Google-managed OAuth client). Their roles live in Firestore like any user's: executive_viewer, app_owner, governance_admin.
- Secret Manager is enabled but holds nothing: every component authenticates with its service account, and no key is needed at runtime.

## D34. Additions to the Section 8 BigQuery tables (M6)
- `app_snapshots` (a daily snapshot of each app's stage, spend, and value with provenance) feeds the spend and value query and the Flow leaderboard. `product_events` holds the console analytics events. `export_runs` records each export for the "last export" time. Each target has a `_staging` twin for the MERGE.
- Events are read with a Firestore collection-group query, so the Portfolio makes one events query instead of one per app.

## D35. IAP uses a custom OAuth client in a project without an organization (M6)
- With no organization, the Google-managed OAuth client is unavailable for browser sign-in: IAP answered 502 "Empty Google Account OAuth client ID(s)/secret(s)". The owner created a Web application OAuth client (External audience, Testing status, owner as test user) and `scripts/iap_oauth.sh` attaches it with `gcloud iap settings set`, writing the secret only to a mode-600 temporary file that is deleted on exit.
- The client's redirect URI must be `https://iap.googleapis.com/v1/oauth/clientIds/CLIENT_ID:handleRedirect`; without it Google returns `redirect_uri_mismatch`.
- With the client attached, unauthenticated and forged requests are stopped at the edge with a 302 to Google sign-in.

## D36. GCP is torn down after verification; the public demo is a browser-only sandbox (M6)
- Kept running, the deployment would cost under $1 a month (Cloud Run scales to zero; Firestore, BigQuery, Scheduler and IAP sit in free tiers; the only charge is image storage above 0.5 GB). It was still torn down the same day: IAP admits only allow-listed test users, so hiring managers could not open it, and live LLM calls cannot be offered to the public.
- The public console is the GitHub Pages build. It adds an interactive demo mode (M7): writes apply to an in-browser copy of the SYNTHETIC data, governed by rule tables generated from the same YAML the backend reads, with a test that runs identical lifecycle cases against both implementations. Changes stay in the visitor's browser and reset on demand.
- Vercel with a hosted database was rejected: it needs a new store backend, public writes need abuse protection and resets, and visitors would see the same behavior with more moving parts.
- Live footage (1080p captures through IAP and the owner's screen recording) was taken before teardown for the M8 videos.

## D37. Smoke checks are safe to repeat (M6)
- The triage smoke case ID is unique per run; it was the container PID, which is always the same, so the ledger correctly refused a third attempt on one case. The gate check accepts an app already in review_gates from an earlier run.
- An export check that saw 6,398 then 6,400 rows was traced to two pipeline moves made in the console during the check; a repeat with no concurrent writes held at 6,400 rows on both runs.

## D38. The public console runs the real backend in the browser (M7)
- The GitHub Pages console (`console/`, built by `npm run build:demo`) loads the unchanged FastAPI app in Pyodide inside a Web Worker. Every API request goes to it through `control_plane.browser.Bridge`, an in-process ASGI call. The memory store is seeded with the SYNTHETIC registry and the committed evidence, so each visitor gets a private copy; Reset or a reload restores it.
- Alternatives: a TypeScript re-implementation of the rules (two codebases that drift), a read-only snapshot (visitors cannot act), a hosted backend with a database (D36). Running the same code removes drift by construction.
- Parity is still tested: `tests/test_demo_parity.py` replays 81 requests (every role, rejected and accepted writes, releases, reviews, notes, reset) against the native app and against the Pyodide engine under Node, and requires identical statuses and bodies. It found one real defect: release events were stamped with the wall clock instead of the app clock.
- The runtime is self-hosted. `scripts/vendor_pyodide.mjs` resolves Pyodide 0.29.5 (Python 3.13, Pydantic 2.12.5) plus FastAPI 0.143.0, Starlette 1.7.0 and pydantic-settings 2.15.0 once, freezes a trimmed lockfile, and checks every file's SHA-256. The browser loads nothing from a CDN or PyPI, and the worker checks the backend bundle's SHA-256 before unpacking it. About 20 MB (8 MB compressed), cached after the first visit.
- The engine runs on the snapshot's fixed clock (2026-10-12 12:00 UTC), so the instant first paint from exported JSON and the engine's answers agree. Identity and writes wait for the engine; write controls appear only once it can enforce the rules.
- Changes made for the browser runtime, none of which alter server behavior: fixture identity may bind to `browser` only when `sys.platform == "emscripten"` (there is no listener to forge headers against); FastAPI's threadpool hops run inline; the IAP key cache, `fcntl`, and scikit-learn load only where used.
- What the demo does not include: Banking77 message text (the bundle ships only the 77-name label list, so routed cases show no text, as in the snapshot), live model calls (the provider is the fixture provider; every MEASURED number comes from the committed real runs), and IAP (visitors pick an identity, which is the point of a demo).

## D39. Diagrams are draw.io, generated from coordinates, with draw.io's own GCP icons (M8)
- A first pass with the Python `diagrams` library (Graphviz auto-layout) produced crossing edges, labels on lines, and 7:1 strips. The owner judged it not presentable, and Section 14.2 asks for draw.io, so it was replaced.
- Each diagram is a short Python source that places every element by coordinate (`.claude/skills/gcp-architecture-diagram/scripts/drawio.py`, stdlib only); `docs/diagrams/build.py` writes the `.drawio` and exports a 2x PNG with the draw.io CLI. Generated `.drawio` files stay editable in draw.io.
- Icons, zones, paths, cards, and the title bar use draw.io's own GCP style strings, extracted byte for byte from `Sidebar-GCP2.js` at a pinned commit and SHA-256; a test re-extracts and compares. Identity-Aware Proxy exists only as a product-card icon and is extracted from the card.
- Five canonical icon styles end without a trailing ";" (their base64 ends in "=="); appending label settings directly corrupted the image, which is why Artifact Registry first rendered blank. The builder now always inserts the separator; the canonical string itself is unchanged.
- The skill's conventions (lanes, spacing, orthogonal edges, short labels, background, 2x export) come from the aws-architecture-diagram skill used in the owner's enterprise-rag-aws project (MIT). An eleventh diagram covers the in-browser public demo (D38).
