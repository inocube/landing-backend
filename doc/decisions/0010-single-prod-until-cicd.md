# 0010. One prod environment until CI/CD exists

- Status: Accepted
- Date: 2026-10-08

## Context
A staging stack without automated deploys doubles manual work and drifts from prod.

## Decision
Only the `inocube-backend` (prod) stack exists until roadmap phase 3. Staging is created together with the
GitHub Actions pipeline.

## Consequences
Until phase 3, changes are verified locally (`sam local`, DynamoDB Local, unit tests) before the owner deploys.
