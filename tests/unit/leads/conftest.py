"""Fixtures for the leads function.

Lambda runs the leads code with ``src/leads/`` as its root, so the code uses flat imports
(``from models import ...``). Putting that folder on ``sys.path`` lets the tests import it the same way.
"""

import json
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "leads"))

TABLE_NAME = "inocube-leads"
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
    import repository  # imported here, after src/leads is on sys.path

    repository._table.cache_clear()
    yield
    repository._table.cache_clear()


@pytest.fixture
def mocked_aws(aws_env):
    """moto-backed AWS without any table (use for storage-failure tests)."""
    with mock_aws():
        yield


@pytest.fixture
def leads_table(mocked_aws):
    """moto table created from the same schema used for DynamoDB Local."""
    schema = json.loads(TABLE_SCHEMA.read_text(encoding="utf-8"))
    client = boto3.client("dynamodb")
    client.create_table(**schema)
    return boto3.resource("dynamodb").Table(TABLE_NAME)
