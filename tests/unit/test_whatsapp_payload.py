from factories import whatsapp_text_payload

from messaging.whatsapp_payload import WebhookPayload


def test_extracts_text_message_with_sender_name() -> None:
    payload = WebhookPayload.model_validate(whatsapp_text_payload("wamid.1", body="Hola"))

    (message,) = payload.inbound_messages()

    assert message.provider_message_id == "wamid.1"
    assert message.sender_phone == "5215550000001"
    assert message.sender_name == "Ana"
    assert message.type == "text"
    assert message.body == "Hola"
    assert message.raw["from"] == "5215550000001"


def test_extracts_every_message_of_a_batch() -> None:
    raw = whatsapp_text_payload("wamid.1")
    second = whatsapp_text_payload("wamid.2")["entry"][0]["changes"][0]["value"]["messages"][0]
    raw["entry"][0]["changes"][0]["value"]["messages"].append(second)

    ids = [m.provider_message_id for m in WebhookPayload.model_validate(raw).inbound_messages()]

    assert ids == ["wamid.1", "wamid.2"]


def test_non_text_message_has_no_body() -> None:
    raw = whatsapp_text_payload("wamid.1")
    message = raw["entry"][0]["changes"][0]["value"]["messages"][0]
    message["type"] = "image"
    del message["text"]

    (parsed,) = WebhookPayload.model_validate(raw).inbound_messages()

    assert parsed.type == "image"
    assert parsed.body is None


def test_status_only_payload_has_no_messages() -> None:
    value = {"statuses": [{"id": "wamid.1", "status": "delivered"}]}
    payload = WebhookPayload.model_validate({"entry": [{"changes": [{"value": value}]}]})

    assert list(payload.inbound_messages()) == []
    (status,) = payload.status_updates()
    assert (status.provider_message_id, status.status) == ("wamid.1", "delivered")
