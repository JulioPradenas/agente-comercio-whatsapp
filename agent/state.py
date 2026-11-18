"""Estado de la conversación que LangGraph guarda entre turnos (por thread_id = teléfono)."""

import operator
from typing import Annotated, Literal, TypedDict

Intent = Literal["sales", "postsale", "faq"]


class Message(TypedDict, total=False):
    """Mensaje independiente del proveedor de LLM: se puede guardar en Postgres o cambiar de modelo."""

    role: Literal["user", "assistant", "tool"]
    text: str  # user / assistant
    name: str  # tool: nombre de la herramienta
    result: dict  # tool: lo que devolvió


class Escalation(TypedDict):
    trigger: Literal["router_rule", "agent_policy", "system_failure"]
    reason: str


class ConversationState(TypedDict, total=False):
    customer_phone: str
    # operator.add = "reducer": cada nodo devuelve solo los mensajes NUEVOS y LangGraph los concatena.
    messages: Annotated[list[Message], operator.add]
    intent: Intent
    cart_id: str | None  # el carrito sobrevive entre turnos
    last_reply: str
    # Derivación a humano
    escalation: Escalation | None  # pedida en este turno por una regla o por el subagente
    handoff_ticket: str | None  # si hay ticket abierto, el bot está en pausa
    consecutive_failures: int  # turnos seguidos en que el agente no pudo resolver
    # Guardrails de entrada: "card" (envió datos de tarjeta), "injection" u "off_topic"
    guard: Literal["card", "injection", "off_topic"] | None

