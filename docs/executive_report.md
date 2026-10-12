# Executive report: AI application portfolio

Generated 2026-10-12 by `cp report` from BigQuery (`spheric-bloom-350617.control_plane`, last export 2026-10-12T13:56:57.039851+00:00).
The registry is a SYNTHETIC sample organization; Support Triage results are real runs.

## Does the deployment create value?

Yes, under the stated assumptions. The configuration in production, classifier_v1, returns $57,270 per month `ASSUMPTION` at 50,000 cases a month `ASSUMPTION`, from measured coverage 86.2% and auto precision 0.944 `MEASURED`.

llm_high_capability_v1 would return $66,957 `ASSUMPTION`, $9,687 more, but it was withheld because it fails the sensitive-intent recall and macro F1 release gates `MEASURED` (docs/release_recommendation.md). The extra value depends on assumed misroute costs; the gates do not.

| Config | Coverage | Auto precision | Model cost per case | Net monthly value |
|---|---|---|---|---|
| llm_high_capability_v1 | 79.4% `MEASURED` | 0.976 `MEASURED` | $0.00107 `MEASURED` | $66,957 `ASSUMPTION` |
| llm_low_cost_v1 | 76.5% `MEASURED` | 0.974 `MEASURED` | $0.00101 `MEASURED` | $62,130 `ASSUMPTION` |
| classifier_v1 | 86.2% `MEASURED` | 0.944 `MEASURED` | $0.00000 `MEASURED` | $57,270 `ASSUMPTION` |

## Portfolio spend and value by platform

| Platform | Apps | Monthly spend | Estimated monthly value |
|---|---|---|---|
| abacus | 9 | $5,960 `FIXTURE` | $35,100 `ASSUMPTION` |
| copilot | 10 | $3,630 `FIXTURE` | $33,100 `ASSUMPTION` |
| managed | 7 | $2,497 `FIXTURE` | $44,000 `ASSUMPTION` |
| custom | 9 | $1,980 `FIXTURE` | $23,300 `ASSUMPTION` |

## Pipeline health

- 5 apps sat more than 30 days in one stage in the latest week `FIXTURE`.
- The slowest stage is evaluation at a median of 12.6 days `FIXTURE`.

## What investment comes next

1. Fix the Support Triage sensitive-intent confusions (card payment versus direct debit) and re-run the release gates before any LLM activation.
2. Use the LLM where it measurably wins: an out-of-scope guard in front of the classifier (it flagged every out-of-domain drift case in the drill).
3. Add a drift-specific monitoring signal; the drill was detected by a 0.0006 margin.
4. Clear the review queue for stalled apps before funding new intake.

Assumptions behind every money figure: configs/business_model.yaml (monthly_volume, manual_handling_minutes, review_minutes, loaded_labor_rate, misroute_cost_standard, misroute_cost_sensitive, infrastructure_monthly).
