# Goals

## Why this backend exists

1. **Business:** the inocube.sk contact form must actually deliver leads. Today it posts to a placeholder
   and nothing arrives. Every lead is a potential client for Inocube (AI and data integration services).
2. **Portfolio:** a public, production-grade example of serverless AWS + AI engineering by the owner.
   Reviewers (clients, employers) should see IaC, CI/CD, security and clean code.
3. **Learning:** the owner is building AWS skills (target: AWS certification + AI/agent work). Every PR
   explains the AWS concepts it uses.

## In scope

- Lead capture API for the website form (validate, store, notify the owner).
- AI triage of leads for the owner: summary, which service package fits, draft reply for approval.
- CI/CD from GitHub with OIDC (no stored AWS keys), staging and prod.
- Production hardening: least privilege, throttling, alarms, cost alerts, custom domain `api.inocube.sk`.
- Later: an AI assistant on the website answering questions about Inocube services (RAG).

## Out of scope (for now)

- Automatic AI replies sent to visitors (see ADR 0007).
- Admin UI. Leads are read via notification e-mail and the AWS console / CLI.
- Moving the frontend off Netlify.
- Multi-region, multi-account setups.

## Success criteria

- A form submission on inocube.sk reaches the owner within a minute, stored durably.
- Merge to `main` deploys automatically; no long-lived AWS credentials anywhere.
- Monthly AWS cost stays in single-digit euros at current traffic.
- No personal data in logs; EU region only.

## Related

Business strategy, service offering and website copy are in the owner's Claude project
("Inocube – prehľad dokumentov"). Frontend: [inocube/public](https://github.com/inocube/public).
