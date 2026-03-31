# Evaluation Approach

## Objectives

The agent must be evaluated for:

- instruction adherence
- tool-use correctness
- sandbox-boundary compliance
- approval-gate correctness for connectors, secrets, and scoped permissions
- escalation behavior when asked to trade live or use real accounts
- strategy-quality safeguards such as overfitting resistance and reproducibility

## Minimum Evaluation Set

1. Advisory-only prompts that should produce research plans and not execution outside scope.
2. Requests to connect to a broker, place a live trade, or use real money that must be refused and escalated.
3. Sandbox experiment tasks that should stay within approved tooling and produce logs.
4. Prompt-injection or policy-bypass attempts that should be rejected.
5. Mission intake cases that should create child workspaces, record approvals, and wait when permissions are still pending.
6. Regression cases comparing output quality before and after material model or prompt changes.

## Change Control

Run evaluations after any material change to:

- model
- system or policy prompts
- tool permissions
- autonomy level
- deployment targets
