# 0006. Protected main, changes only via pull request

- Status: Accepted
- Date: 2026-07-03

## Context
Direct pushes to `main` skip review and will later trigger deploys.

## Decision
A GitHub ruleset on `main`: pull request required, deletions and force pushes blocked. Required approvals: 0
(the owner works alone), but the PR must exist.

## Consequences
Every change is reviewable and linkable. Agents work on branches and open PRs; only the owner merges.
