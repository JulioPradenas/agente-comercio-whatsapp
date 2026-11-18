"""Creación y cierre de tickets de derivación a un ejecutivo."""

import uuid
from typing import Literal

from psycopg.types.json import Jsonb

from agent.state import Message
from db.connection import get_connection

Trigger = Literal["router_rule", "agent_policy", "system_failure"]
TRANSCRIPT_LIMIT = 20

HANDOFF_MESSAGE = (
    "Te voy a derivar con un ejecutivo de atención al cliente para que lo revise en detalle. "
    "Tu número de caso es *{ticket_id}*. Te escribirá por este mismo chat en horario hábil "
    "(lunes a viernes, 9:00 a 18:00)."
)


def build_summary(messages: list[Message], reason: str) -> str:
    """Resumen determinista (sin LLM): motivo, últimos mensajes del cliente y herramientas usadas."""
    customer_lines = [message["text"] for message in messages if message["role"] == "user"][-3:]
    tools_used = sorted({message["name"] for message in messages if message["role"] == "tool"})
    return (
        f"Motivo: {reason}\n"
        f"Últimos mensajes del cliente: {' | '.join(customer_lines)}\n"
        f"Herramientas consultadas: {', '.join(tools_used) or 'ninguna'}"
    )


def create_ticket(phone: str, trigger: Trigger, reason: str, messages: list[Message]) -> str:
    ticket_id = f"HT-{uuid.uuid4().hex[:6].upper()}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO handoff_tickets (ticket_id, customer_phone, trigger, reason, summary, transcript)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (ticket_id, phone, trigger, reason, build_summary(messages, reason), Jsonb(messages[-TRANSCRIPT_LIMIT:])),
        )
    return ticket_id


def close_ticket(ticket_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE handoff_tickets SET status = 'closed', closed_at = now() WHERE ticket_id = %s", (ticket_id,)
        )
