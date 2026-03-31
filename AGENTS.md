# Agent Instructions

Before making substantial code or configuration changes in this repository:

1. run the governance preflight check
2. review `project-control.yaml`
3. review `docs/tool-permission-matrix.md` and `docs/human-oversight-rules.md`
4. confirm the change stays within sandbox-only A2 autonomy
5. proceed only after the project passes preflight or any gaps are explicitly accepted

## Preflight

```bash
bash scripts/governance-preflight.sh
```

## Working Rules

- Treat this repository as a high-risk governed agent project.
- The agent may research strategies and perform bounded sandbox experiments only.
- Live trading, money movement, broker connectivity, and production credentials are prohibited.
- Material changes require review: model change, prompt change, tool-access change, autonomy increase, or deployment-target change.
- Reclassify the project before any move toward real-time or production execution.
