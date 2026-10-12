# Checkpoint: M3 LLM configs and economics complete (2026-10-12)

Plan: ~/.claude/plans/enterprise-ai-control-temporal-magpie.md. Console spec: docs/spec/console_spec.md (applies to M4 and M8). Next: M4 (Section 9A design system, then Section 9 pages, lifecycle, registry seed, importer).

## Exit evidence
- All three configs were evaluated on the identical 1,540-case frozen set in the same order (docs/experiment_report.md, all MEASURED):
  - classifier_v1: macro F1 0.913, auto precision 0.944, coverage 86.2%, p95 2 ms, $0 per 1k cases
  - llm_high_capability_v1 (gemini-3.8-flash, cached prefix): macro F1 0.885, auto precision 0.976, coverage 79.4%, p95 3.5 s, $1.07 per 1k cases
  - llm_low_cost_v1 (gemini-3.1-flash-lite): macro F1 0.839, auto precision 0.974, coverage 76.5%, p95 1.4 s, $1.01 per 1k cases
  - Paired bootstrap against the classifier: both LLMs have significantly lower macro F1 and significantly higher auto precision (CIs exclude 0)
  - No config reaches 0.95 recall on all six sensitive intents. The LLMs abstain on 90% of out-of-domain risk cases; the classifier on 0%.
- docs/business_case.md, all ASSUMPTION: net monthly value $66,957 (3.8 Flash), $62,130 (flash-lite), $57,270 (classifier); all pass breakeven plus 0.03.
- Ledger tests pass on memory, file, and the Firestore emulator; 142 tests total; ruff and mypy clean.
- Spend: $4.89 of the $10 cap at Vertex list prices. 9 unknown outcomes (dropped connections) in the 3.8 Flash run were held and never re-called; they route to review.

## Carried into M4 and M5
- M5 signature scenario: sensitive-intent gates fail for every config. Release decisions and cohort economics come from these measured numbers (decisions D6, D7).
- The owner should review the risk suite labels (single rater, AI drafted).
- Rotate the secrets pasted in chat (Gemini, OpenAI, Hugging Face, HF_CREDENTIALS) and remove GEMINI_API_KEY from .env.
- Spec questions for M4 are listed in the plan (two stall definitions, visual baseline approval, 1,000-app load fixture, Higgsfield key name).
