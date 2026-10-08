"""DynamoDB access for leads. Key formats: see AGENTS.md (DynamoDB key design)."""

import os
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import boto3
from models import LeadCreate

LEAD_STATUS_NEW = "NEW"


@lru_cache(maxsize=1)
def _table() -> Any:
    """Create the boto3 Table lazily (first call, not at import) and reuse it on warm invocations.

    Lazy creation lets tests set up moto before any client exists. An optional ``DYNAMODB_ENDPOINT``
    points boto3 at DynamoDB Local; empty or unset means the real AWS endpoint.
    """
    endpoint_url = os.environ.get("DYNAMODB_ENDPOINT") or None
    dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url)
    return dynamodb.Table(os.environ["TABLE_NAME"])


def build_item(lead: LeadCreate, lead_id: str, created_at: str) -> dict[str, str]:
    """Map a validated lead to its single-table DynamoDB item."""
    return {
        "PK": f"LEAD#{lead_id}",
        "SK": f"LEAD#{lead_id}",
        "GSI1PK": "LEAD",
        "GSI1SK": created_at,
        "GSI2PK": f"EMAIL#{lead.email.lower()}",
        "GSI2SK": created_at,
        "lead_id": lead_id,
        "name": lead.name,
        "email": lead.email,
        "message": lead.message,
        "created_at": created_at,
        "status": LEAD_STATUS_NEW,
    }


def save_lead(lead: LeadCreate) -> dict[str, str]:
    """Store a new lead and return its ``lead_id`` and ``status``.

    Raises botocore errors on storage failure; the handler turns them into a 500.
    """
    lead_id = str(uuid.uuid4())
    created_at = (
        datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )
    _table().put_item(
        Item=build_item(lead, lead_id, created_at),
        # Never overwrite an existing item, even in the (practically impossible) case of a uuid clash.
        ConditionExpression="attribute_not_exists(PK)",
    )
    return {"lead_id": lead_id, "status": LEAD_STATUS_NEW}
