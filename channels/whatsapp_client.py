"""Envío de mensajes por WhatsApp Cloud API (Graph API de Meta)."""

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

MAX_TEXT_LENGTH = 4096  # límite de WhatsApp para un mensaje de texto


class WhatsAppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WHATSAPP_", env_file=".env", extra="ignore")
    token: str = ""  # access token (temporal de 24 h en pruebas; System User para producción)
    phone_number_id: str = ""  # ID del número que envía (no es el número en sí)
    verify_token: str = ""  # string que inventas tú; Meta lo envía al verificar el webhook
    app_secret: str = ""  # para validar la firma X-Hub-Signature-256
    graph_version: str = "v23.0"
    # Demo: tu número real no existe en los datos sintéticos. Si se define, todo mensaje entrante
    # se atiende como este cliente sintético (y tu número real no se guarda en tickets ni estado).
    demo_customer_phone: str = ""


class WhatsAppClient:
    def __init__(self, settings: WhatsAppSettings | None = None, http: httpx.Client | None = None) -> None:
        self.settings = settings or WhatsAppSettings()
        self.http = http or httpx.Client(
            base_url=f"https://graph.facebook.com/{self.settings.graph_version}",
            headers={"Authorization": f"Bearer {self.settings.token}"},
            timeout=10,
        )

    def _post_message(self, payload: dict) -> dict:
        response = self.http.post(f"/{self.settings.phone_number_id}/messages", json={"messaging_product": "whatsapp", **payload})
        response.raise_for_status()
        return response.json()

    def send_text(self, to: str, body: str) -> dict:
        return self._post_message({"to": to, "type": "text", "text": {"body": body[:MAX_TEXT_LENGTH]}})

    def mark_as_read(self, message_id: str) -> None:
        """Los dos ticks azules: el cliente sabe que su mensaje llegó mientras el agente piensa."""
        self._post_message({"status": "read", "message_id": message_id})
