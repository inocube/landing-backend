# T-004: Harden POST /leads for the public website form

- Status: ready
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
(implementer)

## Implementation notes
(implementer)

## Architect review
(architect)
