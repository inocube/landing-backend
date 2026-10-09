# T-002 Align AWS access with ADR 0004

- Status: ready (owner task: IAM Identity Center changes need the owner's admin login)
- Roadmap phase: 2b
- Decided: 2026-10-09, owner chose "align AWS with ADR 0004" over rewriting the ADR.

## Goal

Daily work runs with `PowerUserAccess` (profile `inocube`), and only deploys use `InocubeSamDeploy`
(profile `inocube-deploy`), as ADR 0004, `doc/architecture.md` and `README.md` already say.

## Context

The T-001 deploy (2026-10-08) showed reality differs from the docs:
- The SSO user has only the permission set `InocubeDevAccess`, which can create IAM roles.
- `InocubeSamDeploy` is not assigned, and `~/.aws/config` has no `inocube-deploy` profile.
- The deploy therefore ran with the broad daily profile.

## Steps (owner, AWS console as an Identity Center admin)

1. **IAM Identity Center → Permission sets → Create permission set → Custom**, name `InocubeSamDeploy`,
   session duration 1 h. Inline policy: paste
   [`doc/aws/inocube-sam-deploy-policy.json`](../aws/inocube-sam-deploy-policy.json). No managed policies.
2. **AWS accounts → 754895435437 → Assign users or groups**: your user, permission set `InocubeSamDeploy`.
3. **Narrow daily access**: open permission set `InocubeDevAccess`, remove its current policies and attach
   only the AWS managed policy `PowerUserAccess`. (Or delete it and assign `PowerUserAccess` instead.)
   Then update `sso_role_name` of profile `inocube` in `~/.aws/config` if the name changed.
4. **Add the deploy profile** to `C:\Users\<you>\.aws\config` (the agent on the PC may do this):
   ```ini
   [profile inocube-deploy]
   sso_session = inocube-sso
   sso_account_id = 754895435437
   sso_role_name = InocubeSamDeploy
   region = eu-central-1
   ```

## Acceptance criteria

- `aws sts get-caller-identity --profile inocube-deploy` shows role `AWSReservedSSO_InocubeSamDeploy_*`.
- `sam deploy --profile inocube-deploy --no-execute-changeset` on current `main` ends with
  "No changes to deploy" (no AccessDenied).
- `aws iam create-role ... --profile inocube` fails with AccessDenied (daily profile cannot create roles).

## Notes

- The policy is scoped to stack `inocube-backend`, functions/roles/log groups prefixed `inocube-backend-`,
  table `inocube-leads` (no `DeleteTable`, so a template change that would replace the table fails instead
  of deleting data) and SSM parameters under `/inocube/`.
- Not tested against AWS yet. If a deploy hits AccessDenied, add only the named action and record it here.
- Out of scope: CI/CD OIDC role (roadmap phase 3).
