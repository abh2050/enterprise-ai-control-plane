## 0. Operating rules for the coding agent

You are building a portfolio product for an AI product owner. Build milestones in order (Section 12). For each milestone, read the existing files first, list the paths you will change, implement only that milestone, run its exit checks, and report evidence and remaining gaps. Stop and report if a security check or a truthfulness check fails.

Truthfulness rule: Every number that appears in the UI, the README, or any report carries one provenance label. The allowed labels are MEASURED, SIMULATED, FIXTURE, and ASSUMPTION. Never fabricate metrics, prices, interviews, customer quotes, or benchmark results. If a measured result contradicts the intended demo story, the product reports the measured result.

Scope rule: Do not add Kubernetes, Redis, LangChain, LangGraph, vector databases, multi cloud adapters, payment features, or any action that changes data outside this system. The LLM never chooses user identity, role, budget, routing policy, or release state.
