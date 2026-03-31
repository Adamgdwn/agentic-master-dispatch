# Architecture Overview

## Summary

The system operates as a governed boss agent with specialist child workspaces and role plans. It receives a mission, creates an isolated governed child folder, assigns a scoped execution plan, requests approvals when connectors or elevated access are needed, and produces artifacts for human review. Trading strategy work is one supported profile, and no live execution path is currently approved.

## Components

- Boss agent: receives missions, clarifies scope, creates child workspaces, and enforces governance.
- Mission store: persists mission briefs, statuses, approvals, and artifact timelines.
- Approval gate: tracks connector, secret, and scope approvals before a child may proceed.
- Child workspace bootstrapper: creates isolated folders with local governance docs and working files.
- Planner agent: decomposes work into research, data, strategy, review, and promotion stages.
- Research agent: gathers read-only market, strategy, and reference inputs.
- Data agent: prepares large historical datasets and validation slices.
- Strategy agent: defines candidate entries, exits, sizing, and fee assumptions.
- Backtest agent: runs iterative simulations and ranks candidate strategies.
- Risk and review agents: challenge assumptions, drawdowns, leakage, and overfitting.
- Reporting agent: produces recommended strategies, rationale, charts, and experiment evidence.
- Paper-trade agent: isolated runtime for simulated execution and promotion checks.
- Deployment agent: separate future runtime with stronger restrictions and audit controls.
- Governance layer: enforces autonomy, logging, tool permissions, and escalation rules.

## Data Flow

Inputs enter from user missions, local configuration, and approved read-only data sources. The boss agent creates a mission package, opens an isolated child workspace, writes initial artifacts, and assigns role handoffs inside a sandboxed environment. Only reviewed candidates may move into paper trading, and no approved flow exists from this system to real brokerage or exchange execution.

## Dependencies

- Read-only market or reference data providers
- Local backtesting or simulation tooling
- Reporting and chart summarization helpers
- Approved model providers listed in `docs/model-registry.md`
- Governance controls defined in `project-control.yaml` and supporting documents

## Key Decisions

- Current approval boundary stops at mission intake, governed child execution, research, simulation, sandbox execution, and paper-trade preparation.
- The project is classified as high risk because it is an agentic financial system with potential to affect money-related decisions.
- Autonomy is capped at A2 while the system is limited to bounded sandbox actions with logging and human review.
- Child workspaces are isolated from one another and require explicit approval for connector access.
- Strategy generation and deployment are explicitly separated.
- Any future live deployment or broker integration requires reclassification to critical and updated controls before implementation.
