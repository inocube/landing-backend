# Roadmap

Phases run in order. A phase is done when its acceptance criteria hold and `doc/status.md` says so.
Tasks for the implementer are cut from the current phase into `doc/tasks/`.

| # | Phase | State |
|---|---|---|
| 0 | Skeleton: SSO, SAM, health Lambda, branch protection | done |
| 1 | DynamoDB table and key design | done |
| 2 | Leads API: POST /leads | next (T-001) |
| 2b | Connect the website form | planned |
| 3 | CI/CD with GitHub Actions + OIDC, staging + prod | planned |
| 4 | AI lead triage with Bedrock | planned |
| 5 | Production hardening, `api.inocube.sk` | planned |
| 6 | AI assistant on the website (RAG) | idea |

## 2. Leads API
- `POST /leads` validates input (pydantic) and stores the lead; returns `201 {lead_id, status}`.
- 400 on invalid JSON or fields, 500 on storage failure, no PII in logs.
- Unit tests with moto; least-privilege write policy.

## 2b. Connect the website form
- CORS restricted to `https://inocube.sk` (+ Netlify preview origin for staging).
- Honeypot field and API Gateway throttling against spam.
- SES notification e-mail to the owner for every lead (verified sender in SES).
- Frontend form posts to the API and shows success / error states (frontend repo).

## 3. CI/CD
- GitHub Actions: on PR run lint, tests, `sam validate`, `sam build`.
- On merge to `main`: deploy to staging; prod deploy on manual approval or tag.
- AWS access via GitHub OIDC role with a narrow trust policy (repo + branch). No secrets in GitHub.

## 4. AI lead triage
- Asynchronous (DynamoDB Stream or SQS) so the form response never waits for the model.
- Bedrock model via EU inference; output: summary, matching service package, draft reply.
- Stored on the lead and included in the owner e-mail. Owner sends the reply, never the AI (ADR 0007).
- Prompt-injection defence: lead text treated as data, structured output, no tools for the model.

## 5. Hardening
- Custom domain `api.inocube.sk` (ACM certificate, DNS at Websupport).
- CloudWatch alarms (5xx, Lambda errors, throttles), AWS Budget alert.
- IAM review, log retention, data retention policy for leads (GDPR).

## 6. AI assistant on the website
- RAG over public website content (services, case studies), Bedrock Knowledge Bases or equivalent.
- Clearly labelled as AI (EU AI Act art. 50), rate limited, no personal data stored.
