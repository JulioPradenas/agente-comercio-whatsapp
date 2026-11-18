"""Grafo del agente: router -> subagente (ventas / postventa / faq)."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agent.router import route
from agent.state import ConversationState
from agent.subagents import faq_node, postsale_node, sales_node


def build_graph(checkpointer=None):
    graph = StateGraph(ConversationState)

    graph.add_node("router", route)
    graph.add_node("sales", sales_node)
    graph.add_node("postsale", postsale_node)
    graph.add_node("faq", faq_node)

    graph.add_edge(START, "router")
    # La función recibe el estado y devuelve el nombre del siguiente nodo.
    graph.add_conditional_edges("router", lambda state: state["intent"], ["sales", "postsale", "faq"])
    for node in ["sales", "postsale", "faq"]:
        graph.add_edge(node, END)

    # El checkpointer guarda el estado después de cada turno, por thread_id.
    # InMemorySaver se pierde al reiniciar; al desplegar se cambia por PostgresSaver (Supabase).
    return graph.compile(checkpointer=checkpointer or InMemorySaver())
