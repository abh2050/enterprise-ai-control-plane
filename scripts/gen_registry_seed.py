"""Generate data/registry_seed.json: 40 SYNTHETIC apps with 120 days of history.

The app list below (names, owners, platforms, risk, fates, and business problems) was
written by hand for this project. A seeded random generator turns each app's fate into
an event history ending on REFERENCE_DATE. Nothing here describes a real organization.
Support Triage is the one managed app with real evidence (artifacts/); its registry
history is synthetic like the rest.

Run: uv run python scripts/gen_registry_seed.py
"""

from __future__ import annotations

import json
import math
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "registry_seed.json"
SEED = 42
REFERENCE_DATE = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
WINDOW_DAYS = 120

PATH_EXTERNAL = ["intake", "business_case", "review_gates", "monitored"]
PATH_MANAGED = [
    "intake",
    "business_case",
    "review_gates",
    "evaluation",
    "shadow",
    "controlled_activation",
    "monitored",
]
MEDIAN_DAYS = {
    "intake": 6,
    "business_case": 10,
    "review_gates": 12,
    "evaluation": 14,
    "shadow": 10,
    "controlled_activation": 12,
}
REVIEWERS = {
    "reviewer": "reviewer@example.com",
    "governance": "admin@example.com",
    "security": "security@example.com",
}
GATES = {"low": ["reviewer"], "medium": ["governance"], "high": ["governance", "security"]}

OWNERS = [
    ("owner@example.com", True),
    ("owner2@example.com", True),
    ("priya.raman@example.com", True),
    ("daniel.osei@example.com", True),
    ("lena.fischer@example.com", True),
    ("marco.silva@example.com", True),
    ("aisha.khan@example.com", True),
    ("sofia.marin@example.com", True),
    ("kenji.ito@example.com", True),
    ("tom.becker@example.com", False),  # left the company
]

