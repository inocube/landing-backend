# T-003: Deploy from GitHub Actions with an OIDC role

- Status: in-progress
- Roadmap phase: 3 (pulled forward, prod only)
- Branch: feat/T-003-github-oidc-deploy

## Goal
Every merge to `main` deploys the `inocube-backend` stack from GitHub Actions with a short-lived OIDC role,
so no agent and no laptop needs AWS write credentials (owner decision 2026-10-09, ADR 0011).

## Context
- ADR 0004 (SSO), 0010 (single prod until CI/CD), 0011 (agents never use the owner's identity).
- `doc/aws/inocube-sam-deploy-policy.json` (deploy rights) and `doc/aws/inocube-lambda-boundary.json`
  (ceiling for every role the stack creates) exist from T-002. Owner creates AWS resources by hand once;
  the repo holds the JSON and the steps.
- Repo is public: GitHub-hosted `ubuntu-24.04-arm` runners are free and build arm64 natively.
- `samconfig.toml` sets `profile = "inocube"`, which breaks a CI deploy.
- Functions use `Tracing: Active`, so their roles need X-Ray write inside the boundary.

## Scope
1. `.github/workflows/ci.yml` on `pull_request`: ruff, pytest, `sam validate --lint`, `sam build` (arm64).
2. `.github/workflows/deploy.yml` on `push` to `main` (+ `workflow_dispatch`), job `environment: production`,
   `permissions: id-token: write, contents: read`, `aws-actions/configure-aws-credentials` with
   `role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}` (repo variable, not a secret), `sam build`,
   `sam deploy --no-confirm-changeset --no-fail-on-empty-changeset`, then a smoke test `GET /health` == 200.
   Pin actions to full commit SHAs. `concurrency` so two deploys never overlap.
3. `template.yaml`: `Globals.Function.PermissionsBoundary:
   !Sub arn:aws:iam::${AWS::AccountId}:policy/InocubeLambdaBoundary`.
4. `doc/aws/inocube-lambda-boundary.json`: add `xray:PutTraceSegments`, `xray:PutTelemetryRecords`.
5. `samconfig.toml`: remove `profile`; README deploy section passes `--profile` explicitly.
6. `doc/aws/github-oidc-trust-policy.json`: trust `token.actions.githubusercontent.com`, `aud`
   `sts.amazonaws.com`, `sub` exactly `repo:inocube/landing-backend:environment:production`.
7. Owner steps (in this task file under `## Owner steps`): create the GitHub OIDC identity provider, role
   `inocube-github-deploy` (trust policy from 6, managed policy from the deploy JSON, max session 1 h),
   GitHub environment `production` limited to branch `main`, repo variable `AWS_DEPLOY_ROLE_ARN`.
8. ADR 0012 (GitHub OIDC deploy, prod on merge); update `doc/architecture.md`, `doc/roadmap.md`,
   `doc/status.md`, README.

## Acceptance criteria
- [ ] `ci.yml` passes on the PR itself (deploy workflow does not run on PRs).
- [ ] No AWS keys or secrets anywhere; the role ARN is a repo variable.
- [ ] Trust policy cannot be assumed from another repo, branch, fork or PR (`sub` pinned to the environment).
- [ ] `sam validate --lint` passes with the boundary; local `pytest` green.
- [ ] Every third-party action pinned to a commit SHA.
- [ ] PR explains OIDC, trust policy, permissions boundary and why no access keys, for an owner learning AWS.

## Out of scope
Staging stack, CORS/throttling/honeypot (phase 2b), alarms, custom domain. Do not create AWS resources.

## Open questions
(none)

## Owner steps
(implementer)

## Implementation notes
(implementer)

## Architect review
(architect)
