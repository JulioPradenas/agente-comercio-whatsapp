"""Webhook de WhatsApp con payloads simulados de Meta, firmados como los firma Meta. Sin red ni LLM."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from channels.whatsapp_client import WhatsAppSettings
from channels.whatsapp_webhook import create_app

SETTINGS = WhatsAppSettings(verify_token="mi-token-secreto", app_secret="app-secret-de-prueba", demo_customer_phone="")
CUSTOMER = "56912345678"


class FakeWhatsApp:
    """Registra lo que se habría enviado a Meta."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.read: list[str] = []

    def send_text(self, to: str, body: str) -> None:
        self.sent.append((to, body))

    def mark_as_read(self, message_id: str) -> None:
        self.read.append(message_id)


def meta_payload(message: dict) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA_ID", "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "15550000000", "phone_number_id": "PHONE_ID"},
            "contacts": [{"profile": {"name": "Cliente"}, "wa_id": CUSTOMER}],
            "messages": [message],
        }}]}],
    }


def text_message(text: str, message_id: str = "wamid.1") -> dict:
    return meta_payload({"from": CUSTOMER, "id": message_id, "timestamp": "1763600000", "type": "text", "text": {"body": text}})


def signed_post(client: TestClient, payload: dict, secret: str = SETTINGS.app_secret):
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhook", content=body, headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"})


@pytest.fixture
def setup():
    calls: list[tuple[str, str]] = []

    def fake_agent(phone: str, text: str) -> str:
        calls.append((phone, text))
        return f"respuesta a: {text}"

    whatsapp = FakeWhatsApp()
    client = TestClient(create_app(agent=fake_agent, whatsapp=whatsapp, settings=SETTINGS))
    return client, whatsapp, calls


# --- Verificación (GET) ---


def test_verification_returns_challenge(setup):
    client, _, _ = setup
    params = {"hub.mode": "subscribe", "hub.verify_token": "mi-token-secreto", "hub.challenge": "1158201444"}
    response = client.get("/webhook", params=params)
    assert response.status_code == 200
    assert response.text == "1158201444"


def test_verification_rejects_wrong_token(setup):
    client, _, _ = setup
    params = {"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "1158201444"}
    assert client.get("/webhook", params=params).status_code == 403


# --- Mensajes (POST) ---


def test_text_message_is_answered(setup):
    client, whatsapp, calls = setup
    response = signed_post(client, text_message("hola"))
    assert response.status_code == 200
    assert calls == [(CUSTOMER, "hola")]
    assert whatsapp.sent == [(CUSTOMER, "respuesta a: hola")]
    assert whatsapp.read == ["wamid.1"]


def test_invalid_signature_is_rejected(setup):
    client, whatsapp, calls = setup
    response = signed_post(client, text_message("hola"), secret="secreto-de-un-atacante")
    assert response.status_code == 401
    assert calls == [] and whatsapp.sent == []


def test_missing_signature_is_rejected(setup):
    client, _, calls = setup
    assert client.post("/webhook", json=text_message("hola")).status_code == 401
    assert calls == []


def test_duplicate_message_is_processed_once(setup):
    client, whatsapp, calls = setup
    signed_post(client, text_message("hola", message_id="wamid.repetido"))
    signed_post(client, text_message("hola", message_id="wamid.repetido"))
    assert len(calls) == 1
    assert len(whatsapp.sent) == 1


def test_status_updates_are_ignored(setup):
    client, whatsapp, calls = setup
    payload = meta_payload({})
    payload["entry"][0]["changes"][0]["value"] = {"statuses": [{"id": "wamid.1", "status": "delivered"}]}
    assert signed_post(client, payload).status_code == 200
    assert calls == [] and whatsapp.sent == []


def test_audio_gets_text_only_notice(setup):
    client, whatsapp, calls = setup
    audio = meta_payload({"from": CUSTOMER, "id": "wamid.audio", "type": "audio", "audio": {"id": "MEDIA_ID"}})
    signed_post(client, audio)
    assert calls == []
    assert "solo puedo leer mensajes de texto" in whatsapp.sent[0][1]


def test_button_reply_is_treated_as_text(setup):
    client, _, calls = setup
    button = meta_payload({"from": CUSTOMER, "id": "wamid.btn", "type": "interactive",
                           "interactive": {"type": "button_reply", "button_reply": {"id": "confirm", "title": "Sí, comprar"}}})
    signed_post(client, button)
    assert calls == [(CUSTOMER, "Sí, comprar")]


def test_paused_bot_sends_nothing():
    whatsapp = FakeWhatsApp()
    client = TestClient(create_app(agent=lambda phone, text: "", whatsapp=whatsapp, settings=SETTINGS))
    signed_post(client, text_message("hola?"))
    assert whatsapp.sent == []


def test_demo_mode_maps_real_number_to_synthetic_customer():
    calls = []
    settings = SETTINGS.model_copy(update={"demo_customer_phone": "56989910085"})
    whatsapp = FakeWhatsApp()
    client = TestClient(create_app(agent=lambda phone, text: calls.append(phone) or "ok", whatsapp=whatsapp, settings=settings))
    signed_post(client, text_message("en qué va mi pedido?"))
    assert calls == ["56989910085"]  # el agente atiende al cliente sintético
    assert whatsapp.sent[0][0] == CUSTOMER  # pero la respuesta llega a tu número real
