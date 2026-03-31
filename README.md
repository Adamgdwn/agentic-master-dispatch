# Governed Agent Lab

## Purpose

This repository contains a governed agent project for mission intake, governed child workspaces, sandbox execution, and recommendation workflows. Trading strategy research is one supported domain, but the parent system is designed to be reusable for other research and development tasks.

## Status

- Owner: Adam Goodwin
- Technical lead: Codex pair session
- Risk tier: High
- Production status: Not approved for live deployment or money movement
- Maximum approved autonomy: A2 in sandboxed environments only

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

## Support Model

This project is maintained as a governed agent system. Any material change to model choice, prompts, tool access, autonomy, domain scope, deployment target, or approval flow requires a governance review and a fresh preflight before development continues.
