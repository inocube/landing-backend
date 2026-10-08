# Status

Last updated: 2026-10-08

## Works today

- SAM stack `inocube-backend` deployed in `eu-central-1` (prod), `GET /health` returns 200.
- DynamoDB table `inocube-leads` with GSI1 (by date) and GSI2 (by e-mail); all four access patterns
  verified manually against DynamoDB Local and AWS.
- SSO login with two profiles; `main` protected by a ruleset (PR required).

## In progress

- T-001 POST /leads (roadmap phase 2): task written, not started.

## Not done yet

- Website form is not connected to the API (it still posts to a FormSubmit placeholder).
- No CI/CD, no automated deploy; no alarms; no custom domain.

## Known issues

- Commit `17193d5 "test direct push"` is in `main` history (from testing branch protection). Harmless.
- Owner's local clone was on the merged branch `feat/faza-1-dynamodb`; switch to `main` before new work.
