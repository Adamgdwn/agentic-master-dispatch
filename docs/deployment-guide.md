# Deployment Guide

## Environments

- `dev`: local development and document updates
- `sandbox`: controlled strategy execution and backtesting only

There is no approved `prod` or live trading environment in the current governance scope.

## Deployment Steps

1. Run `bash scripts/governance-preflight.sh`.
2. Review material changes to models, prompts, tools, and autonomy.
3. Validate that the target environment is still sandbox-only.
4. Run the applicable tests and evaluation suite.
5. Record notable changes in `docs/CHANGELOG.md`.

## Rollback

If behavior is unsafe or outside scope, disable execution tooling, revoke any temporary tokens, and return the project to advisory-only operation until reviewed.

## Validation

Validate that:

- no live credentials are present
- no broker or exchange endpoints are configured
- execution remains inside the sandbox
- reporting and logs are produced for each experiment
