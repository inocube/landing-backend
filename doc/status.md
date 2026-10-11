# Status

Last updated: 2026-10-11

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

- T-002 align AWS access with ADR 0004 (owner task).
- T-003 merged (PR #7): `ci.yml` checks every PR; `deploy.yml` deploys prod on merge to `main` via GitHub
  OIDC (ADR 0012). Function roles carry the `InocubeWebLambdaBoundary` boundary.
- T-004 (in review): `POST /leads` hardened for the website form: CORS for `inocube.sk` and Netlify
  previews (`OPTIONS /leads`), honeypot `website`, stage throttling 5 req/s (burst 10), control characters
  rejected, SES e-mail to the owner per stored lead, 256 MB, 30-day log retention. Needs the owner steps in
  `doc/tasks/T-004-leads-hardening.md` (SES identities, IAM policy updates) before merge.

## Not done yet

- Website form is not connected to the API (frontend `inocube/public` T-002).
- No staging stack, no alarms, no custom domain. No CAPTCHA or duplicate-submission check.
- SES account in the sandbox: notification goes only to verified recipients.

## Known issues

- AWS access differs from ADR 0004: the SSO user has only `InocubeDevAccess`, which can create
  IAM roles. `InocubeWebSamDeploy` and the `inocube-deploy` profile do not exist; the T-001 deploy ran
  with `inocube`. Owner decided to align AWS with the ADR: `doc/tasks/T-002-aws-access-alignment.md`.
- Commit `17193d5 "test direct push"` is in `main` history (from testing branch protection). Harmless.
