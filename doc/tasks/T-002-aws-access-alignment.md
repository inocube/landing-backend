# T-002 Restricted deploy identity for agents

- Status: ready (owner steps need the owner's admin login; one small code change for the implementer)
- Roadmap phase: 2b
- Decided: 2026-10-09. Owner: align AWS with ADR 0004, and agents must use only a restricted technical
  identity that cannot grant access, never the owner's (ADR 0011).

## Goal

Daily owner work runs with `PowerUserAccess`. Deploys by agents or a pipeline use only `InocubeWebSamDeploy`,
which cannot manage users, SSO or policies and can create roles only inside `InocubeWebLambdaBoundary`.

## Context

The T-001 deploy (2026-10-08) ran with the owner's SSO session (`InocubeDevAccess`, can create IAM roles).
`InocubeWebSamDeploy` was not assigned; the `inocube-deploy` profile did not exist.

## Steps for the owner (AWS console, as an admin)

1. **IAM → Policies → Create policy**, name `InocubeWebLambdaBoundary`, JSON from
   [`doc/aws/inocube-web-lambda-boundary.json`](../aws/inocube-web-lambda-boundary.json).
2. **IAM Identity Center → Permission sets → Create → Custom**, name `InocubeWebSamDeploy`, session 1 h,
   inline policy from [`doc/aws/inocube-web-sam-deploy-policy.json`](../aws/inocube-web-sam-deploy-policy.json).
3. **Narrow your daily set**: `InocubeDevAccess` keeps only the AWS managed `PowerUserAccess`.
4. **Deploys** run from GitHub Actions with an OIDC role carrying `InocubeWebSamDeploy` (T-003, ADR 0012).
   Agents hold no AWS identity at all (owner decision 2026-10-11). Until T-003 is live the owner deploys.

## Implementer change (done in T-003)

- `template.yaml`: `Globals.Function.PermissionsBoundary:
  !Sub arn:aws:iam::${AWS::AccountId}:policy/InocubeWebLambdaBoundary`. Without it the restricted role cannot
  update `LeadsFunctionRole`.

## Acceptance criteria

- Deploy identity: `sam deploy --no-execute-changeset` on `main` shows only the boundary added to
  `LeadsFunctionRole`, with no AccessDenied.
- Deploy identity: `aws iam create-user` and `aws iam create-role` without the boundary fail with AccessDenied.
- Owner daily profile `inocube`: `aws iam create-role` fails with AccessDenied.

## Notes

- `InocubeWebSamDeploy` has no `DeleteTable`, so a change that would replace `inocube-leads` fails.
- Policies are not tested against AWS yet. On AccessDenied add only the named action and record it here.
