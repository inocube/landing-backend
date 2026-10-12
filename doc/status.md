# Status

Last updated: 2026-10-12

## Works today

- SAM stack `inocube-backend` deployed in `eu-central-1` (prod).
  - `GET /health` returns 200.
  - `POST /leads` (T-001) deployed 2026-10-08:
    `https://i6r0knhf3m.execute-api.eu-central-1.amazonaws.com/Prod/leads`.
    Smoke test: invalid body returns 400. No valid test lead was sent to prod.
    Cold start: init 643 ms, 88 of 128 MB memory used.
- DynamoDB table `inocube-leads` with GSI1 (by date) and GSI2 (by e-mail).
- SSO login; `main` protected by a ruleset (PR required, `Approved` label gate).
- T-004 (PR #8, deployed 2026-10-12 by GitHub Actions): `POST /leads` hardened for the website form.
  CORS for `https://inocube.sk` only (`OPTIONS /leads` 204), honeypot `website`, throttling 5 req/s
  (burst 10) per method, control/format characters rejected, SES e-mail to the owner per stored lead
  (Reply-To = lead), 256 MB, 30-day log retention. Owner smoke test: 201, e-mail arrived, test lead deleted.
  SES domain `inocube.sk` (Easy DKIM) and recipient `inocube@varga.slmail.me` are verified.
- T-003 (PR #7): `ci.yml` checks every PR; `deploy.yml` deploys prod on merge to `main` via GitHub OIDC
  (ADR 0012). Function roles carry the `InocubeWebLambdaBoundary` boundary.
- Website form on inocube.sk/kontakt/ sends leads to this API (frontend T-002).

## In progress

- Nothing. Next phase: owner to choose (roadmap).

## Not done yet

- No staging stack, no alarms, no custom domain. No CAPTCHA or duplicate-submission check.
- SES account in the sandbox: notification goes only to verified recipients.

## Known issues

- AWS access differs from ADR 0004: the SSO user has only `InocubeDevAccess`, which can create
  IAM roles. `InocubeWebSamDeploy` and the `inocube-deploy` profile do not exist; the T-001 deploy ran
  with `inocube`. Owner decided to align AWS with the ADR: `doc/tasks/T-002-aws-access-alignment.md`.
- Commit `17193d5 "test direct push"` is in `main` history (from testing branch protection). Harmless.
