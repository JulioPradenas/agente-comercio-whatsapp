"""Observabilidad con Langfuse: una traza por mensaje de WhatsApp, con tiempos, tokens y costo por paso.

Sin LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY el SDK queda inactivo: el agente funciona igual.
"""

import hashlib

from dotenv import load_dotenv

# El SDK de Langfuse lee sus claves de las variables de entorno del proceso, no del archivo .env
# (pydantic-settings lee el .env pero no lo copia al entorno). En Render no hay .env: no-op.
load_dotenv()

from langfuse import get_client, observe, propagate_attributes  # noqa: E402

# USD por millón de tokens, tier pagado (precio de lista). Fuente: https://aistudio.google.com/docs/pricing
# (consultado el 18-nov-2026). En el tier gratuito el costo real es 0: el KPI se calcula a precio de lista
# porque es lo que costaría la operación en producción.
PRICES_PER_MILLION = {
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
    "gemini-embedding-001": {"input": 0.15, "output": 0.0},
}


def cost_details(model: str, input_tokens: int, output_tokens: int) -> dict[str, float]:
    prices = PRICES_PER_MILLION.get(model, {"input": 0.0, "output": 0.0})
    input_cost = input_tokens * prices["input"] / 1_000_000
    output_cost = output_tokens * prices["output"] / 1_000_000
    return {"input": input_cost, "output": output_cost, "total": input_cost + output_cost}


def anonymize(phone: str) -> str:
    """Langfuse es un servicio externo: se envía un hash del teléfono, nunca el número.
    Sigue sirviendo para agrupar las conversaciones de un mismo cliente."""
    return "cliente-" + hashlib.sha256(phone.encode()).hexdigest()[:12]


__all__ = ["anonymize", "cost_details", "get_client", "observe", "propagate_attributes"]
