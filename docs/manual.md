# Manual

## What This Project Is

Governed Agent Lab is a mission console for bounded agent work. It creates governed child workspaces, records approvals and artifacts, runs sandbox-only research or coding-optimization flows, and keeps the work reviewable.

For coding-optimization missions, the system now also profiles the local lab host, generates a Codex runner contract, and defines an executable local benchmark suite before any claim of improvement is accepted.

## How To Work In This Repo

1. Run `bash scripts/governance-preflight.sh`.
2. Review `project-control.yaml`.
3. Review `docs/tool-permission-matrix.md` and `docs/human-oversight-rules.md` if the change touches tools, autonomy, or deployment targets.
4. Confirm the current roadmap and runbook still match reality.
5. Update docs when behavior or operating expectations change.
6. Run the relevant tests before you call the work complete.

## Core Operator Flows

### Mission Intake

1. Open the app.
2. Create a mission with a domain, goal, and constraints.
3. Review the generated child workspace, approvals, and kickoff artifacts.
4. Clear approvals before treating a mission as ready.

### Coding Optimization

1. Use the `Coding Optimization` domain.
2. Review the generated benchmark suite, instruction candidates, lab-host profile, Codex runner contract, and promotion gates.
3. Inspect the current host through `GET /api/lab-host/profile`.
4. Inspect the executable local benchmark suite through `GET /api/lab-host/benchmarks`.
5. Run the suite through `POST /api/lab-host/benchmarks/run`.
6. Review the persisted results before making any claim that the coding process improved.

## Expected Outputs

- working code or deliverables
- current operational documentation
- a maintained roadmap
- reviewable governance records
- persisted benchmark results when coding-optimization experiments are run
- clear operator guidance for Codex or Claude Code style agents

## Operator Notes

Practical rules that help:

- Treat Chuwi or any other lab machine as a sandbox host, not as permission to widen autonomy.
- Prefer narrow benchmark runs first, then broader suites once the local path is stable.
- When behavior changes, update the docs in the same pass instead of leaving the repo half-explained.
- If a benchmark run surprises you, preserve the output and turn the failure into a case or guardrail instead of hand-waving it away.
