-- BigQuery schema for the control plane analytics (Section 8).
-- Dataset `control_plane`, location US. Every table is partitioned by event date and
-- clustered by app_id. No table holds raw message text. Each table has a `_staging`
-- twin that the export loads before a MERGE keyed on event_id.

CREATE SCHEMA IF NOT EXISTS control_plane OPTIONS (location = 'US');

CREATE TABLE IF NOT EXISTS control_plane.app_events (
  event_id STRING NOT NULL, app_id STRING, kind STRING, from_stage STRING, to_stage STRING,
  actor STRING, reason STRING, source STRING, event_ts TIMESTAMP NOT NULL, event_date DATE NOT NULL)
PARTITION BY event_date CLUSTER BY app_id;

CREATE TABLE IF NOT EXISTS control_plane.app_snapshots (
  event_id STRING NOT NULL, app_id STRING, name STRING, platform STRING, owner STRING,
  business_unit STRING, stage STRING, risk_tier STRING, monthly_spend_usd FLOAT64,
  spend_provenance STRING, monthly_value_usd FLOAT64, value_provenance STRING,
  provenance STRING, event_ts TIMESTAMP NOT NULL, event_date DATE NOT NULL)
PARTITION BY event_date CLUSTER BY app_id;

CREATE TABLE IF NOT EXISTS control_plane.experiment_results (
  event_id STRING NOT NULL, app_id STRING, experiment_id STRING, config_id STRING,
  case_id STRING, predicted_label STRING, reference_label STRING, route STRING, correct BOOL,
  latency_ms INT64, input_tokens INT64, output_tokens INT64, cost_micros INT64,
  attempt_count INT64, event_ts TIMESTAMP NOT NULL, event_date DATE NOT NULL)
PARTITION BY event_date CLUSTER BY app_id;

CREATE TABLE IF NOT EXISTS control_plane.shadow_results (
  event_id STRING NOT NULL, app_id STRING, run_id STRING, simulated_day INT64, case_id STRING,
  approved_label STRING, candidate_label STRING, approved_route STRING,
  candidate_route STRING, label_agree BOOL, route_agree BOOL, candidate_cost_micros INT64,
  event_ts TIMESTAMP NOT NULL, event_date DATE NOT NULL)
PARTITION BY event_date CLUSTER BY app_id;

CREATE TABLE IF NOT EXISTS control_plane.attempts (
  event_id STRING NOT NULL, app_id STRING, experiment_id STRING, model_id STRING,
  status STRING, reserved_micros INT64, actual_micros INT64, input_tokens INT64,
  output_tokens INT64, cached_tokens INT64, event_ts TIMESTAMP NOT NULL,
  event_date DATE NOT NULL)
PARTITION BY event_date CLUSTER BY app_id;

CREATE TABLE IF NOT EXISTS control_plane.incidents (
  event_id STRING NOT NULL, app_id STRING, signal STRING, threshold FLOAT64,
  observed FLOAT64, status STRING, provenance STRING, opened_at TIMESTAMP,
  closed_at TIMESTAMP, event_ts TIMESTAMP NOT NULL, event_date DATE NOT NULL)
PARTITION BY event_date CLUSTER BY app_id;

CREATE TABLE IF NOT EXISTS control_plane.product_events (
  event_id STRING NOT NULL, app_id STRING, event STRING, role STRING, source_view STRING,
  event_ts TIMESTAMP NOT NULL, event_date DATE NOT NULL)
PARTITION BY event_date CLUSTER BY app_id;

CREATE TABLE IF NOT EXISTS control_plane.export_runs (
  run_id STRING NOT NULL, exported_at TIMESTAMP NOT NULL, counts STRING)
PARTITION BY DATE(exported_at);

-- Staging twins with identical schemas; the export truncates and reloads them each run.
CREATE TABLE IF NOT EXISTS control_plane.app_events_staging LIKE control_plane.app_events;
CREATE TABLE IF NOT EXISTS control_plane.app_snapshots_staging LIKE control_plane.app_snapshots;
CREATE TABLE IF NOT EXISTS control_plane.experiment_results_staging LIKE control_plane.experiment_results;
CREATE TABLE IF NOT EXISTS control_plane.shadow_results_staging LIKE control_plane.shadow_results;
CREATE TABLE IF NOT EXISTS control_plane.attempts_staging LIKE control_plane.attempts;
CREATE TABLE IF NOT EXISTS control_plane.incidents_staging LIKE control_plane.incidents;
CREATE TABLE IF NOT EXISTS control_plane.product_events_staging LIKE control_plane.product_events;
