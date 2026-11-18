"""Subagentes de ventas, postventa y FAQ: mismo loop de function calling, distinto prompt y distintas tools."""

import json

from google.genai import types

from agent.llm import generate
from agent.output_guard import SAFE_FALLBACK, check_reply
from agent.prompts import FAQ_PROMPT, POSTSALE_PROMPT, SALES_PROMPT
from agent.state import ConversationState, Message
from agent.tools import CommerceTools

MAX_TOOL_ROUNDS = 5
HISTORY_LIMIT = 20  # mensajes previos que se envían al modelo: acota tokens (= costo por conversación)

SUBAGENTS = {
    "sales": (SALES_PROMPT, ["search_products", "check_stock", "add_to_cart", "search_policies", "escalate_to_human"]),
    "postsale": (
        POSTSALE_PROMPT,
        ["list_my_orders", "get_order_status", "request_return", "search_policies", "escalate_to_human"],
    ),
    "faq": (FAQ_PROMPT, ["search_policies", "escalate_to_human"]),
}


def render_history(messages: list[Message]) -> list[types.Content]:
    """Convierte el historial neutral a formato Gemini. Los resultados de tools de turnos anteriores
    van como texto de contexto: así cualquier subagente puede leerlos aunque no tenga esa tool."""
    contents: list[types.Content] = []
    for message in messages[-HISTORY_LIMIT:]:
        if message["role"] == "user":
            role, text = "user", message["text"]
        elif message["role"] == "assistant":
            role, text = "model", message["text"]
        else:
            role = "user"
            text = f"[Contexto interno, no visible al cliente] {message['name']} devolvió: {json.dumps(message['result'], ensure_ascii=False)}"
        # Mensajes seguidos del mismo rol se agrupan en un solo turno.
        if contents and contents[-1].role == role:
            contents[-1].parts.append(types.Part.from_text(text=text))
        else:
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
    return contents


def run_subagent(state: ConversationState, intent: str) -> dict:
    system_prompt, allowed_tools = SUBAGENTS[intent]
    tools = CommerceTools(customer_phone=state["customer_phone"])
    tools.cart_id = state.get("cart_id")

    functions = {function.__name__: function for function in tools.functions() if function.__name__ in allowed_tools}
    declarations = [declaration for declaration in tools.declarations() if declaration.name in allowed_tools]
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[types.Tool(function_declarations=declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.2,
    )

    contents = render_history(state["messages"])
    new_messages: list[Message] = []
    guard_retried = False  # el guardrail de salida permite UN reintento corregido
    guard_failed = False

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = generate(contents, config)
        except RuntimeError:
            # Todos los modelos caídos: se deriva en vez de dejar al cliente sin respuesta.
            escalation = {"trigger": "system_failure", "reason": "Asistente no disponible (proveedor LLM)"}
            return {"messages": new_messages, "escalation": escalation}
        contents.append(response.candidates[0].content)

        if not response.function_calls:
            answer = response.text or ""
            # Guardrail de salida: la respuesta se revisa antes de enviarla al cliente.
            violations = check_reply(answer, state["messages"] + new_messages)
            if not violations:
                break
            print(f"   [output_guard] {'; '.join(violations)}")
            if guard_retried:
                # Segundo intento también falló: se envía una respuesta segura sin montos.
                answer, guard_failed = SAFE_FALLBACK, True
                break
            guard_retried = True
            correction = (
                f"[Revisión automática, no visible al cliente] Tu respuesta NO se envió: {'; '.join(violations)}. "
                "Corrígela: menciona solo montos que aparezcan en resultados de herramientas (o vuelve a consultarlas) "
                "y nunca pidas datos de pago."
            )
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=correction)]))
            continue

        result_parts = []
        for call in response.function_calls:
            arguments = dict(call.args or {})
            # Defensa extra: si el modelo pide una tool que este subagente no tiene, no se ejecuta.
            if call.name not in functions:
                result = {"error": "TOOL_NOT_ALLOWED", "guidance": "Esa acción no está disponible en esta área."}
            else:
                result = functions[call.name](**arguments)
            print(f"   [{intent}] {call.name}({json.dumps(arguments, ensure_ascii=False)})")
            result_parts.append(types.Part.from_function_response(name=call.name, response=result))
            new_messages.append({"role": "tool", "name": call.name, "result": result})
        contents.append(types.Content(role="user", parts=result_parts))

        # El subagente pidió derivar: se corta aquí y el nodo de derivación da la respuesta.
        if tools.escalation_reason:
            escalation = {"trigger": "agent_policy", "reason": tools.escalation_reason}
            return {"messages": new_messages, "cart_id": tools.cart_id, "escalation": escalation}
    else:
        # Agotó las rondas sin responder: cuenta como fallo (2 seguidos -> derivación por regla del router).
        answer = "Disculpa, no pude resolver tu consulta. ¿Me la puedes explicar de otra forma?"
        new_messages.append({"role": "assistant", "text": answer})
        return {
            "messages": new_messages,
            "cart_id": tools.cart_id,
            "last_reply": answer,
            "consecutive_failures": state.get("consecutive_failures", 0) + 1,
        }

    new_messages.append({"role": "assistant", "text": answer})
    # Si el guardrail tuvo que reemplazar la respuesta, cuenta como fallo (2 seguidos -> derivación).
    failures = state.get("consecutive_failures", 0) + 1 if guard_failed else 0
    return {"messages": new_messages, "cart_id": tools.cart_id, "last_reply": answer, "consecutive_failures": failures}


def sales_node(state: ConversationState) -> dict:
    return run_subagent(state, "sales")


def postsale_node(state: ConversationState) -> dict:
    return run_subagent(state, "postsale")


def faq_node(state: ConversationState) -> dict:
    return run_subagent(state, "faq")
