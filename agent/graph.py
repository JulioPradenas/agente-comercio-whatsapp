"""Grafo del agente.

START -> (¿ticket abierto?) -> paused
      -> router -> (¿derivar?) -> handoff
                -> sales | postsale | faq -> (¿el subagente pidió derivar?) -> handoff | END
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

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


def paused_node(state: ConversationState) -> dict:
    """Con un ejecutivo a cargo, el bot no responde: el mensaje queda en el historial para el humano."""
    return {"last_reply": ""}


def after_start(state: ConversationState) -> str:
    return "paused" if state.get("handoff_ticket") else "router"


def after_router(state: ConversationState) -> str:
    return "handoff" if state.get("escalation") else state["intent"]


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

    graph.add_conditional_edges(START, after_start, ["paused", "router"])
    graph.add_conditional_edges("router", after_router, [*SUBAGENT_NODES, "handoff"])
    for node in SUBAGENT_NODES:
        graph.add_conditional_edges(node, after_subagent, ["handoff", END])
    graph.add_edge("handoff", END)
    graph.add_edge("paused", END)

    # El checkpointer guarda el estado después de cada turno, por thread_id.
    # InMemorySaver se pierde al reiniciar; al desplegar se cambia por PostgresSaver (Supabase).
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def resume_bot(graph, phone: str) -> None:
    """Lo llama el ejecutivo al cerrar el caso: el bot vuelve a atender a ese cliente."""
    graph.update_state({"configurable": {"thread_id": phone}}, {"handoff_ticket": None})
