# Architecture

    Windows startup/sign-in
            |
    Desktop UI (PySide6)
            |
    Shared Core: config, models, event records, SQLite
          /                              \
    AgentGuard                         CrashGuard
    A. Untrusted-input risk             C. Metrics and sustained-risk detection
    B. Policy/approval/executor         D. Recovery recommendations/safe controls

Optional public website is separate and uses labelled sample data. Do not expose a local desktop control API to the public internet.

## Proposed layout
src/sentron/main.py
src/sentron/core/{models.py,config.py,event_bus.py,storage.py}
src/sentron/agentguard/{input_risk.py,policy.py,approval.py,executor.py}
src/sentron/crashguard/{metrics.py,risk.py,recovery.py}
src/sentron/platform/windows/startup.py
src/sentron/ui/main_window.py
tests/{unit,integration,fixtures}/
website/{css,js,assets}/

## Shared action request fields
action_id, agent_id, task_id, tool_name, target, operation, data_classification (optional), untrusted_context_refs (optional), timestamp.

## Shared policy result fields
decision (ALLOW/ASK/BLOCK), reason_code, explanation, required_approval_scope (optional), risk_flags, event_id.

## Shared system snapshot fields
timestamp, cpu_percent, memory_percent, memory_available_bytes, optional disk/temperature values, process summaries (PID/name/CPU/memory), warnings for unavailable metrics.

## Rules
Missing data is not automatically safe. Unknown/high-impact actions should ASK or BLOCK according to policy. Do not use free-form model output as the only enforcement decision. Modules use shared public interfaces, not each other's private internals. Keep OS-specific behaviour in platform adapters. Agree shared models before parallel implementation.
