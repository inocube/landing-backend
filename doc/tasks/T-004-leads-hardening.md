# T-004: Harden POST /leads for the public website form

- Status: review
- Roadmap phase: 2b
- Branch: feat/T-004-leads-hardening

## Goal
The website form at `https://inocube.sk/kontakt` can call `POST /leads` from the browser, spam is cheap to
reject, and the owner gets an e-mail for every new lead.

## Context
- Deploy runs from GitHub Actions on merge (ADR 0012); the merge of this PR deploys prod.
- Every Lambda role is capped by `InocubeWebLambdaBoundary` (`doc/aws/inocube-web-lambda-boundary.json`):
  table, own logs, X-Ray, SSM `/inocube/*`, SES `identity/inocube.sk`. Anything outside needs a boundary change
  (owner applies it in IAM before merge) and possibly a deploy-policy change.
- The architect review of T-001 listed: no throttling, 128 MB memory, control characters accepted, duplicate
  submissions. `LeadCreate` already ignores unknown fields.
- Frontend task `inocube/public` T-002 builds the form against the contract below.

## Scope
1. **CORS:** allowed origins `https://inocube.sk` and Netlify previews
   `https://deploy-preview-<n>--inocube-public.netlify.app`. Answer the `OPTIONS` preflight and set
   `Access-Control-Allow-Origin` (echo only an allowed origin, `Vary: Origin`) on every `/leads` response.
2. **Honeypot:** a non-empty `website` field → respond `201` with a fake `lead_id`, store nothing, send nothing,
   log `Lead dropped: honeypot`.
3. **Throttling** on the API stage (e.g. rate 5/s, burst 10) so a flood cannot run up cost.
4. **Input hygiene:** reject control characters (except newline/tab in `message`) with 400.
5. **Owner notification:** after a successful store, send an e-mail via SES v2 from `noreply@inocube.sk` to the
   address in template parameter `NotifyEmail` (default `inocube@varga.slmail.me`): subject with the lead id, body
   with name, e-mail, message. E-mail failure is logged (id only) and does not change the 201. No PII in logs.
6. **Ops:** `MemorySize: 256`; CloudWatch log retention 30 days for both functions (watch out: log groups created
   by Lambda already exist).
7. Update `doc/status.md`, `doc/architecture.md`, roadmap; owner steps for SES (domain identity `inocube.sk` with
   DKIM records at Websupport, verify the recipient while SES is in sandbox) and any boundary/deploy-policy edit.

## API contract (for the frontend)
`POST /leads` JSON `{name, email, message, website?}` → `201 {lead_id, status}` | `400 {error, details[]}` |
`429` (throttled) | `500 {error}`.

## Acceptance criteria
- [ ] Preflight and POST from an allowed origin succeed; other origins get no `Access-Control-Allow-Origin`.
- [ ] Honeypot submissions are not stored and not mailed; tests prove it.
- [ ] Notification sent once per stored lead; SES failure still returns 201; tests with moto.
- [ ] Throttling, 256 MB and 30-day retention visible in `template.yaml`; `sam validate --lint` passes.
- [ ] No PII in logs; boundary and deploy policy still sufficient (or the needed edits are listed as owner steps).
- [ ] PR explains CORS, honeypot, throttling and SES sandbox for an owner learning AWS.

## Out of scope
CAPTCHA, AI triage (phase 4), custom domain `api.inocube.sk`, auto-reply to the sender (ADR 0007).

## Open questions
(none; defaults: sender `noreply@inocube.sk`, recipient `inocube@varga.slmail.me`)

## Owner steps
Before merging (the merge deploys prod). AWS console as admin, region `eu-central-1`.
1. **SES → Identities → Create identity → Domain** `inocube.sk`, Easy DKIM, RSA 2048, no default configuration
   set. At **Websupport → DNS** add the 3 CNAMEs SES shows (`<token>._domainkey` → `<token>.dkim.amazonses.com`;
   host without the `.inocube.sk` suffix). Wait until the identity is *Verified*. Keep existing SPF/MX records.
