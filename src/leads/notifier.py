"""Owner notification e-mail for a new lead, sent with Amazon SES (API v2)."""

import logging
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from models import LeadCreate

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# The lead is stored before the e-mail is sent, so the e-mail must finish well inside the Lambda timeout.
# botocore's defaults (60 s timeouts, up to 5 attempts) could time the Lambda out; the browser would see 502,
# retry, and the lead would be stored twice. ``total_max_attempts`` counts the first try (botocore's
# ``max_attempts`` counts retries only, so ``max_attempts: 2`` would mean 3 calls). Worst case here:
# 2 x (2 s connect + 3 s read) + under 1 s backoff, about 11 s; LeadsFunction has a 15 s timeout for that.
SES_CLIENT_CONFIG = Config(
    connect_timeout=2,
    read_timeout=3,
    retries={"mode": "standard", "total_max_attempts": 2},
)


@lru_cache(maxsize=1)
def _ses() -> Any:
    """SES v2 client, created lazily (after moto is set up in tests) and reused on warm invocations."""
    return boto3.client("sesv2", config=SES_CLIENT_CONFIG)


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


def reply_to_address(email: str) -> str | None:
    """The lead's address as SES accepts it in Reply-To: ASCII local part, punycode domain; else ``None``.

    The address is already validated (``EmailStr``); a non-ASCII local part cannot be sent without SMTPUTF8,
    so the mail then goes out without Reply-To rather than failing.
    """
    local, _, domain = email.rpartition("@")
    try:
        local.encode("ascii")
        return f"{local}@{domain.encode('idna').decode('ascii')}"
    except UnicodeError:
        return None


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
    request: dict[str, Any] = {
        "FromEmailAddress": sender,
        "Destination": {"ToAddresses": [recipient]},
        "Content": {
            "Simple": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            }
        },
    }
    # The owner answers the lead from the mail client; still a manual reply (ADR 0007).
    reply_to = reply_to_address(lead.email)
    if reply_to:
        request["ReplyToAddresses"] = [reply_to]
    try:
        _ses().send_email(**request)
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
