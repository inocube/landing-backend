# Tasks

One file per task: `T-xxx-short-name.md`, written by the orchestrator from the current roadmap phase.

## Lifecycle

`ready` → `in-progress` (implementer) → `review` (architect) → `changes-requested` ↔ `review` → `approved`
→ `done` (owner merged). `blocked` if an open question needs the owner.

## Who writes what in a task file

| Section | Written by |
|---|---|
| Goal, Context, Scope, Acceptance criteria, Out of scope | Orchestrator |
| Open questions | Anyone; the owner answers |
| Implementation notes (branch, PR link, deviations) | Implementer |
| Architect review | Architect |

## Running a task (Claude Code on the owner's PC, in this repo)

```text
> Use the implementer agent to implement doc/tasks/T-001-leads-post-api.md
> Use the architect agent to review the PR for T-001
```

Keep finished task files: they are the record of what was asked and why. Keep each under ~120 lines.
