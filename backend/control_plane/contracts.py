"""Pydantic contracts for every Firestore collection and API payload.

Money is always integer micro dollars. Numbers that reach the UI or a report travel
inside ``Metric`` so they always carry a provenance label.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Provenance(StrEnum):
    MEASURED = "MEASURED"
    SIMULATED = "SIMULATED"
    FIXTURE = "FIXTURE"
    ASSUMPTION = "ASSUMPTION"


class DatasetLabel(StrEnum):
    """Labels for whole datasets, shown as banners rather than per-number badges."""

    SYNTHETIC = "SYNTHETIC"
    AUTHORED = "AUTHORED"


class DataMode(StrEnum):
    LIVE = "LIVE"
    SIMULATED = "SIMULATED"
    FIXTURE = "FIXTURE"


class Role(StrEnum):
    APP_OWNER = "app_owner"
    REVIEWER = "reviewer"
    GOVERNANCE_ADMIN = "governance_admin"
    EXECUTIVE_VIEWER = "executive_viewer"


class Platform(StrEnum):
    ABACUS = "abacus"
    COPILOT = "copilot"
    CUSTOM = "custom"
    MANAGED = "managed"


class RiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Stage(StrEnum):
    INTAKE = "intake"
    BUSINESS_CASE = "business_case"
    REVIEW_GATES = "review_gates"
    EVALUATION = "evaluation"
    SHADOW = "shadow"
    CONTROLLED_ACTIVATION = "controlled_activation"
    MONITORED = "monitored"
    PAUSED = "paused"
    RETIRED = "retired"


class Route(StrEnum):
    AUTO = "auto"
    REVIEW = "review"
    ABSTAIN = "abstain"


class ConfigKind(StrEnum):
    CLASSIFIER = "classifier"
    LLM = "llm"


class ReleaseDecision(StrEnum):
    ACTIVATE_COHORT = "activate_cohort"
    ACTIVATE_FULL = "activate_full"
    WITHHOLD = "withhold"
    REJECT = "reject"


class AttemptStatus(StrEnum):
    RESERVED = "reserved"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class IncidentStatus(StrEnum):
    OPEN = "open"
    MITIGATED = "mitigated"
    CLOSED = "closed"


class ReviewSubject(StrEnum):
    GATE = "gate"
    CASE = "case"


class Health(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Metric(Record):
    """A number that is allowed to reach a person. It cannot exist without provenance."""

    value: float | int | None
    unit: str
    provenance: Provenance
    source: str = Field(description="File, query, or record that holds this number.")


class User(Record):
    email: str
    role: Role
    active: bool = True
    security_reviewer: bool = False
    created_at: datetime


class AssumedValue(Record):
    value: float
    unit: str
    provenance: Literal[Provenance.ASSUMPTION] = Provenance.ASSUMPTION
    justification: str


class BusinessCase(Record):
    monthly_volume: AssumedValue
    value_hypothesis: str
    monthly_value_usd: AssumedValue
    monthly_cost_estimate_usd: AssumedValue


class GateApproval(Record):
    gate: str
    approved_by: str
    approved_at: datetime
    expires_at: datetime
    review_id: str


class Evidence(Record):
    """Pointers to evaluation and release evidence that move requirements check."""

    scorecard_passed: bool = False
    scorecard_ref: str | None = None
    last_passing_eval_at: datetime | None = None
    release_decision: str | None = None  # activate_cohort, activate_full, withhold, reject
    release_ref: str | None = None


class App(Record):
    app_id: str
    name: str
    owner: str | None
    business_unit: str
    platform: Platform
    business_problem: str
    risk_tier: RiskTier
    stage: Stage
    prior_stage: Stage | None = None
    paused: bool = False
    version: int = 1
    active_config_id: str | None = None
    monthly_budget_micros: int = Field(ge=0)
    monthly_spend_micros: int = Field(default=0, ge=0)
    monthly_volume: int | None = None
    active_users: int | None = None
    usage_series: list[int] = Field(default_factory=list)
    last_usage_at: datetime | None = None
    business_case: BusinessCase | None = None
    submitted_by: str | None = None
    gates: dict[str, GateApproval] = Field(default_factory=dict)
    evidence: Evidence = Field(default_factory=Evidence)
    next_review_at: datetime | None = None
    approvals_expire_at: datetime | None = None
    last_decision: str | None = None
    last_activity_at: datetime | None = None
    stage_entered_at: datetime
    created_at: datetime
    provenance: Provenance | DatasetLabel


class AppEvent(Record):
    event_id: str
    app_id: str
    kind: str
    from_stage: Stage | None
    to_stage: Stage | None
    actor: str
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime


class Limits(Record):
    max_input_tokens: int = 8_000
    max_output_tokens: int = 1_024
    deadline_seconds: int = 30
    max_attempts_per_case: int = 2


class Config(Record):
    config_id: str
    app_id: str
    version: int
    kind: ConfigKind
    model_id: str | None
    prompt_text: str | None
    prompt_sha256: str | None
    policy_id: str | None
    limits: Limits = Field(default_factory=Limits)
    price_card: str | None
    created_by: str
    created_at: datetime


class Dataset(Record):
    dataset_id: str
    source_url: str
    source_commit: str
    sha256: str
    split: str
    row_count: int
    seed: int


class Experiment(Record):
    experiment_id: str
    config_id: str
    dataset_id: str
    status: Literal["queued", "running", "finished", "failed"]
    metrics: dict[str, Metric] = Field(default_factory=dict)
    cost_micros: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    provenance: Provenance


class ExperimentResult(Record):
    case_id: str
    predicted_label: str | None
    reference_label: str
    route: Route
    correct: bool
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_micros: int
    attempt_count: int


class Policy(Record):
    policy_id: str
    thresholds: dict[str, float]
    sensitive_intents: list[str]
    eligible_cohort: list[str]
    created_at: datetime


class GateResult(Record):
    gate: str
    threshold: float
    observed: float | None
    passed: bool


class Release(Record):
    release_id: str
    app_id: str
    candidate_config_id: str
    baseline_config_id: str
    policy_id: str
    scorecard: dict[str, Metric]
    gate_results: list[GateResult]
    decision: ReleaseDecision | None = None
    cohort: list[str] = Field(default_factory=list)
    rationale: str | None = None
    proposed_by: str
    decided_by: str | None = None
    decided_at: datetime | None = None


class ShadowRun(Record):
    run_id: str
    authoritative_config_id: str
    candidate_config_id: str
    simulated_day: int


class Budget(Record):
    budget_id: str
    limit_usd_micros: int
    committed_micros: int = 0
    reserved_micros: int = 0


class Attempt(Record):
    attempt_id: str
    app_id: str
    experiment_id: str
    case_id: str
    model_id: str
    status: AttemptStatus
    reserved_micros: int
    budget_ids: list[str]
    actual_micros: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    failure_reason: str | None = None
    created_at: datetime


class Incident(Record):
    incident_id: str
    app_id: str
    signal: str
    threshold: float
    observed: float
    status: IncidentStatus
    actions: list[str] = Field(default_factory=list)
    opened_at: datetime
    closed_at: datetime | None = None
    provenance: Provenance


class Review(Record):
    review_id: str
    subject: ReviewSubject
    subject_id: str
    reviewer: str
    decision: Literal["approve", "reject"]
    reason: str
    created_at: datetime


# API views


class Me(Record):
    email: str
    role: Role


class ModeInfo(Record):
    data_mode: DataMode
    identity_mode: str
    provider_mode: str
    store_backend: str
    dataset_labels: list[DatasetLabel]


class PortfolioSummary(Record):
    total_apps: Metric
    apps_in_production: Metric
    apps_stalled: Metric
    monthly_model_spend_usd: Metric
    estimated_monthly_value_usd: Metric
    open_incidents: Metric
    approvals_waiting: Metric
    apps_by_stage: dict[Stage, Metric]


class AppCard(Record):
    app_id: str
    name: str
    owner: str | None
    business_unit: str
    platform: Platform
    stage: Stage
    risk_tier: RiskTier
    days_in_stage: Metric
    monthly_spend_usd: Metric
    provenance: Provenance | DatasetLabel
