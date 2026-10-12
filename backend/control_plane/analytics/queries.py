"""Parameterized BigQuery analytics (Section 8).

Every query uses named parameters, sets maximum_bytes_billed to 100 MB, and refuses date
ranges longer than 180 days. They power the Flow page, the Portfolio's analytics, and the
executive report.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

DATASET = "control_plane"
MAX_BYTES = 100 * 1024 * 1024
MAX_RANGE_DAYS = 180


class QueryError(ValueError):
    pass


def check_range(start: date, end: date) -> None:
    if end < start:
        raise QueryError("end is before start")
    if (end - start).days > MAX_RANGE_DAYS:
        raise QueryError(f"date ranges are limited to {MAX_RANGE_DAYS} days")


# The stage intervals every flow query starts from: one row per (app, stage stay).
INTERVALS = """
WITH ev AS (
  SELECT e.app_id, e.kind, e.from_stage, e.to_stage, e.event_ts, e.event_date
  FROM `{p}.{d}.app_events` e
  WHERE e.kind IN ('created', 'stage_change', 'stage_change_undone')
),
apps AS (
  SELECT * EXCEPT(rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY app_id ORDER BY event_ts DESC) rn
    FROM `{p}.{d}.app_snapshots`) WHERE rn = 1
),
scoped AS (
  SELECT ev.* FROM ev JOIN apps USING (app_id)
  WHERE @platform = '' OR apps.platform = @platform
),
intervals AS (
  SELECT app_id, to_stage AS stage, event_ts AS entered,
         LEAD(event_ts) OVER (PARTITION BY app_id ORDER BY event_ts) AS exited
  FROM scoped
)
"""


QUERIES: dict[str, str] = {
    # 1. Apps entering, advancing, stalling (> 30 days in one stage), and exiting per week.
    "weekly_flow": INTERVALS
    + """
, weeks AS (
  SELECT week FROM UNNEST(GENERATE_DATE_ARRAY(DATE_TRUNC(@start, WEEK), @end, INTERVAL 1 WEEK)) week
)
SELECT
  week,
  (SELECT COUNT(*) FROM scoped WHERE kind = 'created'
     AND event_date BETWEEN week AND DATE_ADD(week, INTERVAL 6 DAY)) AS entered,
  (SELECT COUNT(*) FROM scoped WHERE kind = 'stage_change'
     AND to_stage NOT IN ('paused', 'retired')
     AND event_date BETWEEN week AND DATE_ADD(week, INTERVAL 6 DAY)) AS advanced,
  (SELECT COUNT(*) FROM intervals
     WHERE stage NOT IN ('monitored', 'paused', 'retired')
       AND TIMESTAMP(DATE_ADD(week, INTERVAL 6 DAY)) >= entered
       AND (exited IS NULL OR exited > TIMESTAMP(DATE_ADD(week, INTERVAL 6 DAY)))
       AND TIMESTAMP_DIFF(TIMESTAMP(DATE_ADD(week, INTERVAL 6 DAY)), entered, DAY) > 30) AS stalled,
  (SELECT COUNT(*) FROM scoped WHERE kind = 'stage_change' AND to_stage = 'retired'
     AND event_date BETWEEN week AND DATE_ADD(week, INTERVAL 6 DAY)) AS exited
FROM weeks ORDER BY week
""",
    # 2. Median days spent in each stage (completed stays).
    "stage_medians": INTERVALS
    + """
SELECT stage,
       APPROX_QUANTILES(TIMESTAMP_DIFF(exited, entered, SECOND) / 86400, 2)[OFFSET(1)] AS median_days,
       COUNT(*) AS stays
FROM intervals
WHERE exited IS NOT NULL AND DATE(entered) BETWEEN @start AND @end
GROUP BY stage ORDER BY median_days DESC
""",
    # 3. Spend and value by app and platform, with provenance.
    "spend_value": """
SELECT platform, app_id, name, monthly_spend_usd, spend_provenance,
       monthly_value_usd, value_provenance
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY app_id ORDER BY event_ts DESC) rn
  FROM `{p}.{d}.app_snapshots` WHERE event_date BETWEEN @start AND @end)
WHERE rn = 1 AND stage != 'retired' AND (@platform = '' OR platform = @platform)
ORDER BY monthly_spend_usd DESC
""",
    # 4. Support Triage monthly net value: measured rates and model cost, assumed labor.
    "triage_net_value": """
