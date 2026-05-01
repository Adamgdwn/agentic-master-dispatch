# Risk Register

## Current Risk Classification

- Tier: High
- Owner: Adam Goodwin
- Last reviewed: 2026-04-30

## Key Risks

| ID | Risk | Likelihood | Impact | Controls | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | Strategy recommendations are unsound or overfit to historical data. | Medium | High | Require evaluation criteria, out-of-sample testing, and human review before promotion. | Adam Goodwin | Open |
| R-002 | Scope drift leads to unapproved live trading or money movement behavior. | Medium | Critical | Prohibit broker connectivity, prohibit live credentials, cap autonomy at A2, require reclassification before live execution. | Adam Goodwin | Open |
| R-003 | Tool misuse causes unsafe code execution or data exfiltration. | Medium | High | Restrict tools to approved classes, use sandbox-only execution, review tool matrix before changes. | Adam Goodwin | Open |
| R-004 | Prompt or model changes alter behavior without detection. | Medium | High | Maintain model registry, prompt register, and rerun evaluations after material changes. | Adam Goodwin | Open |
| R-005 | Inadequate observability hides unsafe or failed experiments. | Medium | Medium | Require execution logging, experiment reports, and disable procedure in the runbook. | Adam Goodwin | Open |
| R-006 | A lab-host benchmark run is mistaken for approval to widen autonomy or deploy outside the sandbox. | Medium | High | Keep A2 boundaries explicit in the host profile, runner contract, deployment guide, and promotion gates. | Adam Goodwin | Open |
| R-007 | Host-specific tuning makes the coding loop look better on one machine without improving durable coding behavior generally. | Medium | Medium | Treat Chuwi as a lab host, preserve benchmark evidence, and compare host-tuned gains against broader task outcomes before promotion. | Adam Goodwin | Open |
