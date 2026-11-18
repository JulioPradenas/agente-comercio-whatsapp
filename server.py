"""Punto de entrada para Hugging Face Spaces: un solo puerto con los dos servicios.

    /webhook, /health   -> webhook de WhatsApp + agente
    /commerce/api/...   -> API de comercio VTEX-like (simula el sistema externo)

El agente sigue llamando a la API de comercio por HTTP (COMMERCE_API_URL=http://127.0.0.1:8080/commerce):
si mañana se conecta a VTEX real, solo cambia esa URL. Uso: APP_MODULE=server:app
"""

from channels.whatsapp_webhook import build_production_app
from commerce_api.main import app as commerce_app

app = build_production_app()
app.mount("/commerce", commerce_app)
