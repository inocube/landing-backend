# 0008. Secrets: .env for local only, SSM for deployed environments

- Status: Accepted
- Date: 2026-10-08

## Context
The repo is public. Local development needs a few settings; deployed Lambdas may later need secrets.

## Decision
- `.env` (git-ignored) holds local development values only; `.env.example` documents the variable names.
- Deployed environments read configuration from `template.yaml` parameters and secrets from AWS SSM
  Parameter Store (SecureString). No secret values in GitHub, the template or samconfig.

## Consequences
Leaking a laptop `.env` exposes no production secret. New secrets require an SSM parameter and a template
reference, documented in `.env.example` or `doc/architecture.md`.
