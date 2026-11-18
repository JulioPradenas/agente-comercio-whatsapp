"""Guardrails de entrada: enmascarar datos personales antes de que lleguen al LLM, a Postgres o a los logs.

Se usan expresiones regulares y no un modelo (ej. Presidio + spaCy) porque los datos sensibles de este
caso tienen formato fijo (RUT, tarjeta, email, celular) y el contenedor corre con 512 MB de RAM.
Criterio: preferimos enmascarar de más (un número que no era un RUT) que filtrar un dato real.
"""

import re
from dataclasses import dataclass, field

PII_PATTERNS: dict[str, re.Pattern] = {
    # 13 a 19 dígitos, con o sin espacios o guiones: tarjetas de crédito y débito.
    "TARJETA": re.compile(r"\b\d(?:[ -]?\d){12,18}\b"),
    # RUT chileno con puntos o sin ellos, siempre con guion y dígito verificador: 12.345.678-5 / 12345678-K
    "RUT": re.compile(r"\b\d{1,2}(?:\.\d{3}){2}-[\dkK]\b|\b\d{7,8}-[\dkK]\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    # Celular chileno: +56 9 1234 5678 / 56912345678 / 9 1234 5678.
    # (?<!\d) y (?!\d) = "sin otro dígito al lado"; \b no sirve aquí porque entre "56" y "9" no hay límite de palabra.
    "TELEFONO": re.compile(r"(?<!\d)(?:\+?56\s?)?9\s?\d{4}\s?\d{4}(?!\d)"),
}


@dataclass
class MaskResult:
    text: str
    found: list[str] = field(default_factory=list)  # tipos detectados, sin los valores


def mask_pii(text: str) -> MaskResult:
    """Reemplaza cada dato sensible por su tipo entre corchetes. El orden importa: TARJETA va primero
    para que sus dígitos no se interpreten como teléfono."""
    found = []
    for label, pattern in PII_PATTERNS.items():
        text, count = pattern.subn(f"[{label}]", text)
        if count:
            found.append(label)
    return MaskResult(text=text, found=found)


CARD_WARNING = (
    "Por tu seguridad, no compartas datos de tarjetas por chat: no los guardamos y nunca te los "
    "pediremos por WhatsApp. Para pagar te enviamos un *link de pago seguro*. ¿Te ayudo con tu compra?"
)
INJECTION_REPLY = (
    "Solo puedo ayudarte con productos, pedidos y políticas de HogarTec, siguiendo las condiciones "
    "vigentes de la tienda. ¿En qué te puedo ayudar?"
)
OFF_TOPIC_REPLY = (
    "Eso está fuera de lo que puedo hacer: soy el asistente de compras de HogarTec. "
    "Puedo ayudarte a buscar productos, revisar tus pedidos o resolver dudas de despacho, devoluciones y pagos."
)
