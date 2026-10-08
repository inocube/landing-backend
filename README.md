# inocube landing-backend

Serverless backend for [inocube.sk](https://inocube.sk). It receives leads from the website contact form,
stores them in DynamoDB and (later) lets an AI layer triage them for the owner.

The frontend lives in a separate repo ([inocube/public](https://github.com/inocube/public), hosted on Netlify).

## Stack

Python 3.14 on AWS Lambda (arm64) · API Gateway (REST) · DynamoDB (single table) · AWS SAM (IaC) ·
IAM Identity Center (SSO) · region `eu-central-1`.

## Repository layout

| Path | What it is |
|---|---|
| `template.yaml` | The whole AWS stack (SAM). Single source of truth for infrastructure. |
| `samconfig.toml` | SAM deploy settings (stack name, region, profile). No secrets. |
| `src/<function>/` | One folder per Lambda: `app.py` handler + its `requirements.txt`. |
| `tests/unit/` | pytest unit tests (AWS mocked with moto). |
| `local-test/` | JSON fixtures for manual DynamoDB Local / CLI testing. |
| `doc/` | Goals, architecture, status, roadmap, decisions, agent tasks. Start at [`doc/README.md`](doc/README.md). |
| `AGENTS.md` | Rules for AI coding agents working in this repo. |

## Prerequisites

Python 3.14, AWS CLI v2, SAM CLI, Docker, an SSO login (`aws sso login --profile inocube`).

## Run locally

```powershell
cp .env.example .env                     # then adjust values
docker start dynamodb-local              # DynamoDB Local on :8000
sam build --use-container                # container build: Lambda is Linux/arm64
sam local start-api                      # API on http://127.0.0.1:3000
curl http://127.0.0.1:3000/health
```

## Test

```powershell
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```

## Deploy (manual until CI/CD exists)

```powershell
aws sso login --profile inocube
sam validate
sam build --use-container
sam deploy --profile inocube-deploy      # permission set that may create IAM roles
```

`main` is protected: every change goes through a pull request.
