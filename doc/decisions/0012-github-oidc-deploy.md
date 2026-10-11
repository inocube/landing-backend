# 0012. Deploy prod from GitHub Actions with an OIDC role

- Status: Accepted
- Date: 2026-10-11

## Context
ADR 0011 forbids agents from using the owner's identity, so someone else must run deploys. Long-lived AWS
access keys in GitHub would be a standing secret in a public repo.

## Decision
- Every push to `main` runs `.github/workflows/deploy.yml`: `sam build` on a native arm64 runner, then
  `sam deploy` of the `inocube-backend` (prod) stack and a `GET /health` smoke test.
- AWS access comes from the GitHub OIDC provider: role `inocube-github-deploy` with only `InocubeSamDeploy`,
  1 h sessions, trusted only for `sub` = `repo:inocube/landing-backend:environment:production`.
- The GitHub environment `production` accepts only branch `main`. The role ARN is a repo variable, not a secret.
- Pull requests run `ci.yml` (ruff, pytest, `sam validate --lint`, `sam build`) without AWS credentials.

## Consequences
No stored AWS keys; merge = deploy, so `main` protection and review are the release gate. Prod stays the
only stack (ADR 0010 still holds); staging and approval gates come later in phase 3.
