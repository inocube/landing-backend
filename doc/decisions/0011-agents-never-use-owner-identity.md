# 0011. Agents never use the owner's AWS identity

- Status: Accepted
- Date: 2026-10-09

## Context
The T-001 deploy ran from an agent on the owner's PC with the owner's SSO session, whose role can create
IAM roles. An agent holding a role that can grant access can escalate its own rights. The owner requires
agents to use only a restricted technical identity and never act under his account.

## Decision
- Agents never run `aws sso login` for the owner, never use profiles `inocube` / `inocube-deploy`, and never
  ask the owner for sign-in codes.
- Agents hold no AWS identity at all: they change code and open PRs. Only the GitHub Actions OIDC role
  (ADR 0012) deploys, and it gets only `InocubeWebSamDeploy`.
- `InocubeWebSamDeploy` may create IAM roles only with the permissions boundary `InocubeWebLambdaBoundary`
  attached, so no role it creates can exceed that boundary (no IAM, no access outside this project).
- Granting or changing access (Identity Center, IAM users, boundaries) stays with the owner.

## Consequences
Until the OIDC pipeline is live, the owner deploys. SAM functions must declare the
boundary (`Globals.Function.PermissionsBoundary`). Supersedes the deploy part of ADR 0004 for agents.