WITH latest AS (
  SELECT config_id, ARRAY_AGG(experiment_id ORDER BY event_ts DESC LIMIT 1)[OFFSET(0)] AS experiment_id
  FROM `{p}.{d}.experiment_results`
  WHERE app_id = 'support-triage' AND event_date BETWEEN @start AND @end
  GROUP BY config_id
),
rates AS (
  SELECT r.config_id,
         COUNTIF(route = 'auto') / COUNT(*) AS coverage,
         SAFE_DIVIDE(COUNTIF(route = 'auto' AND correct), COUNTIF(route = 'auto')) AS auto_precision,
         COUNTIF(route = 'review') / COUNT(*) AS review_rate,
         SUM(cost_micros) / COUNT(*) / 1e6 AS model_cost_per_case
  FROM `{p}.{d}.experiment_results` r JOIN latest USING (config_id, experiment_id)
  GROUP BY r.config_id
)
SELECT config_id, coverage, auto_precision, review_rate, model_cost_per_case,
  @volume * coverage * auto_precision * (@manual_minutes / 60 * @labor_rate)
  - @volume * coverage * (1 - auto_precision) * @misroute_cost
  - @volume * review_rate * (@review_minutes / 60 * @labor_rate)
  - @volume * model_cost_per_case - @infrastructure AS net_monthly_value
FROM rates ORDER BY net_monthly_value DESC
""",
    # Flow page: transitions, header metrics, leaderboard, and last export time.
    "transitions": INTERVALS
    + """
SELECT from_stage AS source, to_stage AS target, COUNT(*) AS value
FROM scoped WHERE kind = 'stage_change' AND from_stage IS NOT NULL
  AND event_date BETWEEN @start AND @end
GROUP BY source, target ORDER BY value DESC
""",
    "flow_header": INTERVALS
    + """
, created AS (SELECT app_id, MIN(event_ts) AS created_ts FROM scoped WHERE kind = 'created' GROUP BY app_id),
prod AS (
  SELECT app_id, MIN(event_ts) AS prod_ts FROM scoped
  WHERE kind = 'stage_change' AND to_stage = 'monitored' AND event_date BETWEEN @start AND @end
  GROUP BY app_id)
SELECT
  (SELECT COUNT(*) FROM scoped WHERE kind = 'created' AND event_date BETWEEN @start AND @end) AS apps_entered,
  (SELECT COUNT(*) FROM prod) AS apps_to_production,
  (SELECT APPROX_QUANTILES(TIMESTAMP_DIFF(prod_ts, created_ts, SECOND) / 86400, 2)[OFFSET(1)]
     FROM prod JOIN created USING (app_id)) AS median_days_to_production,
  (SELECT COUNT(*) FROM scoped WHERE kind = 'stage_change' AND from_stage = 'review_gates'
     AND to_stage IN ('evaluation', 'monitored') AND event_date BETWEEN @start AND @end) AS published,
  (SELECT COUNT(*) FROM `{p}.{d}.app_events` WHERE kind = 'gate_reject'
     AND event_date BETWEEN @start AND @end) AS rejected
""",
    "leaderboard": INTERVALS
    + """
, created AS (SELECT app_id, MIN(event_ts) AS created_ts FROM scoped WHERE kind = 'created' GROUP BY app_id),
shipped AS (
  SELECT app_id, MIN(event_ts) AS prod_ts FROM scoped
  WHERE kind = 'stage_change' AND to_stage = 'monitored' GROUP BY app_id)
SELECT COALESCE(apps.owner, 'No owner') AS owner, apps.business_unit,
       COUNT(shipped.app_id) AS shipped,
       APPROX_QUANTILES(TIMESTAMP_DIFF(prod_ts, created_ts, SECOND) / 86400, 2)[OFFSET(1)] AS median_cycle_days,
       SUM(apps.monthly_spend_usd) AS spend
FROM apps LEFT JOIN shipped USING (app_id) LEFT JOIN created USING (app_id)
WHERE @platform = '' OR apps.platform = @platform
GROUP BY owner, business_unit
""",
    "last_export": """
