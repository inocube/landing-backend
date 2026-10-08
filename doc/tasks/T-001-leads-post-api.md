# T-001: POST /leads endpoint

- Status: approved
- Roadmap phase: 2
- Branch: feat/T-001-leads-post-api

## Goal
The API accepts a contact-form lead, validates it and stores it in DynamoDB, with unit tests. After this task
the backend is ready for the website form to be connected (phase 2b).

## Context
- Table, keys and access patterns: `doc/architecture.md`, key formats in `AGENTS.md`, ADR 0005.
- Layered function layout and conventions: `AGENTS.md` → Code conventions.
- The owner's local clone may sit on the merged branch `feat/faza-1-dynamodb`; branch from fresh `main`.
- Phase 2b will add CORS, honeypot, throttling and SES. Do not add them here, but do not block them.

## Scope
1. New function `src/leads/` with `app.py` (HTTP), `models.py` (pydantic `LeadCreate`), `repository.py`
   (`save_lead`), `requirements.txt` (`pydantic`, `email-validator`; no boto3).
2. Validation: `name` 1–200 chars, `email` valid (`EmailStr`), `message` 1–5000 chars; strip whitespace;
   reject blank values; ignore unknown fields.
3. Storage: item per the key table in `AGENTS.md`; `lead_id` = uuid4, `created_at` = UTC ISO 8601,
   `status` = `NEW`; e-mail lowercased in `GSI2PK`.
4. boto3 client/resource created lazily (not at import) and honouring optional `DYNAMODB_ENDPOINT`, so
   tests and DynamoDB Local work.
5. Responses: `201 {"lead_id", "status"}`; `400 {"error", "details"}` for invalid JSON or fields (details
   list field names and messages, no input echo); `500 {"error"}` on storage failure.
6. `template.yaml`: `LeadsFunction` with `CodeUri: src/leads/`, env `TABLE_NAME: !Ref LeadsTable`,
   policy `DynamoDBWritePolicy` on `LeadsTable`, event `POST /leads` on the existing implicit API.
7. Tests in `tests/unit/leads/` (moto): valid lead stored with correct keys; each invalid case returns 400;
   invalid JSON returns 400; DynamoDB failure returns 500; nothing PII-like appears in captured logs.
   Leads code uses flat imports (`from models import ...`) because Lambda's root is `src/leads/`; make tests
   import it via a `conftest.py` that puts `src/leads` on `sys.path`.
8. Docs: update `doc/status.md`, the API section of `doc/architecture.md`, and `local-test/` with a sample
   POST body if useful.

## Acceptance criteria
- [ ] `pytest` passes locally, including the existing health test.
- [ ] `sam validate` and `sam build --use-container` succeed.
- [ ] `sam local start-api` + DynamoDB Local: `POST /leads` with a valid body returns 201 and the item is
      visible via a GSI1 query; invalid body returns 400.
- [ ] Lambda role can only write to `inocube-leads` (no read, no other tables).
- [ ] No names, e-mails or message bodies in logs.
- [ ] PR description includes "Why it is built this way" for the owner (layers, pydantic, policy template,
      lazy boto3, moto), plus PowerShell commands to verify locally.

## Out of scope
- `GET /leads` (needs authentication, later task), CORS, honeypot, throttling, SES, any deploy.

## Open questions
(none)

## Implementation notes
- Branch `feat/T-001-leads-post-api`; PR: https://github.com/inocube/landing-backend/compare/main...feat/T-001-leads-post-api?expand=1
- Verified: `pytest` 28 passed (incl. health); `sam validate --lint` valid; `sam build --use-container`
  succeeded (pydantic-core built as `aarch64-linux`); `sam local start-api` + DynamoDB Local: valid body 201
  and lead found via GSI1 query, invalid body / invalid JSON 400. Local cold starts under x86 emulation of
  arm64 exceeded the 10 s timeout, so that run used a temporary copy of the built template with
  Timeout 60 / 512 MB (not committed). Not an issue on real Graviton Lambda.
- Deviations / additions:
  - `DYNAMODB_ENDPOINT: ""` declared in `template.yaml`: `sam local --env-vars` only overrides variables the
    template declares. Empty means real AWS. Values for local use: `local-test/sam-local-env.json`.
  - `PutItem` uses `ConditionExpression attribute_not_exists(PK)` so a lead is never overwritten.
  - `created_at` has millisecond precision (`2026-10-08T15:28:15.083Z`) for stable GSI ordering.
  - 400 `details` replace the e-mail validator message with fixed text, because email-validator messages
    can quote parts of the input.
  - Tests build the moto table from `local-test/table-schema.json` (same schema as DynamoDB Local).

## Architect review
Verdict: approved

Re-run by architect: `pytest` 28 passed; `sam validate --lint` valid. `sam build` / `sam local` not re-run (taken
from implementation notes). All scope items 1–8 and acceptance criteria are met; no scope creep, no ADR conflict
(key design matches AGENTS.md / ADR 0005), no secrets, no deploy. Nothing blocking; findings below are
non-blocking and can go into this PR or a follow-up.

Findings (highest first):
1. Medium, exposure: `template.yaml:43` adds a public, unauthenticated write endpoint with no API throttling,
   no reserved concurrency and on-demand DynamoDB, so the cost and junk-data ceiling is unbounded until phase 2b.
   Acceptable only because the task defers throttling. Fix: do not deploy before 2b, or the owner explicitly
   accepts it (see questions).
2. Low, docs accuracy: `template.yaml:36` and `doc/architecture.md:61` say "no reads". `DynamoDBWritePolicy`
   grants `UpdateItem`/`PutItem`, and both can return the old item with `ReturnValues: ALL_OLD`, so the role can
   read an item whose key it knows. Real risk is low (uuid keys, code never asks for it). Fix: reword to
   "write actions only (no Get/Query/Scan)"; optionally a one-action inline `dynamodb:PutItem` policy later.
3. Low, robustness: `src/leads/app.py:15,52` maps every `value_error` to the e-mail message. Correct today
   (only `EmailStr` raises it), but a future custom validator on another field would get a wrong message.
   Fix: key the override on `(field, type)` or on `loc == ("email",)`.
4. Low, cold start/operability: `template.yaml:8` 128 MB with pydantic-core + `boto3.resource`
   (`src/leads/repository.py:23`) gives a slow first request (CPU scales with memory). Fix: measure
   `Init Duration` after deploy; consider 256 MB and `boto3.client` (lighter than the resource API).
5. Low, input hygiene: `src/leads/models.py:13-17` accepts control characters (e.g. `\x00`) in `name` and
   `message`. Harmless for storage, but phase 2b SES / any admin UI will render them. Fix (2b): reject or strip
   C0 control chars except `\n`, `\t`.
6. Nit, test strength: `tests/unit/leads/test_leads_api.py:47` asserts `"email": item["email"]` (tautology).
   Fix: assert the exact stored value `Jana.Testovacia@example.com` (EmailStr lowercases the domain only).
7. Nit, idempotency: a double-submitted form creates two leads; `ConditionExpression` (`repository.py:57`)
   only guards uuid collisions. Fine at this scale; 2b can dedupe via GSI2 or a client idempotency key.

Questions for the owner:
- Deploy `POST /leads` to prod before phase 2b (no throttling/CORS/honeypot), or wait for 2b?
- Add CloudWatch log retention (e.g. 30–90 days) for all functions in a follow-up? Default is never expire.
