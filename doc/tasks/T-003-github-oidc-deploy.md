# T-003: Deploy from GitHub Actions with an OIDC role

- Status: review
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
Do these before merging: the merge itself triggers the first deploy. AWS console as admin, `eu-central-1`.
1. **IAM → Policies → `InocubeLambdaBoundary`** must exist (T-002 step 1) and match
   [`inocube-lambda-boundary.json`](../aws/inocube-lambda-boundary.json) (now with X-Ray): Edit → JSON →
   paste → Save as new default version. Must exist before any deploy of this template.
2. **IAM → Identity providers → Add provider → OpenID Connect**, URL `https://token.actions.githubusercontent.com`,
   audience `sts.amazonaws.com`.
3. **IAM → Policies → Create policy → JSON**, paste [`inocube-sam-deploy-policy.json`](../aws/inocube-sam-deploy-policy.json),
   name `InocubeSamDeploy` (customer managed; the T-002 permission set is a separate copy).
4. **IAM → Roles → Create role → Custom trust policy**, paste
   [`github-oidc-trust-policy.json`](../aws/github-oidc-trust-policy.json); attach only `InocubeSamDeploy`;
   name `inocube-github-deploy`. Then role → Edit → Maximum session duration 1 hour. Copy the role ARN.
5. **GitHub → repo Settings → Environments → New environment** `production`; Deployment branches and tags →
   Selected branches → add rule `main`.
6. **GitHub → Settings → Secrets and variables → Actions → Variables → New repository variable**
   `AWS_DEPLOY_ROLE_ARN` = the role ARN from step 4 (a variable, not a secret: an ARN is not a credential).
7. Merge the PR, then check **Actions → Deploy**: build, deploy, `GET /health -> 200`. The first deploy adds the
   boundary to `HealthFunctionRole` and `LeadsFunctionRole`; nothing else should change.
8. On AccessDenied in the deploy log: add only the named action to the policy JSON (PR) and to the IAM policy.

## Implementation notes
- Branch `feat/T-003-github-oidc-deploy`, cut from `docs/status-after-T-001` (PR #6, holds ADR 0011 and the
  T-002 policies), not from `main`. Merge PR #6 first. PR opened by the orchestrator.
- Actions pinned to SHAs verified with `git ls-remote`/clone: checkout v7.0.1, setup-python v7.0.0,
  configure-aws-credentials v6.3.0, setup-sam v3 (`use-installer: true`, latest SAM CLI). ruff pinned 0.16.8.
- `allowed-account-ids: 754895435437` makes the job fail if the role ever resolves to another account.
  OIDC sessions are not tagged by the action, so the trust policy needs no `sts:TagSession`.
- Smoke test reads `ApiUrl` via `sam list stack-outputs` (only `DescribeStacks`), curl retries 5x.
- Fixed one pre-existing ruff finding (I001 in `src/health/app.py`) so `ci.yml` passes.
- Deploy policy audit, unchanged: covers CloudFormation (stack, SAM transform, `aws-sam-cli-managed-default`
  stack), S3 SAM bucket, `lambda:*` on `inocube-backend-*`, roles only with boundary, API Gateway, the table
  (no delete) and log groups. X-Ray is runtime-only, so it is in the boundary, not the deploy policy.
  Untested against AWS: if CloudFormation asks for extra table reads (e.g. `DescribeContributorInsights`)
  or IAM role actions, apply step 8.
- Local: `ruff check .` and `pytest` (28 passed) green; actionlint clean; SAM CLI 1.168.0
  `sam validate --lint` valid and `sam build` OK (x86 host, Python 3.14). CI repeats both on arm64.

## Architect review
(architect)
