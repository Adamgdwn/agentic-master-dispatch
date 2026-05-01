# Runbook

## Purpose

This system supports governed research and sandbox experimentation across approved domains. It is not authorized to place live trades or move money.

## Alerts And Failures

Primary failure conditions:

- sandbox execution escapes approved boundaries
- an integration attempts write access to an external financial system
- prompts or tools drift beyond the registered configuration
- experiment results are missing, incomplete, or inconsistent

## Dependencies

- local sandbox runtime
- approved read-only data sources
- model access listed in `docs/model-registry.md`
- a local benchmark-capable host when testing coding-optimization flows

## Recovery

1. Stop any running experiments.
2. Disable execution-capable tools.
3. Remove or revoke any unexpected credentials.
4. Review the latest changes to prompts, tools, and configs.
5. Review the latest lab-host profile and sandbox benchmark results if the incident involved coding-optimization work.
6. Resume only after governance review and a passing preflight.

## Escalation

Escalate immediately to the project owner if:

- any path toward live trading appears
- a broker, exchange, or wallet integration is proposed
- an experiment acts outside the sandbox
- the agent requests broader autonomy or privileged access
- a lab-host benchmark run writes outside the repo or attempts unexpected external access
