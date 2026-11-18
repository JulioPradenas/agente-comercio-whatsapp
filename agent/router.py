"""Nodo router: clasifica la intención y detecta señales de derivación con salida estructurada.

El LLM EXTRAE señales (¿pide una persona? ¿está muy molesto?); la DECISIÓN de derivar la toma
handoff_reason(), código determinista que se puede auditar, testear y ajustar con el negocio.
"""

from typing import Literal

from google.genai import types
from pydantic import BaseModel, Field

from agent.llm import generate
from agent.prompts import ROUTER_PROMPT
from agent.state import ConversationState, Escalation, Intent

CONTEXT_MESSAGES = 6  # el router solo necesita el contexto reciente, no toda la conversación
MAX_CONSECUTIVE_FAILURES = 2


class RouterDecision(BaseModel):
    intent: Intent
    wants_human: bool = Field(description="El cliente pide explícitamente hablar con una persona o ejecutivo")
    frustration: Literal["none", "mild", "high"] = Field(
        description="high = enojo fuerte, insultos o mensajes en mayúsculas; mild = molestia normal"
    )
    legal_threat: bool = Field(description="Menciona SERNAC, abogados, demandas o reclamo formal")
    reason: str = Field(description="Justificación breve, para auditar la decisión")


def handoff_reason(decision: RouterDecision, consecutive_failures: int) -> str | None:
    """Reglas de derivación acordadas con Atención a Clientes. None = el bot sigue atendiendo."""
    if decision.wants_human:
        return "El cliente pidió hablar con una persona"
    if decision.legal_threat:
        return "Mención de reclamo formal o acciones legales"
    if decision.frustration == "high":
        return "Cliente muy molesto"
    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        return f"El asistente no pudo resolver {consecutive_failures} veces seguidas"
    return None


def render_recent_context(state: ConversationState) -> str:
    lines = []
    for message in state["messages"][-CONTEXT_MESSAGES:]:
        if message["role"] == "user":
            lines.append(f"Cliente: {message['text']}")
        elif message["role"] == "assistant":
            lines.append(f"Asistente: {message['text']}")
    return "\n".join(lines)


def classify(state: ConversationState) -> RouterDecision:
    response = generate(
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=render_recent_context(state))])],
        config=types.GenerateContentConfig(
            system_instruction=ROUTER_PROMPT,
            response_mime_type="application/json",
            response_schema=RouterDecision,  # Gemini devuelve JSON que cumple este esquema
            temperature=0,  # clasificar: queremos la misma respuesta ante el mismo input
        ),
    )
    return response.parsed


def route(state: ConversationState) -> dict:
    try:
        decision = classify(state)
    except RuntimeError:
        # Todos los modelos caídos: el cliente no puede quedar sin respuesta.
        escalation: Escalation = {"trigger": "system_failure", "reason": "Asistente no disponible (proveedor LLM)"}
        return {"escalation": escalation}

    reason = handoff_reason(decision, state.get("consecutive_failures", 0))
    print(f"   [router] {decision.intent} | humano={decision.wants_human} frustración={decision.frustration} "
          f"legal={decision.legal_threat} -> {'DERIVAR: ' + reason if reason else 'bot'}")
    escalation = {"trigger": "router_rule", "reason": reason} if reason else None
    # escalation se devuelve siempre (también None) para limpiar la de un turno anterior.
    return {"intent": decision.intent, "escalation": escalation}
