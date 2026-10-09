# Status

Last updated: 2026-10-08

## Works today

- SAM stack `inocube-backend` deployed in `eu-central-1` (prod).
  - `GET /health` returns 200.
  - `POST /leads` (T-001) deployed 2026-10-08:
    `https://i6r0knhf3m.execute-api.eu-central-1.amazonaws.com/Prod/leads`.
    Smoke test: invalid body returns 400. No valid test lead was sent to prod.
    Cold start: init 643 ms, 88 of 128 MB memory used.
- DynamoDB table `inocube-leads` with GSI1 (by date) and GSI2 (by e-mail).
- SSO login; `main` protected by a ruleset (PR required, `Approved` label gate).

## In progress

- T-002 align AWS access with ADR 0004 (owner task). Next: phase 2b hardening tasks (see roadmap).

## Not done yet

- Website form is not connected to the API (the form on the Astro site is disabled).
- `POST /leads` is public with no throttling, CORS or honeypot (architect finding, phase 2b).
- No CI/CD, no alarms, no log retention, no custom domain.

## Known issues

- AWS access differs from ADR 0004: the SSO user has only `InocubeDevAccess`, which can create
  IAM roles. `InocubeSamDeploy` and the `inocube-deploy` profile do not exist; the T-001 deploy ran
  with `inocube`. Owner decided to align AWS with the ADR: `doc/tasks/T-002-aws-access-alignment.md`.
- Commit `17193d5 "test direct push"` is in `main` history (from testing branch protection). Harmless.
