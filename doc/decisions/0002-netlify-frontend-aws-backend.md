# 0002. Frontend stays on Netlify, backend on AWS

- Status: Accepted
- Date: 2026-07-02

## Context
inocube.sk is a static site on Netlify (domain at Websupport). Moving it to S3 + CloudFront adds cost and
work with no benefit for the goals.

## Decision
Keep the frontend on Netlify. Build only the backend on AWS and expose it via API Gateway
(later `api.inocube.sk`).

## Consequences
Cross-origin calls: CORS must be configured and kept tight. Two deploy pipelines (Netlify, GitHub Actions).
