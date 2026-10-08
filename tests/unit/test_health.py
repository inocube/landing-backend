import json

from health import app


def test_health_returns_ok():
    response = app.lambda_handler({}, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["status"] == "ok"
