# 0007. AI triages leads for the owner, never replies to visitors automatically

- Status: Accepted
- Date: 2026-10-07

## Context
The original plan had Bedrock send an automatic reply to each lead. An automatic reply in the company's name
can invent promises or prices, and the EU AI Act (art. 50, from 2026-08-02) requires AI interactions to be
disclosed.

## Decision
The AI layer produces, for the owner only: a summary, the matching service package and a draft reply.
The owner reviews and sends the reply.

## Consequences
No hallucinated commitments reach clients; the owner stays in the loop. A public AI assistant on the website
is a separate, clearly labelled feature (roadmap phase 6).