# fate: final stage, or one of: stalled (long time in final stage), rejected_back,
# rejected_retired, retired_after_prod, paused. Extra keys tune the record.
APPS: list[dict[str, Any]] = [
    {
        "id": "support-triage",
        "name": "Support Triage",
        "bu": "Customer Operations",
        "platform": "managed",
        "risk": "high",
        "owner": "owner@example.com",
        "stage": "evaluation",
        "problem": "Agents read every inbound banking support message to decide which queue owns it. "
        "Misrouted fraud and lost-card reports wait in the wrong queue, and routine requests consume "
        "time that specialists need for complex cases. We want routing recommendations that a "
        "person can trust or override.",
    },
    {
        "id": "fraud-alert-summaries",
        "name": "Fraud Alert Summaries",
        "bu": "Risk",
        "platform": "managed",
        "risk": "high",
        "owner": "priya.raman@example.com",
        "stage": "shadow",
        "problem": "Fraud analysts open five systems to understand one alert before deciding whether "
        "to block a card. A short evidence summary per alert could cut review time, but a wrong "
        "summary could hide a real fraud signal, so it must be shadowed before anyone relies on it.",
    },
    {
        "id": "kyc-document-checker",
        "name": "KYC Document Checker",
        "bu": "Compliance",
        "platform": "managed",
        "risk": "high",
        "owner": "daniel.osei@example.com",
        "stage": "controlled_activation",
        "problem": "Onboarding staff check identity documents by hand against a long checklist, which "
        "delays account opening by two days on average. The checker flags missing or inconsistent "
        "fields so staff review only the exceptions, while every final approval stays with a person.",
    },
    {
        "id": "loan-memo-drafter",
        "name": "Loan Memo Drafter",
        "bu": "Lending",
        "platform": "managed",
        "risk": "medium",
        "owner": "lena.fischer@example.com",
        "stage": "evaluation",
        "stalled": True,
        "problem": "Credit officers spend hours turning application data into a standard credit memo. "
        "A first draft assembled from the application and bureau data could save most of that time, "
        "provided the officer edits and signs every memo and no figure is invented by the model.",
    },
    {
        "id": "collections-call-notes",
        "name": "Collections Call Notes",
        "bu": "Collections",
        "platform": "managed",
        "risk": "medium",
        "owner": "marco.silva@example.com",
        "stage": "monitored",
        "spend": 1850,
        "budget": 2500,
        "volume": 22000,
        "problem": "Collections agents write call notes after every conversation, and notes vary so much "
        "that supervisors cannot audit hardship promises consistently. Structured notes generated "
        "from the call transcript give supervisors a consistent record that agents confirm.",
    },
    {
        "id": "complaint-classifier",
        "name": "Complaint Classifier",
        "bu": "Customer Operations",
        "platform": "managed",
        "risk": "high",
        "owner": "aisha.khan@example.com",
        "stage": "paused",
        "paused_from": "controlled_activation",
        "spend": 640,
        "budget": 1200,
        "volume": 9000,
        "problem": "Regulated complaints must be identified and acknowledged within strict deadlines. "
        "Staff currently tag complaints by hand, and late tagging creates regulatory exposure. "
        "Automatic tagging with human confirmation could protect those deadlines across all channels.",
    },
    # Copilot
    {
        "id": "sales-email-drafts",
        "name": "Sales Email Drafts",
        "bu": "Sales",
        "platform": "copilot",
        "risk": "low",
        "owner": "owner@example.com",
        "stage": "monitored",
        "spend": 610,
        "budget": 900,
        "volume": 14000,
        "users": 120,
        "problem": "Relationship managers write similar follow-up emails after every client meeting, "
        "repeating product details and next steps from their notes. Drafts generated from meeting "
        "notes save time while the manager reviews and sends every message personally.",
    },
    {
        "id": "meeting-notes",
        "name": "Meeting Notes",
        "bu": "Operations",
        "platform": "copilot",
        "risk": "low",
        "owner": "owner@example.com",
        "stage": "intake",
        "problem": "Teams lose decisions and action items from internal meetings because nobody owns "
        "the notes. Automatic summaries with owners and due dates would make follow-up reliable and "
        "reduce the number of repeat meetings held only to recover what was already agreed.",
    },
    {
        "id": "policy-search-assistant",
        "name": "Policy Search Assistant",
        "bu": "HR",
        "platform": "copilot",
        "risk": "low",
        "owner": "sofia.marin@example.com",
        "stage": "monitored",
        "spend": 420,
        "budget": 600,
        "volume": 8000,
        "users": 640,
        "dormant": True,
        "problem": "Employees email HR with questions already answered in the policy handbook, and HR "
        "staff spend hours each week pasting links. A search assistant grounded in the handbook "
        "could answer routine questions and route anything unusual to a person.",
    },
    {
        "id": "board-pack-summaries",
        "name": "Board Pack Summaries",
        "bu": "Finance",
        "platform": "copilot",
        "risk": "medium",
        "owner": "kenji.ito@example.com",
        "stage": "review_gates",
        "stalled": True,
        "problem": "Executives receive two hundred page board packs a few days before each meeting and "
        "struggle to find the decisions they must make. Summaries that list decisions, risks, and "
        "changes since the last pack would focus preparation without replacing the source papers.",
    },
    {
        "id": "excel-variance-explainer",
        "name": "Variance Explainer",
        "bu": "Finance",
        "platform": "copilot",
        "risk": "low",
        "owner": "kenji.ito@example.com",
        "stage": "monitored",
        "spend": 980,
        "budget": 900,
        "volume": 3000,
        "users": 85,
        "problem": "Finance analysts explain monthly budget variances line by line in spreadsheets, and "
        "the same explanations recur every month. Suggested explanations drafted from prior months "
        "and ledger detail could shorten close while analysts approve every line.",
    },
    {
        "id": "procurement-intake",
        "name": "Procurement Intake",
        "bu": "Procurement",
        "platform": "copilot",
        "risk": "low",
        "owner": "marco.silva@example.com",
        "stage": "business_case",
        "problem": "Purchase requests arrive as free text emails and procurement staff rewrite each one "
        "into the request form. Converting requests into structured forms would cut handling time "
        "and reduce back and forth with requesters about missing details.",
    },
    {
        "id": "contract-clause-finder",
        "name": "Contract Clause Finder",
        "bu": "Legal",
        "platform": "copilot",
        "risk": "medium",
        "owner": "owner2@example.com",
        "stage": "monitored",
        "spend": 1320,
        "budget": 1500,
        "volume": 2500,
        "users": 40,
        "expires_in": 9,
        "problem": "Lawyers search hundreds of supplier contracts for specific clauses during renewals "
        "and audits. A clause finder that cites the exact page would turn days of manual review into "
        "hours, while lawyers still confirm every clause before relying on it.",
    },
    {
        "id": "it-ticket-summaries",
        "name": "IT Ticket Summaries",
        "bu": "Technology",
        "platform": "copilot",
        "risk": "low",
        "owner": "tom.becker@example.com",
        "expires_in": 8,
        "stage": "monitored",
        "spend": 300,
        "budget": 500,
        "volume": 12000,
        "users": 60,
        "problem": "Service desk engineers inherit long ticket threads and reread them before acting. "
        "A summary of symptoms, steps tried, and current status at the top of each ticket would "
        "shorten handovers between shifts and reduce repeated troubleshooting.",
    },
    {
        "id": "training-quiz-builder",
        "name": "Training Quiz Builder",
        "bu": "HR",
        "platform": "copilot",
        "risk": "low",
        "owner": "sofia.marin@example.com",
        "stage": "retired_after_prod",
        "retire_reason": "Replaced by the learning platform's native tool",
        "problem": "Learning teams write quiz questions for every compliance module by hand, which "
        "delays course releases. Drafting questions from course material would let them publish "
        "modules faster while subject experts review each question for accuracy.",
    },
    {
        "id": "marketing-copy-variants",
        "name": "Marketing Copy Variants",
        "bu": "Marketing",
        "platform": "copilot",
        "risk": "medium",
        "owner": "aisha.khan@example.com",
        "stage": "rejected_retired",
        "retire_reason": "Rejected at review: no approval path for financial promotions",
        "problem": "Marketing produces many variants of campaign copy for testing, and each variant "
        "needs compliance review for financial promotion rules. Generated variants could widen "
        "testing, but only if compliance review capacity keeps pace with the volume.",
    },
    {
        "id": "branch-faq-bot",
        "name": "Branch FAQ Bot",
        "bu": "Retail Banking",
        "platform": "copilot",
        "risk": "medium",
        "owner": "daniel.osei@example.com",
        "stage": "review_gates",
        "problem": "Branch staff call the central help line with product questions while customers "
        "wait at the counter. An internal assistant answering from approved product sheets would "
        "shorten those waits and leave unusual questions to the help line team.",
    },
    {
        "id": "translation-helper",
        "name": "Translation Helper",
        "bu": "Customer Operations",
        "platform": "copilot",
        "risk": "medium",
        "owner": "lena.fischer@example.com",
        "stage": "intake",
        "stalled": True,
        "problem": "Customers write in more than ten languages and messages wait for the few agents who "
        "speak them. Draft translations for agents could shorten waits, but the bank must decide how "
        "translated content is checked before anything reaches a customer.",
    },
    # Abacus
    {
        "id": "credit-risk-narratives",
        "name": "Credit Risk Narratives",
        "bu": "Risk",
        "platform": "abacus",
        "risk": "high",
        "owner": "priya.raman@example.com",
        "expires_in": 13,
        "stage": "monitored",
        "spend": 2100,
        "budget": 2000,
        "volume": 1800,
        "incident": True,
        "problem": "Risk analysts write quarterly narratives explaining movements in portfolio credit "
        "risk. Drafting the narrative from model outputs could save days each quarter, provided "
        "every number in the narrative traces back to the approved risk model.",
    },
    {
        "id": "aml-case-assistant",
        "name": "AML Case Assistant",
        "bu": "Compliance",
        "platform": "abacus",
        "risk": "high",
        "owner": "daniel.osei@example.com",
        "stage": "review_gates",
        "problem": "Investigators assemble anti money laundering cases from transaction histories and "
        "customer records before filing reports. An assistant that gathers evidence and drafts a "
        "timeline could speed investigations while investigators make every filing decision.",
    },
    {
        "id": "pricing-scenario-explorer",
        "name": "Pricing Scenario Explorer",
        "bu": "Retail Banking",
        "platform": "abacus",
        "risk": "medium",
        "owner": "marco.silva@example.com",
        "stage": "business_case",
        "stalled": True,
        "problem": "Product managers model savings rate changes in spreadsheets that take days to update. "
        "A scenario explorer could answer what if questions in minutes, but the team has not yet "
        "agreed how pricing decisions would use its outputs or who validates them.",
    },
    {
        "id": "vendor-risk-questionnaires",
        "name": "Vendor Risk Questionnaires",
        "bu": "Procurement",
        "platform": "abacus",
        "risk": "medium",
        "owner": "owner2@example.com",
        "stage": "monitored",
        "spend": 760,
        "budget": 1000,
        "volume": 900,
        "users": 25,
        "expires_in": 12,
        "problem": "Third party risk staff read long vendor security questionnaires and map answers to "
        "control requirements. Pre mapping answers to controls with citations could halve review "
        "time while staff confirm every finding before it enters the vendor record.",
    },
    {
        "id": "regulatory-change-tracker",
        "name": "Regulatory Change Tracker",
        "bu": "Compliance",
        "platform": "abacus",
        "risk": "medium",
        "owner": "kenji.ito@example.com",
        "stage": "monitored",
        "spend": 880,
        "budget": 1200,
        "volume": 600,
        "users": 30,
        "problem": "Compliance teams monitor regulator publications manually and often learn about "
        "relevant changes late. A tracker that summarizes new publications and maps them to affected "
        "policies would give owners more time to respond to each change.",
    },
    {
        "id": "treasury-cash-forecast",
        "name": "Treasury Cash Forecast Notes",
        "bu": "Finance",
        "platform": "abacus",
        "risk": "medium",
        "owner": None,
        "expires_in": 10,
        "stage": "monitored",
        "spend": 760,
        "budget": 800,
        "volume": 400,
        "users": 12,
        "problem": "Treasury analysts write daily commentary on cash forecasts for senior management. "
        "Drafting the commentary from forecast movements would free analysts for investigation of "
        "unusual movements, which is where their judgment adds the most value.",
    },
    {
        "id": "dispute-letter-drafts",
        "name": "Dispute Letter Drafts",
        "bu": "Customer Operations",
        "platform": "abacus",
        "risk": "high",
        "owner": "aisha.khan@example.com",
        "stage": "rejected_back",
        "reject_reason": "Letters need legal sign-off workflow before review",
        "problem": "Card dispute teams send outcome letters that must cite the scheme rules applied. "
        "Drafted letters could reduce turnaround, but every letter is customer facing and legally "
        "significant, so the review path needs a legal approval step first.",
    },
    {
        "id": "esg-report-assistant",
        "name": "ESG Report Assistant",
        "bu": "Strategy",
        "platform": "abacus",
        "risk": "medium",
        "owner": "sofia.marin@example.com",
        "stage": "retired_after_prod",
        "retire_reason": "Annual report completed; no ongoing need",
        "problem": "The sustainability team compiles the annual ESG report from dozens of internal "
        "sources. An assistant that drafts sections from source data could shorten the reporting "
        "cycle while the team verifies every disclosed figure against its source.",
    },
    {
        "id": "hr-case-summaries",
        "name": "HR Case Summaries",
        "bu": "HR",
        "platform": "abacus",
        "risk": "high",
        "owner": "lena.fischer@example.com",
        "stage": "rejected_retired",
        "retire_reason": "Rejected at review: employee data use not approved",
        "problem": "Employee relations advisers summarize long case files before every meeting. "
        "Automated summaries could save preparation time, but the data is sensitive and the use of "
        "employee case data for model processing needs explicit approval first.",
    },
    {
        "id": "churn-signal-explainer",
        "name": "Churn Signal Explainer",
        "bu": "Retail Banking",
        "platform": "abacus",
        "risk": "medium",
        "owner": "sofia.marin@example.com",
        "stage": "monitored",
        "spend": 1460,
        "budget": 1550,
        "volume": 4000,
        "users": 22,
        "problem": "Retention teams receive churn risk scores without any explanation, so they cannot "
        "tell which customers to call first or what to offer. Plain language explanations of the "
        "drivers behind each score would help them prioritize calls and choose suitable offers.",
    },
    {
        "id": "branch-staffing-insights",
        "name": "Branch Staffing Insights",
        "bu": "Retail Banking",
        "platform": "abacus",
        "risk": "low",
        "owner": "owner@example.com",
        "stage": "intake",
        "problem": "Regional managers set branch staffing from last year's patterns and react late to "
        "changes in footfall. Plain language insights from visit and transaction data could help them "
        "plan rosters weeks ahead and reduce both overtime and long queues.",
    },
    # Custom
    {
        "id": "policy-qa",
        "name": "Policy Q&A",
        "bu": "HR",
        "platform": "custom",
        "risk": "medium",
        "owner": "owner2@example.com",
        "stage": "business_case",
        "problem": "Managers ask HR the same questions about leave, travel, and expenses every week. "
        "A question answering service grounded in current policies would answer most of them "
        "instantly and send the remainder to HR with the context already attached.",
    },
    {
        "id": "contract-summarizer",
        "name": "Contract Summarizer",
        "bu": "Legal",
        "platform": "custom",
        "risk": "medium",
        "owner": "owner2@example.com",
        "stage": "review_gates",
        "stalled": True,
        "problem": "Commercial teams wait days for legal to summarize key terms in incoming contracts. "
        "A summarizer that extracts obligations, renewal dates, and liability caps would speed deals, "
        "with lawyers confirming any term that affects a signing decision.",
    },
    {
        "id": "invoice-extraction",
        "name": "Invoice Extraction",
        "bu": "Finance",
        "platform": "custom",
        "risk": "high",
        "owner": None,
        "stage": "paused",
        "paused_from": "monitored",
        "spend": 120,
        "budget": 500,
        "volume": 5000,
        "problem": "Accounts payable staff key invoice fields into the ledger by hand, which causes late "
        "payments and duplicate entries. Extracting fields automatically with confidence checks could "
        "cut manual keying while staff handle every exception and approval.",
    },
    {
        "id": "atm-incident-triage",
        "name": "ATM Incident Triage",
        "bu": "Technology",
        "platform": "custom",
        "risk": "medium",
        "owner": "marco.silva@example.com",
        "stage": "monitored",
        "spend": 450,
        "budget": 700,
        "volume": 7000,
        "users": 18,
        "problem": "Field engineers receive ATM fault alerts with little context and often travel without "
        "the right parts. Triage that links alerts to likely causes and parts lists could reduce repeat "
        "visits and shorten the time machines stay out of service.",
    },
    {
        "id": "mortgage-doc-qa",
        "name": "Mortgage Document Q&A",
        "bu": "Lending",
        "platform": "managed",
        "risk": "high",
        "owner": "priya.raman@example.com",
        "stage": "review_gates",
        "gates_complete": True,
        "problem": "Mortgage underwriters search long application packs for specific facts such as income "
        "sources and existing commitments. Answers with exact page citations could speed underwriting "
        "while the underwriter remains responsible for every lending decision.",
    },
    {
        "id": "social-sentiment-monitor",
        "name": "Social Sentiment Monitor",
        "bu": "Marketing",
        "platform": "custom",
        "risk": "low",
        "owner": "kenji.ito@example.com",
        "stage": "monitored",
        "spend": 260,
        "budget": 400,
        "volume": 30000,
        "users": 15,
        "incident": True,
        "problem": "Communications staff discover service outages and complaints on social media hours "
        "after customers start posting. Monitoring public posts for spikes in negative sentiment "
        "would alert the team early enough to post updates before complaints escalate.",
    },
    {
        "id": "developer-code-review",
        "name": "Developer Code Review Aid",
        "bu": "Technology",
        "platform": "custom",
        "risk": "medium",
        "owner": "tom.becker@example.com",
        "stage": "business_case",
        "problem": "Engineering teams wait for scarce senior reviewers before merging changes. A review aid "
        "that flags common defects and policy violations would let reviewers focus on design, while "
        "every merge still requires an approving human reviewer.",
    },
    {
        "id": "call-center-qa-scoring",
        "name": "Call Center QA Scoring",
        "bu": "Customer Operations",
        "platform": "custom",
        "risk": "medium",
        "owner": "aisha.khan@example.com",
        "stage": "monitored",
        "spend": 1150,
        "budget": 1300,
        "volume": 15000,
        "users": 35,
        "problem": "Quality teams score about two percent of calls by hand, so coaching relies on a small "
        "sample. Scoring every call against the quality rubric would show trends across all agents, "
        "with quality leads reviewing scores before any coaching conversation.",
    },
    {
        "id": "data-catalog-descriptions",
        "name": "Data Catalog Descriptions",
        "bu": "Data Office",
        "platform": "custom",
        "risk": "low",
        "owner": "daniel.osei@example.com",
        "stage": "intake",
        "problem": "Thousands of tables in the data catalog have no descriptions, so analysts guess at "
        "meanings or ask around. Drafted descriptions from schemas and query history would make data "
        "easier to find, with data owners approving each description they publish.",
    },
    {
        "id": "travel-expense-checker",
        "name": "Travel Expense Checker",
        "bu": "Finance",
        "platform": "custom",
        "risk": "low",
        "owner": "lena.fischer@example.com",
        "stage": "retired_after_prod",
        "retire_reason": "Low usage after policy simplification",
        "problem": "Finance staff check expense claims against travel policy by hand and miss duplicate "
        "receipts. Automated checks that flag likely policy breaches would focus reviewers on the "
        "claims that matter, while approvers keep the final decision on every claim.",
    },
    {
        "id": "wealth-portfolio-letters",
        "name": "Wealth Portfolio Letters",
        "bu": "Wealth",
        "platform": "custom",
        "risk": "high",
        "owner": "priya.raman@example.com",
        "stage": "business_case",
        "problem": "Advisers write quarterly portfolio letters for each client, explaining performance and "
        "market moves. Drafted letters could free advisers for client conversations, but any "
        "statement about performance must be accurate and approved before it is sent.",
    },
]


