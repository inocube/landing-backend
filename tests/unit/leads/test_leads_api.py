import json
import logging
import re

import app
import pytest

VALID_LEAD = {
    "name": "Jana Testovacia",
    "email": "Jana.Testovacia@Example.COM",
    "message": "Mam zaujem o spolupracu na novom webe.",
}
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def post(body):
    raw = body if isinstance(body, str) or body is None else json.dumps(body)
    response = app.lambda_handler(
        {"httpMethod": "POST", "path": "/leads", "body": raw}, None
    )
    return response["statusCode"], json.loads(response["body"])


def all_items(table):
    return table.scan()["Items"]


def test_valid_lead_is_stored_with_correct_keys(leads_table):
    status, body = post(VALID_LEAD)

    assert status == 201
    assert body["status"] == "NEW"
    lead_id = body["lead_id"]
    item = leads_table.get_item(Key={"PK": f"LEAD#{lead_id}", "SK": f"LEAD#{lead_id}"})[
        "Item"
    ]
    assert ISO_UTC.match(item["created_at"])
    assert item == {
        "PK": f"LEAD#{lead_id}",
        "SK": f"LEAD#{lead_id}",
        "GSI1PK": "LEAD",
        "GSI1SK": item["created_at"],
        "GSI2PK": "EMAIL#jana.testovacia@example.com",
        "GSI2SK": item["created_at"],
        "lead_id": lead_id,
        "name": "Jana Testovacia",
        "email": item["email"],
        "message": VALID_LEAD["message"],
        "created_at": item["created_at"],
        "status": "NEW",
    }
    assert item["email"].lower() == "jana.testovacia@example.com"


def test_stored_lead_is_found_via_both_indexes(leads_table):
    _, body = post(VALID_LEAD)

    by_date = leads_table.query(
        IndexName="GSI1",
        KeyConditionExpression="GSI1PK = :pk",
        ExpressionAttributeValues={":pk": "LEAD"},
    )["Items"]
    by_email = leads_table.query(
        IndexName="GSI2",
        KeyConditionExpression="GSI2PK = :pk",
        ExpressionAttributeValues={":pk": "EMAIL#jana.testovacia@example.com"},
    )["Items"]
    assert [i["lead_id"] for i in by_date] == [body["lead_id"]]
    assert [i["lead_id"] for i in by_email] == [body["lead_id"]]


def test_whitespace_is_stripped_and_unknown_fields_ignored(leads_table):
    lead = {
        "name": "  Jana  ",
        "email": " jana@example.com ",
        "message": "\n Ahoj \t",
        "website": "",
        "status": "DONE",
    }
    status, _ = post(lead)

    assert status == 201
    (item,) = all_items(leads_table)
    assert (item["name"], item["email"], item["message"]) == (
        "Jana",
        "jana@example.com",
        "Ahoj",
    )
    assert "website" not in item
    assert item["status"] == "NEW"


def test_boundary_lengths_are_accepted(leads_table):
    status, _ = post({**VALID_LEAD, "name": "n" * 200, "message": "m" * 5000})
    assert status == 201


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"name": None}, "name"),
        ({"name": ""}, "name"),
        ({"name": "   "}, "name"),
        ({"name": "n" * 201}, "name"),
        ({"name": 123}, "name"),
        ({"email": "not-an-email"}, "email"),
        ({"email": "a@b@example.com"}, "email"),
        ({"email": ""}, "email"),
        ({"message": ""}, "message"),
        ({"message": " \n\t "}, "message"),
        ({"message": "m" * 5001}, "message"),
    ],
)
def test_invalid_field_returns_400(leads_table, override, field):
    lead = {**VALID_LEAD, **override}
    status, body = post(lead)

    assert status == 400
    assert body["error"] == "Invalid input"
    assert [d["field"] for d in body["details"]] == [field]
    assert all_items(leads_table) == []


@pytest.mark.parametrize("missing", ["name", "email", "message"])
def test_missing_field_returns_400(leads_table, missing):
    lead = {k: v for k, v in VALID_LEAD.items() if k != missing}
    status, body = post(lead)

    assert status == 400
    assert body["details"] == [{"field": missing, "message": "Field required"}]


@pytest.mark.parametrize("raw", ["[1, 2]", '"just a string"', "null"])
def test_non_object_json_returns_400(leads_table, raw):
    status, body = post(raw)

    assert status == 400
    assert body["details"][0]["field"] == "body"


@pytest.mark.parametrize("raw", ["{not json", "", None])
def test_invalid_json_returns_400(leads_table, raw):
    status, body = post(raw)

    assert status == 400
    assert body == {"error": "Invalid JSON body", "details": []}


