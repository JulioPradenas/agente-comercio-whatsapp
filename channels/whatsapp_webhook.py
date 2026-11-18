"""Webhook de WhatsApp Cloud API.

GET  /webhook  -> verificación de Meta (devuelve hub.challenge si el verify_token coincide)
POST /webhook  -> valida la firma, responde 200 de inmediato y procesa el mensaje en segundo plano

Uso local: uv run uvicorn channels.whatsapp_webhook:app --port 8000
"""

import hashlib
import hmac
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from channels.whatsapp_client import WhatsAppClient, WhatsAppSettings

AgentFn = Callable[[str, str], str]  # (teléfono, texto del cliente) -> respuesta ("" si el bot está en pausa)
UNSUPPORTED_MESSAGE = "Por ahora solo puedo leer mensajes de texto. ¿Me escribes tu consulta?"


@dataclass
class IncomingMessage:
    message_id: str
    sender: str  # wa_id: número en formato 569XXXXXXXX
    text: str | None  # None si es audio, imagen, etc.


def parse_messages(payload: dict) -> list[IncomingMessage]:
    """Extrae los mensajes del payload de Meta. Los avisos de estado (enviado, leído) se ignoran."""
    messages = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                if message["type"] == "text":
                    text = message["text"]["body"]
                elif message["type"] == "interactive":  # respuesta a un botón o a una lista
                    reply = message["interactive"].get("button_reply") or message["interactive"].get("list_reply")
                    text = reply["title"]
                else:
                    text = None
                messages.append(IncomingMessage(message_id=message["id"], sender=message["from"], text=text))
    return messages


def valid_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Meta firma el body con HMAC-SHA256 usando el App Secret: prueba que el POST viene de Meta."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))


class SeenMessages:
    """Recuerda los últimos IDs procesados: Meta puede reenviar el mismo mensaje."""

    def __init__(self, max_size: int = 5_000) -> None:
        self._ids: OrderedDict[str, None] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def first_time(self, message_id: str) -> bool:
        with self._lock:
            if message_id in self._ids:
                return False
            self._ids[message_id] = None
            if len(self._ids) > self._max_size:
                self._ids.popitem(last=False)
            return True


def create_app(agent: AgentFn, whatsapp: WhatsAppClient, settings: WhatsAppSettings) -> FastAPI:
    app = FastAPI(title="HogarTec WhatsApp webhook")
    seen = SeenMessages()
    # Un lock por cliente: si escribe dos mensajes seguidos, se procesan en orden y no en paralelo
    # (en paralelo, ambos leerían el mismo estado y uno pisaría al otro).
    customer_locks: dict[str, threading.Lock] = {}
    locks_guard = threading.Lock()

    def lock_for(phone: str) -> threading.Lock:
        with locks_guard:
            return customer_locks.setdefault(phone, threading.Lock())

    def handle(message: IncomingMessage) -> None:
        try:
            whatsapp.mark_as_read(message.message_id)
        except Exception as error:  # que no se marque como leído no debe impedir la respuesta
            print(f"[whatsapp] no se pudo marcar como leído: {error}")

        if message.text is None:
            whatsapp.send_text(message.sender, UNSUPPORTED_MESSAGE)
            return

        customer_phone = settings.demo_customer_phone or message.sender
        with lock_for(customer_phone):
            reply = agent(customer_phone, message.text)
        if reply:  # "" = bot en pausa: un ejecutivo atiende
            whatsapp.send_text(message.sender, reply)

    @app.get("/webhook", response_class=PlainTextResponse)
    def verify(
        mode: str = Query(alias="hub.mode"),
        token: str = Query(alias="hub.verify_token"),
        challenge: str = Query(alias="hub.challenge"),
    ) -> str:
        if mode == "subscribe" and settings.verify_token and hmac.compare_digest(token, settings.verify_token):
            return challenge
        raise HTTPException(status_code=403, detail="verify_token inválido")

    @app.post("/webhook")
    async def receive(request: Request, background: BackgroundTasks) -> dict:
        raw_body = await request.body()  # la firma se calcula sobre los bytes exactos, no sobre el JSON parseado
        if not valid_signature(raw_body, request.headers.get("X-Hub-Signature-256"), settings.app_secret):
            raise HTTPException(status_code=401, detail="Firma inválida")

        for message in parse_messages(await request.json()):
            if seen.first_time(message.message_id):
                background.add_task(handle, message)  # se ejecuta DESPUÉS de responder 200
        return {"status": "received"}

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


def build_production_app() -> FastAPI:
    from agent.graph import build_graph, respond

    graph = build_graph()
    settings = WhatsAppSettings()
    return create_app(agent=lambda phone, text: respond(graph, phone, text), whatsapp=WhatsAppClient(settings), settings=settings)


def __getattr__(name: str):
    # `app` se construye solo cuando uvicorn lo pide: importar este módulo en los tests no levanta el agente.
    if name == "app":
        return build_production_app()
    raise AttributeError(name)
