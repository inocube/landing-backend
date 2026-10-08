# 0004. IAM Identity Center with two permission sets

- Status: Accepted
- Date: 2026-07-03

## Context
Long-lived IAM user keys in `~/.aws/credentials` are a security risk. `PowerUserAccess` cannot create IAM
roles, which `sam deploy` needs for Lambda execution roles.

## Decision
Humans sign in through IAM Identity Center (SSO, temporary credentials, MFA). Two permission sets:
`PowerUserAccess` (CLI profile `inocube`) for daily work and `InocubeSamDeploy` (profile `inocube-deploy`)
which adds the IAM actions needed to deploy.

## Consequences
No stored keys on laptops. Deploys use `--profile inocube-deploy`. CI will use a separate OIDC role.