SELECT MAX(exported_at) AS last_export_at FROM `{p}.{d}.export_runs`
WHERE DATE(exported_at) BETWEEN DATE_SUB(@end, INTERVAL 180 DAY) AND @end
""",
}


def run(
    project: str, name: str, start: date, end: date, platform: str = "", **extra: Any
) -> list[dict[str, Any]]:
    from google.cloud import bigquery

    check_range(start, end)
    params: list[Any] = [
        bigquery.ScalarQueryParameter("start", "DATE", start),
        bigquery.ScalarQueryParameter("end", "DATE", end),
        bigquery.ScalarQueryParameter("platform", "STRING", platform),
    ]
    for key, value in extra.items():
        kind = "FLOAT64" if isinstance(value, float | int) else "STRING"
        params.append(bigquery.ScalarQueryParameter(key, kind, value))
    config = bigquery.QueryJobConfig(query_parameters=params, maximum_bytes_billed=MAX_BYTES)
    sql = QUERIES[name].format(p=project, d=DATASET)
    client = bigquery.Client(project=project)
    return [dict(row.items()) for row in client.query(sql, job_config=config).result()]


def flow_from_bigquery(
    project: str, now: datetime, range_days: int, platform: str
) -> dict[str, Any]:
    """The Flow page payload, from BigQuery, in the same shape as the local version."""
    from control_plane.contracts import Provenance
    from control_plane.portfolio import metric

    end = now.date()
    start = end - timedelta(days=range_days)
    prior_start = start - timedelta(days=range_days)
    header = run(project, "flow_header", start, end, platform)[0]
    approvals = header["published"] + header["rejected"]
    weekly = run(project, "weekly_flow", start, end, platform)
    prior = run(project, "weekly_flow", prior_start, start, platform)
    medians = run(project, "stage_medians", end - timedelta(days=MAX_RANGE_DAYS), end, platform)
    board = run(project, "leaderboard", start, end, platform)
    last = run(project, "last_export", start, end)[0]["last_export_at"]

    def table(key: str) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        for row in board:
            g = groups.setdefault(
                row[key] or "Unknown",
                {"name": row[key] or "Unknown", "shipped": 0, "cycles": [], "spend": 0.0},
            )
            g["shipped"] += row["shipped"]
            g["spend"] += row["spend"] or 0.0
            if row["median_cycle_days"] is not None:
                g["cycles"].append(row["median_cycle_days"])
        out = []
        for g in groups.values():
            cycles = sorted(g.pop("cycles"))
            g["median_cycle_days"] = round(cycles[len(cycles) // 2], 1) if cycles else None
            g["spend"] = round(g["spend"], 2)
            out.append(g)
        return sorted(out, key=lambda r: (-r["shipped"], -r["spend"]))

    seed = Provenance.FIXTURE
    return {
        "range_days": range_days,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "header": {
            "apps_entered": metric(header["apps_entered"], "apps", seed, "BigQuery flow_header"),
            "apps_to_production": metric(
                header["apps_to_production"], "apps", seed, "BigQuery flow_header"
            ),
            "median_days_to_production": metric(
                None
                if header["median_days_to_production"] is None
                else round(header["median_days_to_production"], 1),
                "days",
                seed,
                "BigQuery flow_header",
            ),
            "approval_rate": metric(
                round(header["published"] / approvals, 3) if approvals else None,
                "ratio",
                seed,
                f"published / (published + rejected) in range; population {approvals}",
            ),
        },
        "approval_rate_detail": {"published": header["published"], "rejected": header["rejected"]},
        "sankey": run(project, "transitions", start, end, platform),
        "weekly": [
            {
                "week_start": w["week"].isoformat(),
                "in": w["entered"],
                "out": w["exited"],
                "advanced": w["advanced"],
                "stalled": w["stalled"],
            }
            for w in weekly
        ],
        "weekly_prior": [
            {"week_start": w["week"].isoformat(), "in": w["entered"], "out": w["exited"]}
            for w in prior
        ],
        "stage_medians": [
            {"stage": m["stage"], "median_days": round(m["median_days"], 1), "stays": m["stays"]}
            for m in medians
        ],
        "leaderboard": {"owners": table("owner"), "business_units": table("business_unit")},
        "data_source": f"BigQuery {project}.{DATASET}",
        "last_export_at": last.isoformat() if last else None,
    }
