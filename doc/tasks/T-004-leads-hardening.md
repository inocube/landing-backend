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
Before merging (the merge deploys prod; DKIM can take hours). AWS console as admin, `eu-central-1`.
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
- Local: ruff, pytest, SAM CLI 1.168.0 `sam validate --lint` and `sam build` pass. Nothing run against AWS.
- **CORS in the Lambda** (`src/leads/cors.py`) with an `OPTIONS /leads` route; with a proxy integration the
  Lambda sets the headers on its responses anyway. Allowed origin: exactly `https://inocube.sk` (owner decision
  after review: apex, no `www`; previews never call the API, so scope item 1's preview pattern was dropped).
  Errors API Gateway makes itself (429, 403, 5xx) get the same header via `GatewayResponses`.
- **Throttling via `Globals.Api`** so the implicit `ServerlessRestApi` (and its URL) stays. `/*` + `*` limits each
  method separately: POST /leads, OPTIONS /leads, GET /health 5 req/s (burst 10) each.
- **Log groups**: new stack-managed `/aws/lambda/inocube-backend-{health,leads}` (30 days) wired via
  `LoggingConfig.LogGroup` (Lambda-created names exist: AlreadyExists). The CloudFormation LogGroup handler also
  reads data-protection/index/resource policies: deploy-policy edit (from the cfn-lint schema; untested).
- **SES**: inline `ses:SendEmail` on `identity/inocube.sk` + `identity/<NotifyEmail>` (no SESCrudPolicy). In the
  sandbox SES also authorizes against the recipient identity, so role and boundary allow it. No configuration
  set. Reply-To = the lead's address (punycode domain; omitted for a non-ASCII local part). Client: 2 s connect,
  3 s read, `total_max_attempts: 2` (botocore's `max_attempts` counts retries, so 2 would mean 3 calls);
  worst case ~11 s, so `LeadsFunction` timeout is 15 s.
- **Honeypot** is checked before validation (bots learn nothing). **Characters**: Unicode `Cc`, `Cf`, `Zl`, `Zp`
  rejected on the raw value in all fields; `message` keeps `\n`, `\r`, `\t`, ZWJ/ZWNJ (emoji sequences, some
  scripts) and the soft hyphen (pasted text). Zero-width space, BOM and bidi controls are rejected.
  E-mail failures log lead id + AWS error code only. Not done: duplicate submissions; `ses:FromAddress` condition.

## Architect review
Verdict: changes-requested (one small fix; deploy path itself looks clean)

Checked: ruff clean, pytest 95 passed, `sam validate --lint` OK. SAM translator diff vs `origin/main`: same logical
IDs (`ServerlessRestApi`, `ServerlessRestApiProdStage`, roles, `LeadsTable` untouched), so the API id/URL stays;
changes are in-place updates (RestApi body PUT incl. gateway responses, Stage PATCH for MethodSettings, new
Deployment, new OPTIONS permission, inline `LeadsFunctionRolePolicy1` via `iam:PutRolePolicy` on a role that
already has the boundary, so the `iam:PermissionsBoundary` condition holds). Two new log groups match the
deploy-policy and boundary prefix `/aws/lambda/inocube-backend-*`; the boundary wildcard also covers
`...:log-stream:*` for CreateLogStream/PutLogEvents. SES role ∩ boundary = domain + recipient identity; X-Ray
unchanged. Without owner steps 3/4 the worst case is a clean rollback (log groups) or a logged
`AccessDenied` with 201 (SES), never data loss.

Findings
1. Medium - `src/leads/notifier.py:19`: SES client uses botocore defaults (legacy retries, 5 attempts with
   exponential backoff, 60 s connect/read timeouts) inside a 10 s Lambda. SES sandbox allows 1 mail/s while the
   API admits 5+/s, so `TooManyRequests` retries (worst case ~15 s) can time the Lambda out after the lead is
   stored: client gets 502, retries, duplicate lead. Fix: `Config(connect_timeout=2, read_timeout=3,
   retries={"mode": "standard", "max_attempts": 2})` and a test that the client is built with it.
2. Low - `template.yaml:25`, `doc/architecture.md:7,27`, `doc/status.md:22`: `/*` + `*` method settings throttle
   each method separately (POST /leads, OPTIONS /leads, GET /health: 5 req/s each), not "per stage". Fix the
   wording (or accept a ~15 req/s total cap knowingly).
3. Low - `src/leads/models.py:15`: only `Cc` is rejected; U+2028/U+2029 (`Zl`/`Zp`) and bidi/format chars
   (`Cf`, e.g. U+202E) pass into the owner e-mail and the stored name. Consider rejecting `Cf`/`Zl`/`Zp` in
   `name` (and `Zl`/`Zp` in `message`); optional.
4. Info - `src/leads/cors.py:13`: preview origins are allowed although the frontend only sets the API URL in
   Production, and Netlify builds previews for fork PRs of a public repo. Not a real risk (CORS does not stop
   server-side posts) but it is unused allowlist surface; keep only if previews will ever call the API.
5. Info - header injection: subject is the uuid only, From/To fixed, `email` checked for control chars before
   EmailStr; body is plain text. No PII in logs (tests assert it). Honeypot and SES-failure paths proven by tests.

Questions for the owner
- Is the site served on `https://inocube.sk` (apex) with `www` redirecting? If `www` is primary, the form fails
  CORS; add it to `ALLOWED_ORIGIN_PATTERNS` and the gateway responses.
- Set `Reply-To` to the lead's address so you can answer from your mail client? (structured SES field, no
  injection risk; still a manual reply per ADR 0007.)
- Order: do steps 1-4 before merge (DKIM can take hours); step 4 is likely needed by the LogGroup handler (untested), 1-3 only for e-mail.
