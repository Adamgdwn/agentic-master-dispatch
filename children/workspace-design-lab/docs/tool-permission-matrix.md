# Tool Permission Matrix

| Tool | Purpose | Allowed Actions | Prohibited Actions | Approval Required | Notes |
| --- | --- | --- | --- | --- | --- |
| Local shell tools | Build and test child workspace code | Read, local writes, local execution | Destructive system actions | No for normal repo work | Stay in repo boundary |
| Network downloads | Fetch dependencies or external tooling | None by default | Any download or install without review | Yes | Add entries before enabling |
| API connectors | Approved SaaS or model APIs | Calls through documented wrappers and env vars | Raw password sharing, unmanaged browser sessions, production writes | Yes | Keep access narrow and auditable |
| External APIs | Goal-specific integrations | Read-only only if documented | Writes, account actions, production access | Yes | Must be added before use |
