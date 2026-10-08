# T-001: POST /leads endpoint

- Status: review
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
(architect)
