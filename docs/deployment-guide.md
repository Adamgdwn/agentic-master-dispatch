# Deployment Guide

## Environments

- `dev`: local development and document updates
- `sandbox`: controlled strategy execution and backtesting only
- `lab-host-sandbox`: a sandbox lab machine such as Chuwi used for local coding benchmarks, host profiling, and governed Codex runs

There is no approved `prod` or live trading environment in the current governance scope.

## Deployment Steps

1. Run `bash scripts/governance-preflight.sh`.
2. Review material changes to models, prompts, tools, and autonomy.
3. Validate that the target environment is still sandbox-only.
4. Run the applicable tests and evaluation suite.
5. For coding-optimization work, inspect `GET /api/lab-host/profile` and confirm the host profile still matches the intended sandbox machine.
6. For coding-optimization work, list and run the local suite through `GET /api/lab-host/benchmarks` and `POST /api/lab-host/benchmarks/run`.
7. Record notable changes in `docs/CHANGELOG.md`.

## Linux Desktop Notes

- For Linux sandbox hosts such as Xubuntu or Pop!_OS, launch the app with `./GovernedAgentLab.sh`.
- To install a desktop-menu entry, run `bash scripts/install-linux-launcher.sh`.
- The launcher prefers a repo-local virtual environment or active virtual environment before falling back to `python3`.
- If native desktop dependencies are unavailable, the launcher falls back to the browser UI automatically.

## Rollback

If behavior is unsafe or outside scope, disable execution tooling, revoke any temporary tokens, and return the project to advisory-only operation until reviewed.

## Validation

Validate that:

- no live credentials are present
- no broker or exchange endpoints are configured
- execution remains inside the sandbox
- reporting and logs are produced for each experiment
- local benchmark outputs are captured and reviewable when using a lab host
