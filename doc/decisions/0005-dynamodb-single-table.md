# 0005. DynamoDB single-table design for leads

- Status: Accepted
- Date: 2026-07-04

## Context
Access patterns: save lead, get by ID, list newest first, find by e-mail. Traffic: a few leads per day.

## Decision
One table `inocube-leads`, on-demand billing, generic keys `PK/SK`, `GSI1PK/GSI1SK` (all leads by date),
`GSI2PK/GSI2SK` (by e-mail). Key formats are listed in `AGENTS.md`.

## Consequences
All patterns are Queries, never Scans. GSI1 uses a single partition value (`LEAD`), a hot partition at
high write rates; accepted at current volume. If writes approach hundreds per second, add write sharding.
