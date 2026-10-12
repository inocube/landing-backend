"""Fixtures for the leads function.

Lambda runs the leads code with ``src/leads/`` as its root, so the code uses flat imports
(``from models import ...``). Putting that folder on ``sys.path`` lets the tests import it the same way.
"""

import json
import sys
from pathlib import Path
from typing import Any

import boto3
import pytest
from moto import mock_aws

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "leads"))

TABLE_NAME = "inocube-leads"
NOTIFY_FROM = "noreply@inocube.sk"
NOTIFY_TO = "owner@example.org"
TABLE_SCHEMA = REPO_ROOT / "local-test" / "table-schema.json"


@pytest.fixture
def aws_env(monkeypatch):
    """Fake credentials and region so nothing can ever reach a real AWS account."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("DYNAMODB_ENDPOINT", raising=False)
    monkeypatch.setenv("TABLE_NAME", TABLE_NAME)
    monkeypatch.setenv("NOTIFY_FROM", NOTIFY_FROM)
    monkeypatch.setenv("NOTIFY_TO", NOTIFY_TO)
    import notifier  # imported here, after src/leads is on sys.path
    import repository

    repository._table.cache_clear()
    notifier._ses.cache_clear()
    yield
    repository._table.cache_clear()
    notifier._ses.cache_clear()


@pytest.fixture
def mocked_aws(aws_env):
    """moto-backed AWS without any table (use for storage-failure tests)."""
    with mock_aws():
        yield


@pytest.fixture
def ses_domain(mocked_aws):
    """Verified SES domain identity ``inocube.sk`` in moto, so sending from noreply@inocube.sk succeeds.

    Without this fixture moto rejects the send (unverified sender), which is how tests simulate an SES failure.
    """
    boto3.client("sesv2").create_email_identity(EmailIdentity="inocube.sk")


@pytest.fixture
def outbox(mocked_aws) -> list[Any]:
    """Live list of messages moto's SES backend accepted (SES v2 sends are recorded by the v1 backend)."""
    from moto.core import DEFAULT_ACCOUNT_ID
    from moto.ses.models import ses_backends

    return ses_backends[DEFAULT_ACCOUNT_ID]["eu-central-1"].sent_messages


@pytest.fixture
def leads_table(mocked_aws):
    """moto table created from the same schema used for DynamoDB Local."""
    schema = json.loads(TABLE_SCHEMA.read_text(encoding="utf-8"))
    client = boto3.client("dynamodb")
    client.create_table(**schema)
    return boto3.resource("dynamodb").Table(TABLE_NAME)
