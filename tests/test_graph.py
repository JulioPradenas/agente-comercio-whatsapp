"""Tests de la estructura del agente que no requieren llamar al LLM."""

from agent.graph import build_graph
from agent.subagents import SUBAGENTS, render_history
from agent.tools import CommerceTools


def test_subagent_tools_exist():
    available = {function.__name__ for function in CommerceTools("56900000000").functions()}
    for intent, (_, tool_names) in SUBAGENTS.items():
        assert set(tool_names) <= available, intent


def test_faq_cannot_sell_or_touch_orders():
    _, faq_tools = SUBAGENTS["faq"]
    assert faq_tools == ["search_policies"]


def test_only_postsale_can_create_returns():
    owners = [intent for intent, (_, tools) in SUBAGENTS.items() if "request_return" in tools]
    assert owners == ["postsale"]


def test_graph_has_expected_routes():
    graph = build_graph().get_graph()
    edges = {(edge.source, edge.target) for edge in graph.edges}
    assert {("router", "sales"), ("router", "postsale"), ("router", "faq")} <= edges


def test_render_history_groups_tool_results_as_context():
    contents = render_history(
        [
            {"role": "user", "text": "busco un refri"},
            {"role": "tool", "name": "search_products", "result": {"products": []}},
            {"role": "assistant", "text": "Tengo estas opciones"},
        ]
    )
    assert [content.role for content in contents] == ["user", "model"]
    assert "Contexto interno" in contents[0].parts[1].text