def test_400_details_never_echo_input(leads_table):
    secret_email = "secret-person!!@@weird-domain.example"
    status, body = post({**VALID_LEAD, "email": secret_email, "name": "x" * 201})

    assert status == 400
    raw = json.dumps(body)
    assert "secret-person" not in raw
    assert "weird-domain" not in raw
    assert "x" * 201 not in raw


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"name": "Jana\x00"}, "name"),
        ({"name": "Jana\nNovak"}, "name"),
        ({"name": "Jana\t"}, "name"),
        ({"name": "\x1fJana"}, "name"),
        ({"name": "Jana\x7f"}, "name"),
        ({"name": "Jana\x85"}, "name"),
        ({"email": "jana@example.com\r\nBcc: x@example.com"}, "email"),
        ({"email": "jana\x00@example.com"}, "email"),
        ({"message": "Ahoj\x00"}, "message"),
        ({"message": "Ahoj\x1b[31m"}, "message"),
        ({"message": "Ahoj\x0b"}, "message"),
        # Cf (bidi override, zero-width space, BOM), Zl and Zp
        ({"name": "Jana\u202egpj.exe"}, "name"),
        ({"name": "Ja\u200bna"}, "name"),
        ({"name": "Jana\u200d"}, "name"),
        ({"name": "\ufeffJana"}, "name"),
        ({"name": "Jana\u2028Novak"}, "name"),
        ({"name": "Jana\u2029"}, "name"),
        ({"email": "jana\u202e@example.com"}, "email"),
        ({"message": "Ahoj\u202e"}, "message"),
        ({"message": "Ahoj\u2066x\u2069"}, "message"),
        ({"message": "Ahoj\u200b"}, "message"),
        ({"message": "Ahoj\u2028svet"}, "message"),
        ({"message": "Ahoj\u2029svet"}, "message"),
    ],
)
def test_control_characters_return_400(leads_table, override, field):
    status, body = post({**VALID_LEAD, **override})

    assert status == 400
    assert body["details"] == [
        {"field": field, "message": "must not contain control or formatting characters"}
    ]
    assert all_items(leads_table) == []


@pytest.mark.parametrize(
    "message",
    [
        "Rodina \U0001f468\u200d\U0001f469\u200d\U0001f467 a vlajka \U0001f3f3\ufe0f\u200d\U0001f308",
        "Dobr\u00fd de\u0148, \u017eelezni\u010dn\u00e1 stanica, na\u00adkladanie",
        "\u0645\u06cc\u200c\u062e\u0648\u0627\u0647\u0645",
    ],
)
def test_message_keeps_normal_unicode_text(leads_table, message):
    status, _ = post(
        {**VALID_LEAD, "name": "\u017dofia \u0160\u0165astn\u00e1", "message": message}
    )

    assert status == 201
    (item,) = all_items(leads_table)
    assert item["message"] == message


def test_message_keeps_newlines_and_tabs(leads_table):
    message = "Dobry den,\r\nmam zaujem:\n\t- web\n\t- e-shop"
    status, _ = post({**VALID_LEAD, "message": message})

    assert status == 201
    (item,) = all_items(leads_table)
    assert item["message"] == message


@pytest.mark.parametrize("website", ["http://spam.example", "  x ", 1, ["a"], True])
def test_honeypot_returns_fake_201_and_stores_nothing(
    leads_table, outbox, caplog, website
):
    caplog.set_level(logging.INFO)
    status, body = post({**VALID_LEAD, "website": website})

    assert status == 201
    assert body["status"] == "NEW"
    assert re.fullmatch(r"[0-9a-f-]{36}", body["lead_id"])
    assert all_items(leads_table) == []
    assert outbox == []
    assert "Lead dropped: honeypot" in caplog.text


def test_honeypot_hit_skips_validation(leads_table):
    # A bot never learns the validation rules: even invalid input gets the fake success.
    status, _ = post({"website": "spam", "email": "not-an-email"})

    assert status == 201
    assert all_items(leads_table) == []


@pytest.mark.parametrize("website", ["", "   ", None, False, 0])
def test_empty_honeypot_is_a_normal_lead(leads_table, website):
    status, _ = post({**VALID_LEAD, "website": website})

    assert status == 201
    assert len(all_items(leads_table)) == 1


def test_storage_failure_returns_500(mocked_aws):
    # No table exists in moto, so put_item fails with ResourceNotFoundException.
    status, body = post(VALID_LEAD)

    assert status == 500
    assert body == {"error": "Internal server error"}


def test_logs_contain_no_personal_data(leads_table, mocked_aws, caplog):
    caplog.set_level(logging.INFO)
    pii = [
        VALID_LEAD["name"],
        "Jana",
        "Testovacia",
        "jana.testovacia",
        "example.com",
        "spolupracu",
    ]

    ok_status, ok_body = post(VALID_LEAD)
    bad_status, _ = post({**VALID_LEAD, "email": "jana.testovacia@@example.com"})
    leads_table.delete()
    fail_status, _ = post(VALID_LEAD)

    assert (ok_status, bad_status, fail_status) == (201, 400, 500)
    logs = "\n".join(
        record.getMessage() + (record.exc_text or "") for record in caplog.records
    )
    assert ok_body["lead_id"] in logs
    for value in pii:
        assert value.lower() not in logs.lower()
