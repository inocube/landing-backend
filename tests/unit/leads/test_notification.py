import json
import logging

import app
import pytest

VALID_LEAD = {
    "name": "Jana Testovacia",
    "email": "jana.testovacia@example.com",
    "message": "Mam zaujem o spolupracu.\nDakujem, Jana",
}
PII = ["Jana", "Testovacia", "jana.testovacia", "example.com", "spolupracu", "owner@"]


def post(body):
    event = {"httpMethod": "POST", "path": "/leads", "body": json.dumps(body)}
    response = app.lambda_handler(event, None)
    return response["statusCode"], json.loads(response["body"])


def log_text(caplog):
    return "\n".join(r.getMessage() + (r.exc_text or "") for r in caplog.records)


def test_stored_lead_sends_one_email_to_owner(leads_table, ses_domain, outbox):
    status, body = post(VALID_LEAD)

    assert status == 201
    (email,) = outbox
    assert email.source == "noreply@inocube.sk"
    assert email.destinations == {"ToAddresses": ["owner@example.org"]}
    assert email.subject == f"New lead {body['lead_id']}"
    assert f"Lead ID: {body['lead_id']}" in email.body
    assert "Name: Jana Testovacia" in email.body
    assert "E-mail: jana.testovacia@example.com" in email.body
    assert VALID_LEAD["message"] in email.body


def test_each_lead_sends_its_own_email(leads_table, ses_domain, outbox):
    ids = [post(VALID_LEAD)[1]["lead_id"] for _ in range(2)]

    assert [e.subject for e in outbox] == [f"New lead {i}" for i in ids]


def test_ses_failure_still_returns_201_and_logs_id_only(leads_table, outbox, caplog):
    # No verified identity in moto: SES rejects the send (MessageRejected), as in a misconfigured account.
    caplog.set_level(logging.INFO)
    status, body = post(VALID_LEAD)

    assert status == 201
    assert len(leads_table.scan()["Items"]) == 1
    assert outbox == []
    logs = log_text(caplog)
    assert (
        f"Lead notification failed: lead_id={body['lead_id']} error=MessageRejected"
        in logs
    )
    for value in PII:
        assert value.lower() not in logs.lower()


def test_unexpected_notification_error_still_returns_201(
    leads_table, monkeypatch, caplog
):
    import notifier

    def network_down(**kwargs):
        raise TimeoutError("network down")

    monkeypatch.setattr(notifier._ses(), "send_email", network_down)
    caplog.set_level(logging.INFO)
    status, body = post(VALID_LEAD)

    assert status == 201
    assert f"lead_id={body['lead_id']} error=TimeoutError" in log_text(caplog)


@pytest.mark.parametrize("unset", ["NOTIFY_TO", "NOTIFY_FROM"])
def test_notification_skipped_when_not_configured(
    leads_table, ses_domain, outbox, monkeypatch, unset
):
    monkeypatch.setenv(unset, "")
    status, _ = post(VALID_LEAD)

    assert status == 201
    assert outbox == []


@pytest.mark.parametrize(
    "lead", [{**VALID_LEAD, "email": "bad"}, {**VALID_LEAD, "website": "spam"}]
)
def test_no_email_for_rejected_or_honeypot_leads(leads_table, ses_domain, outbox, lead):
    post(lead)

    assert outbox == []


def test_no_email_when_storage_fails(mocked_aws, ses_domain, outbox):
    status, _ = post(VALID_LEAD)

    assert status == 500
    assert outbox == []


def test_success_logs_contain_no_personal_data(leads_table, ses_domain, caplog):
    caplog.set_level(logging.INFO)
    _, body = post(VALID_LEAD)

    logs = log_text(caplog)
    assert f"Lead notification sent: lead_id={body['lead_id']}" in logs
    for value in PII:
        assert value.lower() not in logs.lower()
