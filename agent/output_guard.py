"""Guardrails de salida: revisan la respuesta del LLM ANTES de enviarla al cliente.

1. Precios respaldados: todo monto en pesos de la respuesta debe venir de una herramienta (precio,
   total, despacho, política) o de un mensaje del cliente ("bajo 700 lucas"). Un precio inventado
   es el error más caro en e-commerce: el prompt lo prohíbe, pero el prompt no lo garantiza.
2. Nunca pedir datos de pago: el pago es siempre por link seguro.
"""

import json
import re

from agent.observability import observe
from agent.state import Message

# $479.990 / $ 3.990 / $49990
AMOUNT_PATTERN = re.compile(r"\$\s?(\d{1,3}(?:\.\d{3})+|\d+)")
# Cómo escriben los clientes chilenos un presupuesto: "700 lucas", "700 mil", "700k", "1,5 millones"
BUDGET_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*(lucas|luca|mil|k|millones|millón|millon)\b", re.IGNORECASE)
MULTIPLIERS = {"lucas": 1_000, "luca": 1_000, "mil": 1_000, "k": 1_000, "millones": 1_000_000, "millón": 1_000_000, "millon": 1_000_000}

# Pedir datos de pago. Se ignora si la oración es una advertencia ("nunca te pediremos tu clave").
PAYMENT_DATA_REQUEST = re.compile(
    r"(n[uú]mero|datos|d[ií]gitos) de (tu |la )?tarjeta|\bcvv\b|c[oó]digo de seguridad|\bclave\b|contrase[nñ]a",
    re.IGNORECASE,
)
NEGATION = re.compile(r"\b(nunca|no|jam[aá]s)\b", re.IGNORECASE)

SAFE_FALLBACK = (
    "Disculpa, no pude confirmar ese dato con exactitud. ¿Me dices de nuevo qué producto o pedido te interesa "
    "y lo reviso?"
)


def extract_amounts(text: str) -> set[int]:
    return {int(raw.replace(".", "")) for raw in AMOUNT_PATTERN.findall(text)}


def extract_budgets(text: str) -> set[int]:
    budgets = set()
    for number, unit in BUDGET_PATTERN.findall(text):
        budgets.add(int(float(number.replace(",", ".")) * MULTIPLIERS[unit.lower()]))
    return budgets


def allowed_amounts(messages: list[Message]) -> set[int]:
    """Montos que el agente puede mencionar: los de resultados de herramientas y los que dijo el cliente."""
    allowed: set[int] = set()
    for message in messages:
        if message["role"] == "tool":
            allowed |= extract_amounts(json.dumps(message["result"], ensure_ascii=False))
        elif message["role"] == "user":
            allowed |= extract_amounts(message["text"]) | extract_budgets(message["text"])
    return allowed


def asks_for_payment_data(reply: str) -> bool:
    sentences = re.split(r"(?<=[.!?\n])\s+", reply)
    return any(PAYMENT_DATA_REQUEST.search(sentence) and not NEGATION.search(sentence) for sentence in sentences)


@observe(name="output_guard", as_type="guardrail", capture_input=False)
def check_reply(reply: str, messages: list[Message]) -> list[str]:
    """Devuelve las violaciones encontradas (lista vacía = la respuesta se puede enviar)."""
    violations = []
    unsupported = sorted(extract_amounts(reply) - allowed_amounts(messages))
    if unsupported:
        amounts = ", ".join(f"${amount:,}".replace(",", ".") for amount in unsupported)
        violations.append(f"Montos que no vienen de ninguna herramienta: {amounts}")
    if asks_for_payment_data(reply):
        violations.append("La respuesta pide datos de pago; el pago es solo por link seguro")
    return violations
