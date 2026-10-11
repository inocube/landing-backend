"""Owner notification e-mail for a new lead, sent with Amazon SES (API v2)."""

import logging
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError
from models import LeadCreate

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@lru_cache(maxsize=1)
def _ses() -> Any:
    """SES v2 client, created lazily (after moto is set up in tests) and reused on warm invocations."""
    return boto3.client("sesv2")


def build_email(lead: LeadCreate, lead_id: str) -> tuple[str, str]:
    """Subject and plain-text body. The subject carries only the lead id, never personal data."""
    subject = f"New lead {lead_id}"
    body = (
        "New lead from the inocube.sk contact form.\n\n"
        f"Lead ID: {lead_id}\n"
        f"Name: {lead.name}\n"
        f"E-mail: {lead.email}\n\n"
        f"Message:\n{lead.message}\n"
    )
    return subject, body


def notify_owner(lead: LeadCreate, lead_id: str) -> bool:
    """Send the notification; return whether it was sent. Never raises: the lead is already stored.

    ``NOTIFY_TO`` empty or unset (local runs) skips sending. Failures are logged with the lead id and the
    AWS error code only; SES error messages can contain addresses, so they are not logged.
    """
    sender = os.environ.get("NOTIFY_FROM") or ""
    recipient = os.environ.get("NOTIFY_TO") or ""
    if not sender or not recipient:
        logger.info("Lead notification skipped (not configured): lead_id=%s", lead_id)
        return False

    subject, body = build_email(lead, lead_id)
    try:
        _ses().send_email(
            FromEmailAddress=sender,
            Destination={"ToAddresses": [recipient]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                }
            },
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        logger.error("Lead notification failed: lead_id=%s error=%s", lead_id, code)
        return False
    # Deliberately broad: the lead is stored, so nothing here may turn the 201 into an error. No traceback is
    # logged because botocore messages can contain addresses; the exception type is enough to start debugging.
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Lead notification failed: lead_id=%s error=%s", lead_id, type(exc).__name__
        )
        return False

    logger.info("Lead notification sent: lead_id=%s", lead_id)
    return True
