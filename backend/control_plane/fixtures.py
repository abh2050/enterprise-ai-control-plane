"""Fixture identities and a small FIXTURE app list for local development.

These records exist so the console renders before real data arrives. Every app is
labeled FIXTURE. The 40-app SYNTHETIC registry seed replaces them in M4.
"""

from datetime import UTC, datetime, timedelta

from control_plane.contracts import App, Platform, Provenance, RiskTier, Role, Stage, User
from control_plane.settings import MICROS_PER_USD
from control_plane.store import Store

FIXTURE_USERS: list[tuple[str, Role, bool]] = [
    ("owner@example.com", Role.APP_OWNER, False),
    ("owner2@example.com", Role.APP_OWNER, False),
    ("reviewer@example.com", Role.REVIEWER, False),
    ("security@example.com", Role.REVIEWER, True),
    ("admin@example.com", Role.GOVERNANCE_ADMIN, False),
    ("exec@example.com", Role.EXECUTIVE_VIEWER, False),
]

# (app_id, name, owner, business unit, platform, risk, stage, days in stage,
#  monthly budget usd, monthly spend usd)
_FIXTURE_APPS: list[tuple[str, str, str | None, str, Platform, RiskTier, Stage, int, int, int]] = [
    (
        "support-triage",
        "Support Triage",
        "owner@example.com",
        "Customer Operations",
        Platform.MANAGED,
        RiskTier.HIGH,
        Stage.EVALUATION,
        12,
        150,
        0,
    ),
    (
        "contract-summarizer",
        "Contract Summarizer",
        "owner2@example.com",
        "Legal",
        Platform.ABACUS,
        RiskTier.MEDIUM,
        Stage.REVIEW_GATES,
        41,
        400,
        0,
    ),
    (
        "sales-email-drafts",
        "Sales Email Drafts",
        "owner@example.com",
        "Sales",
        Platform.COPILOT,
        RiskTier.LOW,
        Stage.MONITORED,
        63,
        900,
        610,
    ),
    (
        "policy-qa",
        "Policy Q&A",
        "owner2@example.com",
        "HR",
        Platform.CUSTOM,
        RiskTier.MEDIUM,
        Stage.BUSINESS_CASE,
        5,
        300,
        0,
    ),
    (
        "invoice-extraction",
        "Invoice Extraction",
        None,
        "Finance",
        Platform.CUSTOM,
        RiskTier.HIGH,
        Stage.PAUSED,
        20,
        500,
        120,
    ),
    (
        "meeting-notes",
        "Meeting Notes",
        "owner@example.com",
        "Operations",
        Platform.COPILOT,
        RiskTier.LOW,
        Stage.INTAKE,
        2,
        100,
        0,
    ),
]

_PROBLEM = (
    "Teams spend significant manual effort on this task today. This fixture record "
    "stands in for a real business problem statement so the console can render before "
    "the synthetic registry seed is loaded in a later milestone of the build."
)


def fixture_users(now: datetime) -> list[User]:
    return [
        User(email=email, role=role, security_reviewer=sec, created_at=now)
        for email, role, sec in FIXTURE_USERS
    ]


def fixture_apps(now: datetime) -> list[App]:
    apps = []
    for app_id, name, owner, bu, platform, risk, stage, days, budget, spend in _FIXTURE_APPS:
        entered = now - timedelta(days=days)
        apps.append(
            App(
                app_id=app_id,
                name=name,
                owner=owner,
                business_unit=bu,
                platform=platform,
                business_problem=_PROBLEM,
                risk_tier=risk,
                stage=stage,
                prior_stage=Stage.MONITORED if stage is Stage.PAUSED else None,
                paused=stage is Stage.PAUSED,
                monthly_budget_micros=budget * MICROS_PER_USD,
                monthly_spend_micros=spend * MICROS_PER_USD,
                stage_entered_at=entered,
                created_at=entered - timedelta(days=30),
                provenance=Provenance.FIXTURE,
            )
        )
    return apps


def seed_fixture(store: Store, now: datetime | None = None) -> tuple[int, int]:
    """Write fixture users and apps. Safe to run repeatedly; it overwrites them."""
    now = now or datetime.now(UTC)
    users = fixture_users(now)
    apps = fixture_apps(now)
    for user in users:
        store.set("users", user.email, user.model_dump(mode="json"))
    for app in apps:
        store.set("apps", app.app_id, app.model_dump(mode="json"))
    return len(users), len(apps)
