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
- Accepted risk, pending owner (architect finding 5): `InocubeSamDeploy` can create `inocube-backend-*` roles
  with any trust policy (only the boundary is enforced). A stolen 1 h deploy session could leave a role that a
  foreign account can assume after the session ends and that, within the boundary, reads leads (PII), reads
  `/inocube/*` and sends mail as inocube.sk. Mitigation (test first): a boundary `Deny` on all actions when
  `lambda:SourceFunctionArn` is Null, so only Lambda can use these roles.
- Owner: require a reviewer on environment `production` until staging exists?
- Owner: pin `sub` to `repository_id` later? (`inocube` is a user account; a rename frees the name.)

## Owner steps
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
- Cut from `docs/status-after-T-001` (PR #6); merge #6 first. SHAs verified via `git ls-remote`: checkout v7.0.1,
  setup-python v7.0.0, configure-aws-credentials v6.3.0, setup-sam v3 (SAM CLI 1.168.0); ruff 0.16.8.
- `allowed-account-ids` guards the account; OIDC sessions are untagged (no `sts:TagSession`). Fixed ruff I001
  in `src/health/app.py`. Deploy policy untested against AWS: on AccessDenied apply step 11.
- Follow-ups: exact pins in `src/*/requirements.txt`; narrower `apigateway`; `xray:GetSampling*` if needed.

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
