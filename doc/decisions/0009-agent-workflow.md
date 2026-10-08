# 0009. Orchestrator, implementer and architect agents; owner merges

- Status: Accepted
- Date: 2026-10-08

## Context
Implementation is done by AI agents. The owner wants independent review and to keep learning from the work.

## Decision
The orchestrator writes a task in `doc/tasks/`. The implementer agent (Claude Code on the owner's PC)
implements it on a branch and opens a PR that explains the reasoning. The architect agent reviews against the
task, ADRs and `AGENTS.md` and records the verdict in the task. The owner merges and deploys.

## Consequences
Every change has a written spec, an explanation and an independent review. Tasks and docs must be complete
enough for an agent with no chat history.
