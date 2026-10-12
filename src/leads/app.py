"""POST /leads (+ OPTIONS preflight): HTTP layer only.

CORS in cors.py, validation in models.py, storage in repository.py, owner e-mail in notifier.py.
"""

import json
import logging
import uuid
from typing import Any

from cors import cors_headers, preflight_headers, request_origin
from models import LeadCreate
from notifier import notify_owner
from pydantic import ValidationError
from repository import LEAD_STATUS_NEW, save_lead

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Some validators (e-mail) put parts of the input into their message; replace those with fixed text.
_SAFE_MESSAGES = {"value_error": "value is not a valid email address"}

# Hidden form field that humans leave empty and naive bots fill in.
HONEYPOT_FIELD = "website"


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Logs carry IDs and outcomes only, never names, e-mails or message bodies (GDPR).
    origin = request_origin(event)
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 204, "headers": preflight_headers(origin), "body": ""}
    headers = cors_headers(origin)

    try:
        payload = json.loads(event.get("body") or "")
    except (TypeError, ValueError):
        logger.info("Lead rejected: invalid JSON body")
        return _response(400, {"error": "Invalid JSON body", "details": []}, headers)

    if _honeypot_filled(payload):
        # Look like a success so the bot does not adapt; store nothing, send nothing.
        logger.info("Lead dropped: honeypot")
        fake = {"lead_id": str(uuid.uuid4()), "status": LEAD_STATUS_NEW}
        return _response(201, fake, headers)

    try:
        lead = LeadCreate.model_validate(payload)
    except ValidationError as exc:
        details = _validation_details(exc)
        logger.info(
            "Lead rejected: invalid fields %s", sorted({d["field"] for d in details})
        )
        return _response(400, {"error": "Invalid input", "details": details}, headers)

    try:
        result = save_lead(lead)
    except Exception:
        logger.exception("Lead storage failed")
        return _response(500, {"error": "Internal server error"}, headers)

    logger.info("Lead stored: lead_id=%s", result["lead_id"])
    # Best effort: a failed e-mail is logged inside notify_owner and never turns the 201 into an error.
    notify_owner(lead, result["lead_id"])
    return _response(201, result, headers)


def _honeypot_filled(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    value = payload.get(HONEYPOT_FIELD)
    if isinstance(value, str):
        return value.strip() != ""
    return bool(value)  # a bot may send a number or list; null, false, 0 count as empty


def _validation_details(exc: ValidationError) -> list[dict[str, str]]:
    """Field names and messages only; the submitted values are never echoed back."""
    details = []
    for error in exc.errors(
        include_url=False, include_context=False, include_input=False
    ):
        field = ".".join(str(part) for part in error["loc"]) or "body"
        message = _SAFE_MESSAGES.get(error["type"], error["msg"])
        details.append({"field": field, "message": message})
    return details


def _response(
    status_code: int, body: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **headers},
        "body": json.dumps(body),
    }
