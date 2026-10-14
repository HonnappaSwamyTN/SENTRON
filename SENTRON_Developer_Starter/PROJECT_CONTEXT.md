# Authoritative Project Context
SENTRON is a Windows-first desktop protection app, not primarily a website. An optional website presents the product and labelled simulations; it does not perform actual desktop monitoring.

## Goals
- Help prevent unauthorized AI-agent actions, including actions influenced by malicious instructions in untrusted content.
- Enforce scoped permissions at a controlled action/tool execution boundary.
- Monitor system resources and surface sustained pressure.
- Provide understandable alerts, event history and user-controlled responses.
- Work locally without network access or API keys.

## First-version non-goals
No mandatory cloud LLM/API; no perfect-injection-detection claim; no guarantee of preventing every crash; no automatic process termination/suspension; no claim of intercepting unintegrated agents; no Linux release yet.

## Definitions
AgentGuard protects supported agent actions. CrashGuard monitors resource pressure. The policy engine deterministically returns ALLOW, ASK or BLOCK. The controlled action boundary is the integration through which a proposed action must pass before execution. Untrusted content includes emails, pages, documents, retrieved text and tool output.

## User experience
Plan for startup at sign-in or earlier Windows startup, with background engine separated from dashboard. Ask only when policy requires it.

## API-key-free design
Use local deterministic rules, heuristics, explicit policies and controlled execution. Any future external integration requires a separate decision and is not required in version one.

## Security honesty
Heuristics can miss attacks and flag benign content. Strong enforcement requires controlling execution at the tool boundary. An agent that bypasses that boundary cannot reliably be controlled by SENTRON.
