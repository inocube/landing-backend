# 0003. AWS SAM for infrastructure as code

- Status: Accepted
- Date: 2026-07-02

## Context
A small serverless stack (API Gateway, Lambda, DynamoDB) needs IaC, local testing and simple deploys.

## Decision
Use AWS SAM (`template.yaml`, `samconfig.toml`). All infrastructure is defined there; no console changes.

## Consequences
Fast start, `sam local` for local runs, built-in least-privilege policy templates. If the stack outgrows SAM,
CDK is the migration path (would need a new ADR).