2. **SES → Create identity → Email address** `inocube@varga.slmail.me`, click the link in the mail (sandbox only
   delivers to verified addresses). Both identities must show *Verified*.
3. **IAM → Policies → `InocubeWebLambdaBoundary`** → Edit → JSON → paste
   [`inocube-web-lambda-boundary.json`](../aws/inocube-web-lambda-boundary.json) (adds the recipient identity).
4. **IAM → Policies → `InocubeWebSamDeploy`** → paste [`inocube-web-sam-deploy-policy.json`](../aws/inocube-web-sam-deploy-policy.json)
   (log-group read actions for CloudFormation); same JSON in the permission-set copy.
5. Merge; watch **Actions → Deploy**. Then check in PowerShell (one real lead, delete it in DynamoDB after):
   ```powershell
   $api = "https://i6r0knhf3m.execute-api.eu-central-1.amazonaws.com/Prod/leads"
   curl.exe -i -X OPTIONS $api -H "Origin: https://inocube.sk" -H "Access-Control-Request-Method: POST"
   curl.exe -i -X POST $api -H "Origin: https://inocube.sk" -H "Content-Type: application/json" --data-binary "@local-test/lead-post-valid.json"
   ```
   Expect `204` + `Access-Control-Allow-Origin`, then `201` and an e-mail "New lead <id>". CloudWatch → Log groups
   → `/aws/lambda/inocube-backend-leads` shows retention 1 month and the request.
6. Optional cleanup: the old groups `/aws/lambda/inocube-backend-*Function-*` get no new logs; set their
   retention to 30 days or delete them (they are not in the stack).
7. Changing `NotifyEmail` later: verify the new address and add its identity ARN to the boundary first.
   On AccessDenied during deploy: T-003 step 10/11.

## Implementation notes
- Branch `feat/T-004-leads-hardening`; PR opened by the orchestrator. Local: ruff clean, pytest green,
  SAM CLI 1.168.0 `sam validate --lint` and `sam build` pass. Nothing was run against AWS.
- **CORS in the Lambda** (`src/leads/cors.py`) with an `OPTIONS /leads` route: API Gateway CORS takes only exact
  origins, not `deploy-preview-<n>--…`. Errors API Gateway makes itself (429, 403, 5xx) get a fixed
  `https://inocube.sk` header via `GatewayResponses` (previews see a CORS error on those).
- **Throttling/CORS via `Globals.Api`** so the implicit `ServerlessRestApi` (and its URL) stays; stage update is
  `apigateway:PATCH`, gateway responses are part of the API body (`PUT`), both already allowed.
- **Log groups**: new stack-managed `/aws/lambda/inocube-backend-{health,leads}` (30 days) wired via
  `LoggingConfig.LogGroup`. Reusing the Lambda-created names would fail with AlreadyExists. Names match the
  deploy policy and the boundary prefix. The CloudFormation LogGroup handler also reads data-protection, index
  and resource policies, hence the deploy-policy edit (from the cfn-lint resource schema; untested in AWS).
- **SES**: inline `ses:SendEmail` on `identity/inocube.sk` + `identity/<NotifyEmail>` (no SESCrudPolicy). In the
  sandbox SES also authorizes against the recipient identity, so role and boundary allow it. No configuration
  set is used; adding one (or a default one on the identity) needs its ARN in role and boundary.
- **Honeypot** is checked before validation (bots learn nothing). **Control characters**: Unicode `Cc` checked
  before trimming; `message` allows `\n`, `\r` (CRLF) and `\t`. E-mail failures log lead id + AWS error code
  only (SES messages can contain addresses); no traceback, so the broad `except` has `noqa: BLE001`.
- Not done (scope): POSTs from foreign origins are still processed (CORS only stops browsers reading the
  answer); duplicate submissions; `www.inocube.sk` not allowed. Follow-up: `ses:FromAddress` condition.

## Architect review
(architect)
