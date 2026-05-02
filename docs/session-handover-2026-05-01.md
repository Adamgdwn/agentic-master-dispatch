# Session Handover: 2026-05-01

## Executive Summary

This session moved the project from a single-mission governed lab toward a reusable governed experimentation platform.

The highest-signal changes were:

- added neutral objective framing for broad goals such as "better x with less y"
- added a hard-coded exploratory intake UI that keeps operator hunches separate from the core mission brief
- added Linux launch support for repo-launched use on Pop!_OS and Xubuntu
- added a first-class `project -> mission -> run -> outcome` lifecycle so repeated work is isolated rather than overwritten

The repository remains within the approved `sandbox-only A2` boundary. No live trading, money movement, production deployment, or external write integrations were introduced.

## Governance Status

- Preflight status: passing
- Approved autonomy: `A2`
- Scope status: research, sandbox execution, benchmark evaluation, and reviewed recommendations only
- No connector expansion was enabled by default
- No production secrets, broker access, or real-money pathways were added

Primary governance references:

- `project-control.yaml`
- `docs/tool-permission-matrix.md`
- `docs/human-oversight-rules.md`

## What Changed

### 1. Neutral Objective Framing

The coding loop can now derive an objective profile from broad tradeoff missions instead of forcing a hand-written evaluation target.

Key behavior:

- parses broad mission wording into candidate measurable dimensions
- keeps `static_readiness` intact as the base scoring shape
- layers a limited objective-alignment adjustment on top rather than replacing the underlying loop
- exposes the derived objective profile in results for human inspection

Primary files:

- `src/governed_agent_lab/coding_loop.py`
- `src/governed_agent_lab/agent.py`
- `src/governed_agent_lab/mission_control.py`

### 2. Exploratory Intake GUI

The starting interface is now a hard-coded exploration form rather than a raw mission creator.

The intake asks for:

- mission
- hard constraints
- available environment
- evidence requirements
- operator hunches
- disallowed assumptions
- project name
- project kind

It also previews the agent framing before mission creation so the user can review how the system is interpreting the mission without silently biasing execution.

Primary files:

- `web/index.html`
- `web/app.js`
- `web/style.css`
- `src/governed_agent_lab/server.py`

### 3. Linux Support

The repository now has a Linux-first launcher path suitable for Chuwi/Xubuntu and local Pop!_OS testing.

Added:

- `GovernedAgentLab.sh`
- `scripts/install-linux-launcher.sh`
- safer interpreter selection in `scripts/run-dev.sh`

This is repo-launched Linux support, not a packaged installer format such as `.deb` or AppImage.

### 4. Controlled Lifecycle Model

The repo no longer needs to treat every new mission as work in one mutable child workspace.

Implemented model:

- `Project`: durable container
- `Mission`: governed request against a project
- `Run`: isolated execution workspace per mission instance
- `Outcome`: reviewable result that can be promoted explicitly

Important effects:

- repeated work against one project creates new run workspaces
- old runs remain intact
- coding-optimization recommendations can be recorded as draft outcomes
- future promotion can point a project at a current approved outcome instead of overwriting prior work

Primary files:

- `src/governed_agent_lab/storage.py`
- `src/governed_agent_lab/child_projects.py`
- `src/governed_agent_lab/mission_control.py`
- `src/governed_agent_lab/server.py`
- `web/index.html`
- `web/app.js`

## Storage and Filesystem Shape

### SQLite

Added first-class persistence for:

- `projects`
- `mission_runs`
- `outcomes`

`missions` now also carries:

- `project_id`
- `run_id`

### Workspace Layout

Governed project workspaces now support a durable container plus isolated run folders:

```text
children/<project-slug>/
  workspace/
    goal.md
    registry.md
    outcomes/
      README.md
    runs/
      run-001-<slug>/
        goal.md
        approvals/
        artifacts/
        outputs/
```

The design intent is that exploration writes into a run, not directly into the project root as canonical mutable state.

## API and UI Surface

### API

Relevant additions and changes:

- `/api/exploration/preview`
- `/api/state` now includes `projects`, `runs`, and `outcomes`
- `/api/missions` now accepts `project_name` and `project_kind`

### UI

Relevant additions:

- overview cards for projects, missions, runs, outcomes, approvals, and risk
- mission list entries show project and run lineage
- mission detail shows project container and run workspace separately

## Verification Performed

Completed during this session:

- `bash scripts/governance-preflight.sh`
- full unit/integration suite via repo interpreter

Latest successful result:

- `28 passed in 3.29s`

Note:

- plain `pytest` and `pyenv exec python` were not available from the shell default path
- the working test invocation used `~/.pyenv/versions/agents-env/bin/python -m pytest -q`

## Important Decisions Made

### Keep the Loop Close to the Existing Self-Learning Shape

The user explicitly asked not to drift far from the existing self-learning loop structure. Because of that, the neutral-objective work was added as a narrow extension rather than a redesign.

### Keep the Interface Outcome-Neutral

Operator hunches are stored and shown separately from the mission statement so they do not silently become optimization weights.

### Prefer Explicit Promotion Over Silent Replacement

The lifecycle work intentionally favors immutable run history and explicit outcome promotion over a mutable "latest workspace" model.

## Known Limitations

These are still open:

- no complete UI/API actions yet for `promote`, `archive`, `complete`, or `supersede`
- no packaged Linux distribution artifact yet
- multi-agent execution is still more orchestration/gating than true specialist child execution
- connector configuration exists, but this checkout may still be unconfigured depending on local env
- project current-outcome promotion exists at the storage layer but is not yet exposed cleanly in the UI

## Recommended Next Steps

Suggested order:

1. Add explicit lifecycle actions to the API and UI.
2. Add project history and comparison views for runs and outcomes.
3. Add outcome promotion/review screens so a project can adopt an approved result intentionally.
4. Add archive/supersede semantics for stale runs and outcomes.
5. Package the Linux launcher if a broader install flow is needed.

## Safe Commands for Next Session

Governance:

```bash
bash scripts/governance-preflight.sh
```

Run tests:

```bash
~/.pyenv/versions/agents-env/bin/python -m pytest -q
```

Launch app on Linux:

```bash
./GovernedAgentLab.sh
```

Install Linux desktop launcher:

```bash
bash scripts/install-linux-launcher.sh
```

## Files Most Worth Reading First Next Time

- `src/governed_agent_lab/storage.py`
- `src/governed_agent_lab/mission_control.py`
- `src/governed_agent_lab/child_projects.py`
- `src/governed_agent_lab/server.py`
- `web/app.js`
- `tests/test_mission_control.py`
- `tests/test_coding_loop.py`

## Final State at End of Session

- governance preflight: passing
- tests: passing
- branch at session end: `main`
- lifecycle model: implemented
- exploratory intake: implemented
- Linux launch path: implemented
- project remains sandbox-only and review-gated
