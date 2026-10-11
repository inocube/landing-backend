"""CORS for /leads: which browser origin may call the API and the headers that tell the browser so.

Only the production site calls the API (owner decision: the apex domain, no ``www``; Netlify previews
never get the API URL). With a Lambda proxy integration the Lambda must set the CORS headers on its own
responses anyway, so the preflight is answered here too and the rule lives in one place.
"""

from typing import Any

ALLOWED_ORIGINS = frozenset({"https://inocube.sk"})
ALLOWED_METHODS = "POST, OPTIONS"
ALLOWED_HEADERS = "Content-Type"
PREFLIGHT_MAX_AGE_SECONDS = "600"


def request_origin(event: dict[str, Any]) -> str | None:
    """The ``Origin`` request header; API Gateway keeps the client's casing, so look it up case-insensitively."""
    for name, value in (event.get("headers") or {}).items():
        if name.lower() == "origin":
            return value
    return None


def is_allowed_origin(origin: str | None) -> bool:
    return origin in ALLOWED_ORIGINS


def cors_headers(origin: str | None) -> dict[str, str]:
    """Headers for every /leads response: echo the origin only if it is allowed.

    ``Vary: Origin`` is always set so a cache never serves one origin's answer to another.
    """
    headers = {"Vary": "Origin"}
    if is_allowed_origin(origin):
        headers["Access-Control-Allow-Origin"] = origin
    return headers


def preflight_headers(origin: str | None) -> dict[str, str]:
    """Answer to the browser's ``OPTIONS`` preflight; a disallowed origin gets no ``Access-Control-*``."""
    headers = cors_headers(origin)
    if "Access-Control-Allow-Origin" in headers:
        headers["Access-Control-Allow-Methods"] = ALLOWED_METHODS
        headers["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
        headers["Access-Control-Max-Age"] = PREFLIGHT_MAX_AGE_SECONDS
    return headers
