"""Grafo del agente.

START -> (¿ticket abierto?) -> paused
      -> (¿envió una tarjeta?) -> guarded_reply
      -> router -> (¿derivar?) -> handoff
                -> (¿injection o fuera de tema?) -> guarded_reply
                -> sales | postsale | faq -> (¿el subagente pidió derivar?) -> handoff | END
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agent.guardrails import CARD_WARNING, INJECTION_REPLY, OFF_TOPIC_REPLY, mask_pii
from agent.handoff import HANDOFF_MESSAGE, create_ticket
from agent.router import route
from agent.state import ConversationState
from agent.subagents import faq_node, postsale_node, sales_node

SUBAGENT_NODES = ["sales", "postsale", "faq"]


def handoff_node(state: ConversationState) -> dict:
    """Único punto donde se crean tickets, venga la derivación de una regla, del subagente o de una falla."""
    escalation = state["escalation"]
    ticket_id = create_ticket(state["customer_phone"], escalation["trigger"], escalation["reason"], state["messages"])
    print(f"   [handoff] ticket {ticket_id} ({escalation['trigger']}): {escalation['reason']}")
    reply = HANDOFF_MESSAGE.format(ticket_id=ticket_id)
    return {
        "messages": [{"role": "assistant", "text": reply}],
        "last_reply": reply,
        "handoff_ticket": ticket_id,
        "escalation": None,
        "consecutive_failures": 0,
    }


GUARDED_REPLIES = {"card": CARD_WARNING, "injection": INJECTION_REPLY, "off_topic": OFF_TOPIC_REPLY}


def guarded_reply_node(state: ConversationState) -> dict:
    """Respuesta fija, sin LLM: no hay nada que conversar y una respuesta fija no se puede manipular."""
    reply = GUARDED_REPLIES[state["guard"]]
    print(f"   [guardrail] {state['guard']}")
    return {"messages": [{"role": "assistant", "text": reply}], "last_reply": reply, "guard": None}


def paused_node(state: ConversationState) -> dict:
    """Con un ejecutivo a cargo, el bot no responde: el mensaje queda en el historial para el humano."""
    return {"last_reply": ""}


def after_start(state: ConversationState) -> str:
    if state.get("handoff_ticket"):
        return "paused"
    if state.get("guard") == "card":
        return "guarded_reply"
    return "router"


def after_router(state: ConversationState) -> str:
    if state.get("escalation"):
        return "handoff"
    if state.get("guard"):
        return "guarded_reply"
    return state["intent"]


def after_subagent(state: ConversationState) -> str:
    return "handoff" if state.get("escalation") else END


def build_graph(checkpointer=None):
    graph = StateGraph(ConversationState)

    graph.add_node("router", route)
    graph.add_node("sales", sales_node)
    graph.add_node("postsale", postsale_node)
    graph.add_node("faq", faq_node)
    graph.add_node("handoff", handoff_node)
    graph.add_node("paused", paused_node)
    graph.add_node("guarded_reply", guarded_reply_node)

    graph.add_conditional_edges(START, after_start, ["paused", "guarded_reply", "router"])
    graph.add_conditional_edges("router", after_router, [*SUBAGENT_NODES, "handoff", "guarded_reply"])
    for node in SUBAGENT_NODES:
        graph.add_conditional_edges(node, after_subagent, ["handoff", END])
    graph.add_edge("handoff", END)
    graph.add_edge("paused", END)
    graph.add_edge("guarded_reply", END)

    # El checkpointer guarda el estado después de cada turno, por thread_id.
    # InMemorySaver (por defecto) sirve para la CLI y los tests; en producción se pasa PostgresSaver.
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def respond(graph, phone: str, text: str) -> str:
    """Procesa un mensaje del cliente y devuelve la respuesta. "" = bot en pausa (atiende un ejecutivo)."""
    # thread_id = teléfono: cada cliente tiene su propia memoria de conversación.
    config = {"configurable": {"thread_id": phone}}
    # Guardrail de entrada: el texto se enmascara ANTES de entrar al estado,
    # así el dato real no llega al LLM, a Postgres (checkpoints) ni a los tickets.
    masked = mask_pii(text)
    guard = "card" if "TARJETA" in masked.found else None
    message = {"role": "user", "text": masked.text}
    result = graph.invoke({"customer_phone": phone, "messages": [message], "guard": guard}, config)
    return result["last_reply"]


def resume_bot(graph, phone: str) -> None:
    """Lo llama el ejecutivo al cerrar el caso: el bot vuelve a atender a ese cliente."""
    graph.update_state({"configurable": {"thread_id": phone}}, {"handoff_ticket": None})
