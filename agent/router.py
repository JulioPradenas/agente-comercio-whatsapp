"""Nodo router: clasifica la intención del último mensaje con salida estructurada."""

from google.genai import types
from pydantic import BaseModel, Field

from agent.llm import generate
from agent.prompts import ROUTER_PROMPT
from agent.state import ConversationState, Intent

CONTEXT_MESSAGES = 6  # el router solo necesita el contexto reciente, no toda la conversación


class RouterDecision(BaseModel):
    intent: Intent
    reason: str = Field(description="Justificación breve, para auditar la decisión")


def render_recent_context(state: ConversationState) -> str:
    lines = []
    for message in state["messages"][-CONTEXT_MESSAGES:]:
        if message["role"] == "user":
            lines.append(f"Cliente: {message['text']}")
        elif message["role"] == "assistant":
            lines.append(f"Asistente: {message['text']}")
    return "\n".join(lines)


def route(state: ConversationState) -> dict:
    response = generate(
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=render_recent_context(state))])],
        config=types.GenerateContentConfig(
            system_instruction=ROUTER_PROMPT,
            response_mime_type="application/json",
            response_schema=RouterDecision,  # Gemini devuelve JSON que cumple este esquema
            temperature=0,  # clasificar: queremos la misma respuesta ante el mismo input
        ),
    )
    decision: RouterDecision = response.parsed
    print(f"   [router] {decision.intent}: {decision.reason}")
    return {"intent": decision.intent}
