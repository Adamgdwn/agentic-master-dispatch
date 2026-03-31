# Human Oversight Rules

## Oversight Boundary

Human approval is mandatory for:

- any action outside research or sandbox experimentation
- any change to autonomy level
- any new tool that can write to external systems
- any use of credentials, secrets, or paid external integrations
- any proposal to connect to brokers, exchanges, wallets, or live execution venues

## Escalation Rules

The agent must stop and escalate when:

- the requested action is ambiguous from a financial-risk perspective
- instructions conflict with the sandbox-only boundary
- the user asks for real-time deployment or automated live execution
- the agent cannot verify that a tool is operating in read-only or sandbox mode

## Review Requirements

- A human reviews recommended strategies before any broader use.
- A human reviews experiment artifacts when performance claims are material.
- A human approves all material changes listed in `project-control.yaml`.
