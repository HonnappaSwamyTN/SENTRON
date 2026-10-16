# Mandatory Rules for AI Coding Assistants

> **V1 Specification Status: FROZEN**  
> Any AI coding assistant (or human developer using an AI assistant) operating in this repository must strictly adhere to these instructions.

---

## 1. Pre-Execution Protocol

Before modifying or creating any code, the AI assistant must:
1. Read the core documentation:
   - [PROJECT_CONTEXT.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/PROJECT_CONTEXT.md)
   - [ARCHITECTURE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/ARCHITECTURE.md)
   - [MODULE_OWNERSHIP.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/MODULE_OWNERSHIP.md)
   - [FEATURES_AND_ACCEPTANCE.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/FEATURES_AND_ACCEPTANCE.md)
   - [SECURITY_RULES.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/SECURITY_RULES.md)
   - [DECISIONS.md](file:///c:/Users/Honnu/OneDrive/Desktop/kagada/SENTRON/SENTRON_Developer_Starter/DECISIONS.md)
2. Identify the active developer assignment (`Dev1`, `Dev2`, `Dev3`, `Dev4`, or `Integration Owner`).
3. Output a structured pre-work summary:
   - Assigned module and permitted files.
   - Shared interfaces and models consumed/produced.
   - Governing acceptance criteria (from AC-01 to AC-18).
   - Architectural constraints, security boundaries, and risks.
4. **Wait for human confirmation before writing any code.**

---

## 2. Strict Coding Guardrails

1. **Strict File Isolation**: Modify only files within the assigned developer scope. Never edit another developer's files or shared models in `src/sentron/core/models.py` without an agreed RFC.
2. **Zero External AI APIs**: Do not add imports or dependencies for OpenAI, Anthropic, Google GenAI, LangChain, or cloud LLMs. V1 requires 100% deterministic local rules.
3. **No External Network Calls or Cloud Infrastructure**: The core application must function completely offline. Do not introduce network calls, cloud databases, microservices, or external telemetry.
4. **No Secrets in Code or Git**: Never embed real API keys, passwords, or personal credentials in code, tests, or docs. Use synthetic tokens and ensure all log outputs redact detected secrets.
5. **No Automatic Process Termination**: CrashGuard code must NEVER automatically kill, suspend, or pause any process. Implement safe recommendations only.
6. **No Fabricated Telemetry**: In CrashGuard, do not display simulated data as real telemetry. Use genuine `psutil` readings and Windows Event Logs. Handle missing counters gracefully with `unavailable_metrics`.
7. **Safe Mock Executor in Demo**: AgentGuard must use a safe mock executor. Do not implement arbitrary shell commands (`cmd.exe`, `powershell.exe`) or destructive disk operations in demo tools.
8. **Automated Testing & Honest Reporting**: Always create or update `pytest` tests alongside code changes. Run tests and report exact terminal commands and actual results. **Never claim tests passed if they were not run.**
9. **No Speculative Abstractions**: Implement only the frozen V1 requirements. Do not build speculative abstractions for future features.

---

## 3. Standard Teammate AI Prompt Template

Copy and paste this prompt when initiating a task with an AI coding assistant:

```text
"I am assigning you the role of Dev[N] for SENTRON V1 (1=AgentGuard Input Risk, 2=AgentGuard Policy/Executor, 3=CrashGuard Metrics/Risk, 4=CrashGuard Recovery/Evidence, or Integration Owner). 

Read the authoritative documentation in SENTRON_Developer_Starter/. Before generating or editing code:
1. Summarize the product, frozen V1 scope, and architectural boundaries.
2. State my assigned component, owned source files, and owned test files.
3. Identify the shared contracts and data schemas I must use from sentron.core.models.
4. List the exact acceptance criteria (from AC-01 through AC-18) that apply to my task.
5. Confirm that you will NOT add external AI APIs, network calls, automatic process killing, or arbitrary shell execution.

Wait for my explicit approval before modifying any files."
```
