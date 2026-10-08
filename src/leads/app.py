"""POST /leads: HTTP layer only. Validation lives in models.py, storage in repository.py."""

import json
import logging
from typing import Any

from models import LeadCreate
from pydantic import ValidationError
from repository import save_lead

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Some validators (e-mail) put parts of the input into their message; replace those with fixed text.
_SAFE_MESSAGES = {"value_error": "value is not a valid email address"}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # Logs carry IDs and outcomes only, never names, e-mails or message bodies (GDPR).
    try:
        payload = json.loads(event.get("body") or "")
    except (TypeError, ValueError):
        logger.info("Lead rejected: invalid JSON body")
        return _response(400, {"error": "Invalid JSON body", "details": []})

    try:
        lead = LeadCreate.model_validate(payload)
    except ValidationError as exc:
        details = _validation_details(exc)
        logger.info(
            "Lead rejected: invalid fields %s", sorted({d["field"] for d in details})
        )
        return _response(400, {"error": "Invalid input", "details": details})

    try:
        result = save_lead(lead)
    except Exception:
        logger.exception("Lead storage failed")
        return _response(500, {"error": "Internal server error"})

    logger.info("Lead stored: lead_id=%s", result["lead_id"])
    return _response(201, result)


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


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
