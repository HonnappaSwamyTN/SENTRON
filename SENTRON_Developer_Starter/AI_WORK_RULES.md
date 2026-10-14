# AI Coding Rules
Before editing, the coding AI must read PROJECT_CONTEXT.md, ARCHITECTURE.md, MODULE_OWNERSHIP.md, FEATURES_AND_ACCEPTANCE.md, SECURITY_RULES.md and DECISIONS.md; identify the Dev label; summarize task, allowed files, interfaces, acceptance criteria, dependencies and risks; ask about ambiguity; and wait for confirmation.

Rules:
- Work only on assigned module and tests unless authorised.
- Inspect existing code; never overwrite blindly.
- Make small, reviewable changes.
- No external APIs, API keys, cloud inference, telemetry or network calls in v1.
- Never place secrets in code, website JS or Git history.
- Do not change shared models without proposing the impact first.
- Add tests, run them and report exact commands/results honestly.
- Use synthetic data and mock tools; no real emails, private uploads, deletion or destructive commands.
- Do not automatically terminate/suspend processes.
- Keep Windows APIs isolated; explain new dependencies.
- At completion report files changed, behaviour, tests, limitations and integration notes.

## Copy/paste prompt
“I am DevN. Read SENTRON's documentation. First summarize the product, my assigned module, files I may edit, shared interfaces, acceptance criteria, dependencies and risks. Do not edit yet. After I confirm, implement the smallest complete change for my module only, add tests, run them and report exact results. Do not add external APIs, keys, network calls, unrelated features or edits to another developer's files.”
