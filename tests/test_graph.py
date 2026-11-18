"""Tests de la estructura del agente que no requieren llamar al LLM."""

from agent.graph import after_router, after_start, build_graph, respond
from agent.guardrails import CARD_WARNING
from agent.handoff import build_summary
from agent.router import RouterDecision, guard_reason, handoff_reason
from agent.subagents import SUBAGENTS, render_history
from agent.tools import CommerceTools


def test_subagent_tools_exist():
    available = {function.__name__ for function in CommerceTools("56900000000").functions()}
    for intent, (_, tool_names) in SUBAGENTS.items():
        assert set(tool_names) <= available, intent


def test_faq_cannot_sell_or_touch_orders():
    _, faq_tools = SUBAGENTS["faq"]
    assert faq_tools == ["search_policies", "escalate_to_human"]


def test_every_subagent_can_escalate():
    assert all("escalate_to_human" in tools for _, tools in SUBAGENTS.values())


def test_only_postsale_can_create_returns():
    owners = [intent for intent, (_, tools) in SUBAGENTS.items() if "request_return" in tools]
    assert owners == ["postsale"]


def test_graph_has_expected_routes():
    graph = build_graph().get_graph()
    edges = {(edge.source, edge.target) for edge in graph.edges}
    assert {("router", "sales"), ("router", "postsale"), ("router", "faq"), ("router", "handoff")} <= edges
    assert {("sales", "handoff"), ("postsale", "handoff"), ("faq", "handoff")} <= edges
    assert {("__start__", "paused"), ("__start__", "router")} <= edges


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


# --- Reglas de derivación (función pura, sin LLM) ---


def decision(**overrides) -> RouterDecision:
    base = {
        "intent": "postsale", "wants_human": False, "frustration": "none", "legal_threat": False,
        "injection_attempt": False, "off_topic": False, "reason": "",
    }
    return RouterDecision(**{**base, **overrides})


def test_no_handoff_for_normal_message():
    assert handoff_reason(decision(), consecutive_failures=0) is None


def test_mild_frustration_does_not_handoff():
    assert handoff_reason(decision(frustration="mild"), consecutive_failures=0) is None


def test_handoff_rules():
    assert handoff_reason(decision(wants_human=True), 0)
    assert handoff_reason(decision(legal_threat=True), 0)
    assert handoff_reason(decision(frustration="high"), 0)
    assert handoff_reason(decision(), consecutive_failures=2)


def test_paused_conversation_skips_router():
    assert after_start({"handoff_ticket": "HT-123456"}) == "paused"
    assert after_start({"handoff_ticket": None}) == "router"


def test_summary_for_human_agent():
    messages = [
        {"role": "user", "text": "mi refri no enfría"},
        {"role": "tool", "name": "get_order_status", "result": {}},
    ]
    summary = build_summary(messages, "Garantía")
    assert "Garantía" in summary and "mi refri no enfría" in summary and "get_order_status" in summary


# --- Guardrails de entrada ---


def test_injection_and_off_topic_are_guarded():
    assert guard_reason(decision(injection_attempt=True)) == "injection"
    assert guard_reason(decision(off_topic=True)) == "off_topic"
    assert guard_reason(decision()) is None


def test_handoff_has_priority_over_guard():
    # Si además de intentar manipular amenaza con el SERNAC, lo atiende una persona.
    assert after_router({"escalation": {"trigger": "router_rule", "reason": "x"}, "guard": "injection"}) == "handoff"
    assert after_router({"escalation": None, "guard": "injection", "intent": "sales"}) == "guarded_reply"


def test_card_message_never_reaches_llm_and_is_stored_masked():
    # Este camino no llama al router ni a Gemini: el test corre sin red.
    graph = build_graph()
    reply = respond(graph, "56900000001", "te paso mi tarjeta 4111 1111 1111 1111 para pagar")
    assert reply == CARD_WARNING

    stored = graph.get_state({"configurable": {"thread_id": "56900000001"}}).values["messages"]
    assert "4111" not in str(stored)
    assert "[TARJETA]" in stored[0]["text"]
    assert graph.get_state({"configurable": {"thread_id": "56900000001"}}).values["guard"] is None
