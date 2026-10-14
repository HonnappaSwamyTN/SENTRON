# Acceptance Criteria

## Dev1: input risk
- Accept text and optional source metadata.
- Local heuristics only; no API.
- Return stable flags, explanations and limitations.
- Test suspicious and benign samples.
- No action execution or permission grants.

## Dev2: policy/executor
- Structured action requests.
- ALLOW/ASK/BLOCK plus reason code.
- Approval scoped to operation, target, purpose/task and duration.
- Changed scope requires fresh approval.
- No action runs before policy evaluation.
- Unknown/high-impact actions do not default to ALLOW.
- Mock executor tests all three paths; decisions are auditable.

## Dev3: metrics/risk
- Local CPU, memory, available-memory and process summaries.
- Explicit unavailable values.
- Configurable thresholds, sustained window and cooldown.
- Tests use simulated snapshots.
- Risk output explains evidence without claiming certainty.
- No automatic process control.

## Dev4: recovery
- Ranked recommendations with evidence and uncertainty.
- Initial actions are recommendations/simulations.
- Consequential actions require confirmation.
- Re-measure after actions where possible; record before/after.
- No claim that metrics prove root cause.

## Shared
- Modules use agreed interfaces and can be tested independently.
- No network required for core functions.
- No API keys/secrets.
- Safe error handling; labelled simulated demos.
- Startup integration comes later after privilege/security review.
