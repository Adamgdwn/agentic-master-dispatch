# Governed Agent Lab

## Purpose

This repository contains a governed agent project for mission intake, governed child workspaces, sandbox execution, and recommendation workflows. Trading strategy research is one supported domain, but the parent system is designed to be reusable for other research and development tasks.

## Status

- Owner: Adam Goodwin
- Technical lead: Codex pair session
- Risk tier: High
- Production status: Not approved for live deployment or money movement
- Maximum approved autonomy: A2 in sandboxed environments only

## Recent Improvements

- The app now behaves like a boss-agent mission console instead of a simple task runner.
- Missions create isolated child workspaces automatically under `children/`.
- Mission state, approvals, and artifacts are persisted in SQLite for reviewable workflows.
- The GUI now centers on mission intake, mission queue, approval cards, connector readiness, and mission detail.
- A desktop launcher and app icon are in place for a cleaner local experience.
- The repository is now published at `https://github.com/Adamgdwn/agentic-master-dispatch`.
- Governance preflight passes and the current unit test suite passes locally.

## Build Snapshot

- Product direction: a boss agent that receives a mission, opens a governed child workspace, and controls approvals before execution.
- Current state: mission intake, child bootstrap, approval records, artifact tracking, and a cleaner GUI are implemented.
- Not implemented yet: real post-approval child execution, per-child connector loading, and packaged native desktop distribution.
- Repo URL: `https://github.com/Adamgdwn/agentic-master-dispatch`

## Quick Start

1. Run the governance preflight:

   ```bash
   bash scripts/governance-preflight.sh
   ```

2. Launch the desktop app with the executable file:

   ```bash
   ./GovernedAgentLab.command
   ```

3. The launcher now opens a native desktop window when `pywebview` is installed. If the desktop shell is unavailable, it falls back to your browser at `http://127.0.0.1:8000`.
4. Install or refresh desktop support with a Python that has `pip` available, for example `~/.pyenv/versions/3.12.1/bin/python -m pip install -r requirements.txt`.
5. Configure connectors with `config/secrets.example.env` and `config/tool-profiles.toml` before enabling external tools.
6. Use the boss-agent interface to define a mission, set constraints, request connectors, and create a governed child workspace automatically.
7. Do not add broker access, exchange credentials, or live execution without reclassification and updated approvals.

## Documentation

- `docs/architecture.md`
- `docs/deployment-guide.md`
- `docs/runbook.md`
- `docs/CHANGELOG.md`
- `docs/risks/risk-register.md`
- `docs/agent-inventory.md`
- `docs/model-registry.md`
- `docs/prompt-register.md`
- `docs/tool-permission-matrix.md`
- `docs/evaluation-approach.md`
- `docs/human-oversight-rules.md`

## Next Actions For Codex

1. Add real child execution flows after approval, not just mission packaging and child bootstrap.
2. Implement per-child connector enablement so approved missions can load only the env vars and tools they were granted.
3. Add mission actions such as `start`, `pause`, `archive`, and `complete`, with clearer lifecycle transitions in the UI.
4. Improve the desktop experience further by packaging the launcher into a more native app bundle.
5. Add richer artifact generation and logs so each child returns execution evidence, not just kickoff files.
6. Update model and prompt registries once the real connector-backed execution path is finalized.

## Resume Here Later

When work resumes, start with the first unfinished product milestone:

1. Wire one real child execution flow end to end after approvals clear.
2. Scope connector access per child instead of only recording approval intent.
3. Test the workflow with one concrete mission in the GUI and refine the UX from that real path.

## Next Actions For Adam

1. Decide which connectors should be enabled first for real usage, especially model, research, and browser-adjacent tools.
2. Provide API keys or local env values only for approved connectors in `config/secrets.local.env`, not in committed files.
3. Decide whether the first real child workflow should be `research-and-development` or `trading-strategy`.
4. Define the first real-world mission you want the boss agent to handle end to end.
5. Review and approve any material changes before broker connectivity, paid data, or live-like execution are introduced.
6. Start sharing the public repo and README so the project has a clearer public-facing narrative.

## Support Model

This project is maintained as a governed agent system. Any material change to model choice, prompts, tool access, autonomy, domain scope, deployment target, or approval flow requires a governance review and a fresh preflight before development continues.
