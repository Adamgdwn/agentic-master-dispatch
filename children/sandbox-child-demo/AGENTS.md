# Agent Instructions

Before making substantial code or configuration changes in this repository:

1. run the governance preflight check
2. review `project-control.yaml`
3. review `docs/tool-permission-matrix.md` and `docs/human-oversight-rules.md`
4. stay within sandbox-only A2 autonomy unless governance is explicitly updated
5. document any tool, model, or prompt changes before broadening the child agent

## Preflight

```bash
bash scripts/governance-preflight.sh
```
