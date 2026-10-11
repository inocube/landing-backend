# T-003: Deploy from GitHub Actions with an OIDC role

- Status: changes-requested
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
7. Owner steps (in this task file under `## Owner steps
Do all of these before merging: the merge itself triggers a deploy. AWS console as admin, `eu-central-1`.
1. **GitHub → repo Settings → Environments → New environment** `production`; Deployment branches and tags →
   Selected branches → add rule `main`. Do this first: before it exists, any workflow naming `production`
   would auto-create it unprotected and get a token the role trusts.
2. **IAM → Policies → `InocubeLambdaBoundary`** must exist (T-002 step 1) and match
   [`inocube-lambda-boundary.json`](../aws/inocube-lambda-boundary.json) (now with X-Ray): Edit → JSON →
   paste → Save as new default version. Must exist before any deploy of this template.
3. **IAM → Identity providers → Add provider → OpenID Connect**, URL `https://token.actions.githubusercontent.com`,
   audience `sts.amazonaws.com`.
4. **IAM → Policies → Create policy → JSON**, paste [`inocube-sam-deploy-policy.json`](../aws/inocube-sam-deploy-policy.json),
   name `InocubeSamDeploy` (customer managed; also update the T-002 permission set copy to the same JSON).
5. **IAM → Roles → Create role → Custom trust policy**, paste
   [`github-oidc-trust-policy.json`](../aws/github-oidc-trust-policy.json); attach only `InocubeSamDeploy`;
   name `inocube-github-deploy`. Then role → Edit → Maximum session duration 1 hour. Copy the role ARN.
6. **GitHub → Settings → Secrets and variables → Actions → Variables → New repository variable**
   `AWS_DEPLOY_ROLE_ARN` = the role ARN from step 5 (a variable, not a secret: an ARN is not a credential).
7. **GitHub → Settings → Rules → Rulesets → the `main` ruleset → Require status checks to pass** → add `checks`
   (the `ci.yml` job; it appears after one CI run on the PR).
8. **Check before merging:** Settings → Environments → `production` shows the branch rule `main`, and the
   ruleset lists `checks`. If either is missing, do not merge.
9. Merge the PR and watch **Actions → Deploy** right away (or start it via **Run workflow**
   (`workflow_dispatch`) on `main` right after setup). Expect: tests, build, deploy, `GET /health -> 200`.
   The first deploy adds the boundary to `HealthFunctionRole` and `LeadsFunctionRole`; nothing else changes.
10. **If that first deploy fails** and the stack ends in `UPDATE_ROLLBACK_FAILED` (rollback cannot remove the
    boundaries: the deploy role is denied `iam:DeleteRolePermissionsBoundary`), recover as admin:
    `aws cloudformation continue-update-rollback --stack-name inocube-backend --resources-to-skip HealthFunctionRole LeadsFunctionRole`
    The roles keep the boundary, which is harmless; fix the cause and run the workflow again.
11. On AccessDenied in the deploy log: add only the named action to the policy JSON (PR) and to the IAM policy.

## Implementation notes
- Branch `feat/T-003-github-oidc-deploy`, cut from `docs/status-after-T-001` (PR #6, holds ADR 0011 and the
  T-002 policies), not from `main`. Merge PR #6 first. PR opened by the orchestrator.
- Actions pinned to SHAs verified with `git ls-remote`/clone: checkout v7.0.1, setup-python v7.0.0,
  configure-aws-credentials v6.3.0, setup-sam v3 (`use-installer: true`, SAM CLI 1.168.0). ruff pinned 0.16.8.
- `allowed-account-ids: 754895435437` makes the job fail if the role ever resolves to another account.
  OIDC sessions are not tagged by the action, so the trust policy needs no `sts:TagSession`.
- Smoke test reads `ApiUrl` via `sam list stack-outputs` (only `DescribeStacks`), curl retries 5x.
- Fixed one pre-existing ruff finding (I001 in `src/health/app.py`) so `ci.yml` passes.
- Deploy policy audit, unchanged: covers CloudFormation (stack, SAM transform, `aws-sam-cli-managed-default`
  stack), S3 SAM bucket, `lambda:*` on `inocube-backend-*`, roles only with boundary, API Gateway, the table
  (no delete) and log groups. X-Ray is runtime-only, so it is in the boundary, not the deploy policy.
  Untested against AWS: if CloudFormation asks for extra table reads (e.g. `DescribeContributorInsights`)
  or IAM role actions, apply step 8.
- Review fixes: owner steps reordered (environment first, pre-merge check, required `checks` status,
  rollback recovery); SAM CLI pinned 1.168.0; `deploy.yml` reruns ruff + pytest before deploying;
  `iam:PassRole` only to `lambda.amazonaws.com`; SAM bucket limited by `s3:ResourceAccount`; ADR 0012 amends 0010.
- Follow-ups (not in this task): pin exact versions in `src/*/requirements.txt` (ranges resolve at deploy
  time); narrow `apigateway` beyond `/restapis/*`; `xray:GetSampling*` in the boundary if ever needed.
- Local: `ruff check .` and `pytest` (28 passed) green; actionlint clean; SAM CLI 1.168.0
  `sam validate --lint` valid and `sam build` OK (x86 host, Python 3.14). CI repeats both on arm64.

## Architect review
Verdict: changes-requested (re-review of d3e5e9b, a6f7861, ea72a1e; one doc regression left)

Re-checked: ruff clean, `pytest` 28 passed, `sam validate --lint` valid, actionlint clean, policy JSON parses.
First review: 1 (environment before role, pre-merge check), 2 (rollback recovery step), 3 (SAM CLI 1.168.0
pinned in both workflows), 4 (required `checks` step and ruff + pytest rerun in `deploy.yml` before credentials)
and 7 (ADR 0012 amends 0010) are resolved. Finding 6: `iam:PassedToService` is a valid key for `iam:PassRole`,
and CloudFormation's Lambda create/update passes the role to `lambda.amazonaws.com`, so deploys still work.
`s3:ResourceAccount` is valid for all S3 actions and matches the existing SAM bucket. Requirements pins,
`apigateway` and `xray:GetSampling*` are follow-ups, as the coordinator decided.

1. High, `doc/tasks/T-003-github-oidc-deploy.md:33-34`: ea72a1e cut this file apart. Scope item 7 now ends
   mid-sentence ("under `## Owner steps"), scope item 8 is gone, and the `## Acceptance criteria`,
   `## Out of scope`, `## Open questions` and `## Owner steps` headings are deleted. The owner steps now sit
   inside Scope. Fix: restore those sections from 88aa8f3 and keep the new 11 owner steps under `## Owner steps`.
2. Medium, same file: the commit says finding 5 is recorded in Open questions as an accepted risk pending the
   owner, but that section no longer exists. Restore it with that entry.
3. Low, `:76`: "apply step 8" should now say "apply step 11".
No IAM or workflow regressions found.

Questions for the owner
- Finding 5 (a stolen deploy session can create a bounded role that another AWS account can assume and that
  outlives the session): accept it, or harden the boundary? Want a required reviewer on `production` until
  staging exists?
- `inocube` is a user account, so a rename frees the name used in `sub`. Pin `sub` to `repository_id` later?
