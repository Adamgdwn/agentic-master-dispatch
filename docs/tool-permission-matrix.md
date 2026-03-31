# Tool Permission Matrix

| Tool | Purpose | Allowed Actions | Prohibited Actions | Approval Required | Notes |
| --- | --- | --- | --- | --- | --- |
| Web research tools | Gather market structure, public strategy references, and documentation | Read-only browsing and retrieval | Logging into accounts, placing trades, or interacting with broker dashboards | Yes for any authenticated access | Public research only under current scope |
| Market data APIs | Read price and reference data for research and backtesting | Read-only queries against approved datasets | Order placement, account actions, or write operations | Yes for new provider adoption | Must remain read-only |
| OpenAI connector | Model-backed analysis through an API key | Approved API calls through `tools/openai_responses.py` | Sharing account passwords or unmanaged browser sessions | Yes | Use `OPENAI_API_KEY` only |
| Perplexity connector | External research and summarization | Approved API calls through `tools/perplexity_search.py` | Raw account sharing or unmanaged browser automation | Yes | Use `PERPLEXITY_API_KEY` only |
| Genspark bridge | Narrow access to browser-only or bridge-only workflows | Calls through a local authenticated bridge | Direct credential sharing with the agent | Yes | Prefer bridge tokens over passwords |
| SQLite read-only connector | Local dataset inspection | Read-only SQL queries through `tools/sqlite_readonly.py` | Schema changes, writes, or using production databases | Yes | Prefer dedicated research snapshots |
| Local sandbox executor | Run strategy code, tests, and simulations inside approved boundaries | Local bounded execution and backtests | Network-enabled live execution, credential use, or unsandboxed runs | Yes for capability expansion | Must produce logs and artifacts |
| Repository file tools | Update code and governance documents in this repo | Read and write within repo scope | Secret insertion, credential storage, or policy bypasses | No for normal repo work | Governed by repo instructions |
| Secret management | Store minimal non-production secrets if later needed for sandbox data providers | Scoped sandbox secrets only | Production, broker, exchange, or wallet credentials | Yes | Prefer API keys, service accounts, and local env vars |

## Control Rules

- Any new tool or integration must be added here before use.
- Approval is required before enabling tools that can affect external systems.
- Do not paste raw passwords, session cookies, or MFA seeds into prompts or checked-in files.
- Prefer API keys, service accounts, or local bridge tokens over full account credentials.
- Tools must fail closed when scope, permissions, or environment are ambiguous.
