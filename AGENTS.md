# AGENTS.md: rules for AI agents in landing-backend

Read this first, then `doc/README.md`. Keep this file under ~150 lines.

## Project in one paragraph

Serverless lead-capture backend for the inocube.sk company website. Python Lambdas behind API Gateway,
DynamoDB single-table storage, AWS SAM as IaC, deployed to `eu-central-1`. The repo is public and serves as
the owner's portfolio, so code quality and clear commits matter as much as working features.

## Where to find things

- Goals and scope: `doc/goals.md`
- How it is built: `doc/architecture.md`
- What works today: `doc/status.md`
- What comes next: `doc/roadmap.md`
- Why things are the way they are: `doc/decisions/` (ADRs, read before proposing a change of direction)
- Your assignment: `doc/tasks/T-xxx-*.md`

## Roles

| Role | Who | Does |
|---|---|---|
| Orchestrator | Claude in the owner's project | Writes tasks in `doc/tasks/`, keeps `doc/` current, routes work |
| Implementer | Claude Code agent (`.claude/agents/implementer.md`) | Implements one task on a branch, opens a PR |
| Architect | Claude Code agent (`.claude/agents/architect.md`) | Reviews the PR against the task, ADRs and these rules; may block |
| Owner | Roman | Answers open questions, merges PRs, runs deploys |

## Workflow for a task

1. Read the task file fully. If something is ambiguous, write the question under `## Open questions`
   in the task and stop; do not guess on scope, security or data model.
2. Branch from fresh `main`: `feat/T-xxx-short-name` (or `fix/`, `docs/`).
3. Implement in small commits (Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`).
4. Run before pushing: `sam validate`, `pytest`, and `sam build --use-container` when dependencies changed.
5. Update docs touched by the change: `doc/status.md` always; `doc/architecture.md` if structure changed;
   a new ADR if you made a decision with lasting impact.
6. Push the branch and open a PR. The PR description must contain:
   - What changed and how to verify it.
   - **Why it is built this way**: a short explanation for the owner, who is learning AWS through this
     project. Explain the AWS concepts used, the alternatives you rejected and the trade-offs.
7. Set the task `Status` to `review`. The architect reviews; fix findings in the same PR.

## Hard rules

- Never commit secrets. `.env` is git-ignored; only `.env.example` (names, no real values) is tracked.
  Production secrets go to AWS SSM Parameter Store, referenced from `template.yaml`.
- Never push to `main`, never force-push a shared branch, never merge your own PR.
- Never run `sam deploy`, `aws ... delete-*` or anything that changes AWS resources unless the task says so
  explicitly. The owner deploys.
- Infrastructure changes go through `template.yaml` only, never by hand in the console.
- Least privilege: use the narrowest SAM policy template (e.g. `DynamoDBWritePolicy` over `DynamoDBCrudPolicy`).
- No personal data in logs: log IDs and outcomes, never names, emails or message bodies (GDPR).
- Do not add dependencies without a reason stated in the PR. `boto3` ships with the Lambda runtime: do not
  package it.

## Code conventions

- One folder per function in `src/`. Handler `app.py` handles HTTP only; validation in `models.py`
  (pydantic); data access in `repository.py` (boto3). Keep handlers thin.
- Read configuration from environment variables set in `template.yaml` (e.g. `TABLE_NAME`); never hardcode
  resource names. Optional `DYNAMODB_ENDPOINT` switches boto3 to DynamoDB Local.
- HTTP responses: JSON body, correct status codes (201 created, 400 invalid input, 500 server error).
  Error bodies never leak stack traces.
- Use `logging`, not `print`. `logger.exception` for unexpected errors.
- Type hints on public functions. Format with `ruff format`, lint with `ruff check` if available.
- Tests in `tests/unit/`, AWS mocked with `moto`. Every endpoint: happy path, invalid input, storage failure.

## DynamoDB key design (do not change without an ADR)

| Item | PK | SK | GSI1PK / GSI1SK | GSI2PK / GSI2SK |
|---|---|---|---|---|
| Lead | `LEAD#<uuid>` | `LEAD#<uuid>` | `LEAD` / `<created_at ISO>` | `EMAIL#<email lowercased>` / `<created_at ISO>` |

## Environment notes

- Owner works on Windows + PowerShell. Give commands that work in PowerShell; for AWS CLI JSON input use
  `file://` arguments instead of inline escaped JSON.
- AWS profiles: `inocube` (PowerUserAccess, daily work), `inocube-deploy` (can create IAM roles, for deploys).
- Build with `sam build --use-container` (compiled deps such as pydantic-core must be Linux/arm64).
