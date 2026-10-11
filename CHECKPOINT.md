# Checkpoint: M3 in progress, paused by the owner to revise the spec (2026-10-11)

Plan: ~/.claude/plans/enterprise-ai-control-temporal-magpie.md. GCP project: spheric-bloom-350617 (billing on, Vertex AI enabled, ADC set with quota project).

## Spend so far
$0.1896 at Vertex list prices (`uv run cp ledger`), all on dev-set pilots and preflight. Cap: $10 total, $5 per app per day.

## Done in M3
- Vertex price card `configs/price_cards/2026-10-11_vertex.yaml` (standard table, Global endpoint, <= 200K tier, cache storage rate)
- Preflight passed for both models (artifacts/preflight/): flash-lite with thinking `minimal`; 3.8 Flash rejects `minimal`, uses `low`. Both 0 thinking tokens.
- Uncached 50-case dev pilots (real Vertex calls):
  - gemini-3.1-flash-lite: 50/50 valid, ~3,557 input tokens, ~42 output, ~1.0 s, $0.00095 per call, projected M3 $2.19
  - gemini-3.8-flash: 50/50 valid, ~3,557 input, ~43 output, ~1.7 s, $0.00283 per call, projected M3 $6.49
  - Projected M3 plus M5 is about $10.20, over the cap. Implicit caching gave 0 cached tokens.
  - Token count vs billed input: flash-lite 6 percent under, 3.8 Flash 20 percent under (structured output overhead); no reservation was exceeded.
- Owner chose explicit context caching to fit the cap. Code is built and tested (cache session, storage charged through the ledger, cached reservations), 138 tests pass.

## Blocker found just before the pause (explicit caching probe, ledgered, $0)
- gemini-3.1-flash-lite: cache create on global returns 403 PERMISSION_DENIED; the model is 404 in us-central1 and us-east5. Explicit caching appears unavailable for it.
- gemini-3.8-flash on global: 400 INVALID_ARGUMENT, "The cached content is of 2836 tokens..." (below the minimum cache size; message truncated). It is 404 in us-central1 and us-east5.
- `configs/triage_configs.yaml` currently sets `context_cache: true` for both LLM configs, so `cp pilot` will fail until this is resolved.

## Options to decide after the spec revision
1. 3.8 Flash: pad or enlarge the static prefix above the minimum (e.g. 2 examples per label) and cache it; flash-lite: run uncached (it is cheap).
2. Drop caching; use a smaller prompt or raise the cap.
3. Vertex batch prediction (50 percent off) for dev tuning and the frozen set.

## Not yet done in M3
- Dev tuning, freezing, and frozen evaluation of both LLM configs
- Experiment report LLM sections, paired bootstrap, total cost per correct case, docs/business_case.md

## Housekeeping for the owner
- Rotate the secrets pasted in chat: AI Studio Gemini key, OpenAI key, Hugging Face token, and HF_CREDENTIALS (printed by mistake)
- After the Gemini key is revoked, remove GEMINI_API_KEY from .env
