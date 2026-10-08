# 0001. Python for the backend

- Status: Accepted
- Date: 2026-07-02

## Context
The owner knows C# and Python. The project leads to AI work (Bedrock, RAG, agents), and a previous production
project used a Python Lambda with Bedrock.

## Decision
Backend Lambdas are written in Python. Runtime `python3.14` on arm64.

## Consequences
One language for API and AI layers; the AI ecosystem is Python-first; small cold starts. Compiled
dependencies need container builds (`sam build --use-container`).