def lognormal(rng: random.Random, median: float, sigma: float = 0.45) -> float:
    return median * math.exp(rng.gauss(0, sigma))


def _plan(
    app: dict[str, Any], rng: random.Random
) -> tuple[list[tuple[str, float]], dict[str, Any]]:
    """List of (stage, days spent) ending in the current stage, plus final details."""
    path = PATH_MANAGED if app["platform"] == "managed" else PATH_EXTERNAL
    stage = app["stage"]
    info: dict[str, Any] = {}
    if stage in ("retired_after_prod",):
        stops = path[:]
        info.update(final="retired", reason=app["retire_reason"])
    elif stage == "rejected_retired":
        stops = path[: path.index("review_gates") + 1]
        info.update(final="retired", reason=app["retire_reason"], rejected=True)
    elif stage == "rejected_back":
        stops = path[: path.index("review_gates") + 1] + ["business_case"]
        info.update(rejected=True, reject_reason=app["reject_reason"])
    elif stage == "paused":
        stops = path[: path.index(app["paused_from"]) + 1] + ["paused"]
        info.update(paused_from=app["paused_from"])
    else:
        stops = path[: path.index(stage) + 1]
    plan = []
    for s in stops[:-1]:
        plan.append((s, max(1.0, lognormal(rng, MEDIAN_DAYS.get(s, 20)))))
    last = stops[-1]
    if app.get("stalled"):
        current = rng.uniform(42, 70)
    elif last == "monitored":
        current = rng.uniform(15, 60)
    else:
        current = max(1.0, lognormal(rng, MEDIAN_DAYS.get(last, 8)) * rng.uniform(0.2, 0.9))
    plan.append((last, current))
    if info.get("final") == "retired":
        plan.append(("retired", rng.uniform(3, 25)))
    total = sum(d for _, d in plan)
    if total > WINDOW_DAYS - 2:  # compress to fit the 120-day window
        scale = (WINDOW_DAYS - 2) / total
        plan = [(s, d * scale) for s, d in plan]
    return plan, info


