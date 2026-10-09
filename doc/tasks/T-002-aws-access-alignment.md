# T-002 Restricted deploy identity for agents

- Status: ready (owner steps need the owner's admin login; one small code change for the implementer)
- Roadmap phase: 2b
- Decided: 2026-10-09. Owner: align AWS with ADR 0004, and agents must use only a restricted technical
  identity that cannot grant access, never the owner's (ADR 0011).

## Goal

Daily owner work runs with `PowerUserAccess`. Deploys by agents or a pipeline use only `InocubeSamDeploy`,
which cannot manage users, SSO or policies and can create roles only inside `InocubeLambdaBoundary`.

## Context

The T-001 deploy (2026-10-08) ran with the owner's SSO session (`InocubeDevAccess`, can create IAM roles).
`InocubeSamDeploy` was not assigned; the `inocube-deploy` profile did not exist.

## Steps for the owner (AWS console, as an admin)

1. **IAM → Policies → Create policy**, name `InocubeLambdaBoundary`, JSON from
   [`doc/aws/inocube-lambda-boundary.json`](../aws/inocube-lambda-boundary.json).
2. **IAM Identity Center → Permission sets → Create → Custom**, name `InocubeSamDeploy`, session 1 h,
   inline policy from [`doc/aws/inocube-sam-deploy-policy.json`](../aws/inocube-sam-deploy-policy.json).
3. **Narrow your daily set**: `InocubeDevAccess` keeps only the AWS managed `PowerUserAccess`.
4. **Agent user** `inocube-agent` (IAM user, owner's choice 2026-10-09): no console password, MFA on,
   inline policy only [`doc/aws/inocube-agent-readonly-policy.json`](../aws/inocube-agent-readonly-policy.json)
   (read stack, logs, metrics; no lead data, no writes, IAM/SSO denied). The owner runs
   `aws configure --profile inocube-agent` himself; agents never see the keys. Rotate the key every 90 days.
5. **Deploys** run from GitHub Actions with an OIDC role carrying `InocubeSamDeploy` (phase 3), so no agent
   needs write access. Until then the owner deploys.

## Implementer change (before the first deploy with the new policy)

- `template.yaml`: `Globals.Function.PermissionsBoundary:
  !Sub arn:aws:iam::${AWS::AccountId}:policy/InocubeLambdaBoundary`. Without it the restricted role cannot
  update `LeadsFunctionRole`.

## Acceptance criteria

- `inocube-agent`: `aws iam list-users` and any write call fail with AccessDenied.
- Deploy identity: `sam deploy --no-execute-changeset` on `main` shows only the boundary added to
  `LeadsFunctionRole`, with no AccessDenied.
- Deploy identity: `aws iam create-user` and `aws iam create-role` without the boundary fail with AccessDenied.
- Owner daily profile `inocube`: `aws iam create-role` fails with AccessDenied.

## Notes

- `InocubeSamDeploy` has no `DeleteTable`, so a change that would replace `inocube-leads` fails.
- Policies are not tested against AWS yet. On AccessDenied add only the named action and record it here.
