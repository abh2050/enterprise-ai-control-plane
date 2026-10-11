# Checkpoint: M3 in progress, waiting on Vertex auth

Plan: ~/.claude/plans/enterprise-ai-control-temporal-magpie.md. No paid model calls made yet.

## M3 built and tested (offline)
- pricing.py: versioned price cards from the official Vertex pricing page (standard table, Global endpoint, <= 200K tier, date-effective prices); refuses to guess
- providers/vertex.py: google-genai client for Vertex (global endpoint), one attempt, 30 s deadline, thinking minimal, usage incl. thinking and cached tokens; any error response releases the reservation (Vertex bills only 200s)
- budget.py: ledger (reserve, send, settle once, unknown hold, release on error, overrun pause and incident), $10 total cap; call_with_budget
- store.py: FileStore for durable local ledger; paid commands refuse the memory store
- triage/llm.py: response schema, parsing, response cache (never pay twice), rate limiter
- triage/llm_eval.py: pilot, dev tuning of agreement threshold (examples excluded), freeze, resumable frozen evaluation
- triage/preflight.py: model access, token counting, structured output; live runs require a pass
- triage/business_model.py and configs/business_model.yaml: net value, breakeven precision, sensitivity (all ASSUMPTION inputs, justified)
- CLI: pricecheck, preflight, pilot, tune, evaluate (LLM), ledger
- docs/decisions.md D11 to D17
- Tests: 136 passed (ledger concurrency, settlement, unknown outcome, overrun, pricing, business model); ruff and mypy clean

## Waiting on the owner
- `gcloud auth login` and `gcloud auth application-default login` (current gcloud token has expired)
- Confirm billing is enabled and the Vertex AI API is on for gen-lang-client-0320912223
- Delete the AI Studio key (pasted in chat); then remove it from .env

## Next steps once authenticated
1. `cp pricecheck --backend vertex`
2. `cp preflight` (two tiny calls)
3. `cp pilot llm_low_cost_v1 --n 50` and the same for llm_high_capability_v1 → projected cost; ask before full runs
4. `cp tune` both configs, `cp evaluate` both, regenerate the experiment report with economics and bootstrap, write docs/business_case.md

## Still to build in M3
- Report: LLM sections, paired bootstrap vs classifier, total cost per correct case, business case doc