def _case(app: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    volume = app.get("volume") or rng.choice([800, 1500, 3000, 6000, 12000])
    cost = app.get("budget") or rng.choice([300, 500, 800, 1200])
    value = round(cost * rng.uniform(1.6, 9.0), -2)
    if app["id"] in ("pricing-scenario-explorer", "translation-helper"):
        value = round(cost * rng.uniform(0.5, 0.9), -2)  # weak cases worth a decision
    return {
        "monthly_volume": {
            "value": volume,
            "unit": "cases per month",
            "provenance": "ASSUMPTION",
            "justification": "Owner estimate at intake (synthetic).",
        },
        "value_hypothesis": "Time saved for the team named in the business problem.",
        "monthly_value_usd": {
            "value": value,
            "unit": "USD per month",
            "provenance": "ASSUMPTION",
            "justification": "Owner estimate of labor saved (synthetic).",
        },
        "monthly_cost_estimate_usd": {
            "value": cost,
            "unit": "USD per month",
            "provenance": "ASSUMPTION",
            "justification": "Owner estimate of license and usage cost (synthetic).",
        },
    }


def build() -> dict[str, Any]:
    rng = random.Random(SEED)
    apps_out, events_out, incidents = [], [], []
    for app in APPS:
        plan, info = _plan(app, rng)
        start = REFERENCE_DATE - timedelta(days=sum(d for _, d in plan))
        t = start
        app_id = app["id"]
        evs: list[dict[str, Any]] = []

        def ev(
            kind: str,
            frm: str | None,
            to: str | None,
            actor: str,
            reason: str,
            when: datetime,
            refs: list[str] | None = None,
        ) -> None:
            evs.append(
                {
                    "event_id": uuid.UUID(int=rng.getrandbits(128)).hex,
                    "app_id": app_id,
                    "kind": kind,
                    "from_stage": frm,
                    "to_stage": to,
                    "actor": actor,
                    "reason": reason,
                    "evidence_refs": refs or [],
                    "created_at": when.isoformat(),
                }
            )

        owner = app["owner"] or "tom.becker@example.com"
        gates: dict[str, Any] = {}
        prev = None
        submitted_by = None
        for i, (stage, days) in enumerate(plan):
            if i == 0:
                ev("created", None, "intake", owner, "Registered at intake", t)
            else:
                actor = owner
                reason = f"Moved to {stage}"
                if stage == "monitored" and prev == "review_gates":
                    actor, reason = "admin@example.com", "Publish decision recorded"
                elif stage in ("controlled_activation", "monitored", "paused", "retired"):
                    actor = "admin@example.com"
                    reason = {
                        "controlled_activation": "Release decision: activate cohort",
                        "monitored": "Activation complete",
                        "paused": "Paused pending investigation",
                        "retired": info.get("reason", "Retired"),
                    }[stage]
                elif stage == "business_case" and prev == "review_gates":
                    actor, reason = "admin@example.com", info["reject_reason"]
                if stage == "review_gates":
                    submitted_by = actor
                ev("stage_change", prev, stage, actor, reason, t)
            # Gate decisions happen while the app waits at review_gates.
            if stage == "review_gates":
                rejected_here = info.get("rejected") and i == next(
                    j for j, (s, _) in enumerate(plan) if s == "review_gates"
                )
                for g in GATES[app["risk"]]:
                    when = t + timedelta(days=days * rng.uniform(0.4, 0.95))
                    left_gates = i < len(plan) - 1
                    if not left_gates and app.get("stalled"):
                        continue  # stalled: still waiting for reviewers
                    if not left_gates and not app.get("gates_complete") and rng.random() < 0.5:
                        continue  # in progress: some gates still pending
                    decision = (
                        "reject" if rejected_here and g == GATES[app["risk"]][-1] else "approve"
                    )
                    review_ref = f"reviews/{app_id}-{g}"
                    ev(
                        f"gate_{decision}",
                        "review_gates",
                        "review_gates",
                        REVIEWERS[g],
                        "Evidence reviewed" if decision == "approve" else "Requirements not met",
                        when,
                        [review_ref],
                    )
                    if decision == "approve":
                        expires = when + timedelta(days=180)
                        if app.get("expires_in"):
                            expires = REFERENCE_DATE + timedelta(days=app["expires_in"])
                        gates[g] = {
                            "gate": g,
                            "approved_by": REVIEWERS[g],
                            "approved_at": when.isoformat(),
                            "expires_at": expires.isoformat(),
                            "review_id": review_ref,
                        }
            prev = stage
            t = t + timedelta(days=days)

        final_stage, final_days = plan[-1]
        entered = REFERENCE_DATE - timedelta(days=final_days)
        live = final_stage in ("monitored", "controlled_activation", "paused")
        spend = app.get("spend", 0) if live else 0
        weeks = 12
        series = []
        for w in range(weeks):
            base = (app.get("volume") or 0) / 4.3
            on = live and (w >= weeks - max(1, int((REFERENCE_DATE - start).days / 7)))
            v = int(base * rng.uniform(0.75, 1.2)) if on else 0
            if app.get("dormant") and w >= weeks - 5:
                v = 0
            series.append(v)
        last_usage = None
        if live and any(series):
            idx = max(i for i, v in enumerate(series) if v)
            last_usage = (REFERENCE_DATE - timedelta(weeks=weeks - 1 - idx)).isoformat()
        record = {
            "app_id": app_id,
            "name": app["name"],
            "owner": app["owner"],
            "business_unit": app["bu"],
            "platform": app["platform"],
            "business_problem": " ".join(app["problem"].split()),
            "risk_tier": app["risk"],
            "stage": final_stage,
            "prior_stage": info.get("paused_from"),
            "paused": final_stage == "paused",
            "version": 1 + len(evs),
            "active_config_id": "llm_low_cost_v1"
            if app_id == "support-triage"
            else (f"{app_id}_v1" if app["platform"] == "managed" else None),
            "monthly_budget_micros": int((app.get("budget") or 500) * 1e6),
            "monthly_spend_micros": int(spend * 1e6),
            "monthly_volume": app.get("volume"),
            "active_users": app.get("users"),
            "usage_series": series,
            "last_usage_at": last_usage,
            "business_case": _case(app, rng) if final_stage != "intake" else None,
            "submitted_by": submitted_by,
            "gates": gates,
            "evidence": {
                "scorecard_passed": final_stage in ("shadow", "controlled_activation", "monitored")
                and app["platform"] == "managed",
                "release_decision": "activate_cohort"
                if final_stage in ("controlled_activation", "monitored")
                and app["platform"] == "managed"
                else None,
            },
            "approvals_expire_at": min((g["expires_at"] for g in gates.values()), default=None),
            "last_decision": evs[-1]["reason"] if evs else None,
            "last_activity_at": evs[-1]["created_at"],
            "stage_entered_at": entered.isoformat(),
            "created_at": start.isoformat(),
            "provenance": "SYNTHETIC",
        }
        apps_out.append(record)
        events_out.extend(evs)
        if app.get("incident"):
            opened = REFERENCE_DATE - timedelta(days=rng.uniform(1, 4))
            incidents.append(
                {
                    "incident_id": f"seed-{app_id}",
                    "app_id": app_id,
                    "signal": "review_rate" if app["platform"] != "abacus" else "cost_per_case",
                    "threshold": 0.25,
                    "observed": round(rng.uniform(0.31, 0.42), 2),
                    "status": "open",
                    "actions": ["owner notified"],
                    "opened_at": opened.isoformat(),
                    "closed_at": None,
                    "provenance": "SYNTHETIC",
                }
            )
    users = [
        {
            "email": e,
            "role": "app_owner",
            "active": active,
            "security_reviewer": False,
            "created_at": (REFERENCE_DATE - timedelta(days=200)).isoformat(),
        }
        for e, active in OWNERS
        if not e.startswith("owner")
    ]
    return {
        "provenance": "SYNTHETIC",
        "description": "40 synthetic AI applications for a fictional bank. Not real data.",
        "reference_date": REFERENCE_DATE.isoformat(),
        "seed": SEED,
        "users": users,
        "apps": apps_out,
        "events": events_out,
        "incidents": incidents,
    }


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, indent=1) + "\n")
    stages: dict[str, int] = {}
    for a in data["apps"]:
        stages[a["stage"]] = stages.get(a["stage"], 0) + 1
    print(
        f"{len(data['apps'])} apps, {len(data['events'])} events, "
        f"{len(data['incidents'])} incidents -> {OUT}"
    )
    print(stages)
