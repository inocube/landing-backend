import json

import app
import pytest

VALID_LEAD = {"name": "Jana", "email": "jana@example.com", "message": "Ahoj"}
ALLOWED = [
    "https://inocube.sk",
    "https://deploy-preview-1--inocube-public.netlify.app",
    "https://deploy-preview-123--inocube-public.netlify.app",
]
DISALLOWED = [
    "https://evil.example",
    "http://inocube.sk",
    "https://www.inocube.sk",
    "https://inocube.sk.evil.example",
    "https://inocube.sk:8443",
    "https://deploy-preview-x--inocube-public.netlify.app",
    "https://deploy-preview-1--inocube-public.netlify.app.evil.example",
    "https://evil--inocube-public.netlify.app",
    "https://deploy-preview-1--other-site.netlify.app",
    "null",
    "",
]


def call(method, origin=None, body=None, header_name="origin"):
    headers = {header_name: origin} if origin is not None else None
    event = {"httpMethod": method, "path": "/leads", "headers": headers, "body": body}
    return app.lambda_handler(event, None)


@pytest.mark.parametrize("origin", ALLOWED)
def test_preflight_from_allowed_origin(origin):
    response = call("OPTIONS", origin)

    assert response["statusCode"] == 204
    assert response["headers"] == {
        "Vary": "Origin",
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "600",
    }


@pytest.mark.parametrize("origin", [*DISALLOWED, None])
def test_preflight_from_other_origin_gets_no_cors_headers(origin):
    response = call("OPTIONS", origin)

    assert response["statusCode"] == 204
    assert response["headers"] == {"Vary": "Origin"}


def test_origin_header_is_matched_case_insensitively():
    response = call("OPTIONS", "https://inocube.sk", header_name="Origin")

    assert response["headers"]["Access-Control-Allow-Origin"] == "https://inocube.sk"


@pytest.mark.parametrize("origin", ALLOWED)
def test_post_from_allowed_origin_echoes_origin(leads_table, origin):
    response = call("POST", origin, json.dumps(VALID_LEAD))

    assert response["statusCode"] == 201
    assert response["headers"]["Access-Control-Allow-Origin"] == origin
    assert response["headers"]["Vary"] == "Origin"


@pytest.mark.parametrize("origin", DISALLOWED)
def test_post_from_other_origin_gets_no_allow_origin(leads_table, origin):
    response = call("POST", origin, json.dumps(VALID_LEAD))

    assert "Access-Control-Allow-Origin" not in response["headers"]
    assert response["headers"]["Vary"] == "Origin"


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ("{not json", 400),
        (json.dumps({**VALID_LEAD, "email": "x"}), 400),
        (json.dumps({**VALID_LEAD, "website": "spam"}), 201),
    ],
)
def test_cors_headers_on_every_outcome(leads_table, body, status):
    response = call("POST", "https://inocube.sk", body)

    assert response["statusCode"] == status
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://inocube.sk"


def test_cors_headers_on_storage_failure(mocked_aws):
    response = call("POST", "https://inocube.sk", json.dumps(VALID_LEAD))

    assert response["statusCode"] == 500
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://inocube.sk"
