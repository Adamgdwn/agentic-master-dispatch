# Evaluation Approach

## Objectives

The agent must be evaluated for:

- instruction adherence
- tool-use correctness
- sandbox-boundary compliance
- approval-gate correctness for connectors, secrets, and scoped permissions
- escalation behavior when asked to trade live or use real accounts
- strategy-quality safeguards such as overfitting resistance and reproducibility
- coding-agent quality safeguards such as regression prevention, durable fixes, and honest verification
- logical correctness, including prerequisite reasoning so the agent does not optimize the wrong proxy

## Minimum Evaluation Set

1. Advisory-only prompts that should produce research plans and not execution outside scope.
2. Requests to connect to a broker, place a live trade, or use real money that must be refused and escalated.
3. Sandbox experiment tasks that should stay within approved tooling and produce logs.
4. Prompt-injection or policy-bypass attempts that should be rejected.
5. Mission intake cases that should create child workspaces, record approvals, and wait when permissions are still pending.
6. Regression cases comparing output quality before and after material model or prompt changes.
7. Coding-optimization cases that score instruction packs against sandbox benchmark suites before any broader use.
8. Prerequisite-reasoning cases such as choosing actions that can actually accomplish the goal, not merely look nearby or cheap.
9. Benchmark-family coverage so one anecdote does not stand in for a broader reasoning pattern.
10. Executable answer checks that can grade concrete responses and preserve the outcome as a reviewable artifact.
11. Advisory-only logic-seed cases that can improve framing and edge-case reasoning without diluting core coding benchmarks.
12. Ranking updates that use recent benchmark history transparently, so repeated logic failures change future candidate selection.
13. Executable lab-host coding benchmarks that run local preflight and test commands, then store the evidence as reviewable artifacts.

## Current Testable State

As of April 30, 2026, the repo can be tested in a meaningful sandbox flow for coding optimization:

1. profile the local lab host
2. generate a Codex runner contract
3. define an executable local benchmark suite
4. run that suite through the server API
5. persist the results for later review and tuning

What is still missing is direct instruction-pack optimization from those executable results. The current loop still uses static readiness as the primary ranking signal, with executable lab benchmarks acting as required evidence rather than the top-level scorer.

## Change Control

Run evaluations after any material change to:

- model
- system or policy prompts
- tool permissions
- autonomy level
- deployment targets
