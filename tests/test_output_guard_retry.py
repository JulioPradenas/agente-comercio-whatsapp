"""Reintento del guardrail de salida dentro del subagente, con un LLM simulado (sin red).

No se puede pedir a Gemini que invente un precio a voluntad: se reemplaza `generate`
por respuestas programadas para probar la lógica de forma determinista.
"""

from types import SimpleNamespace

import pytest
from google.genai import types

from agent import subagents
from agent.output_guard import SAFE_FALLBACK

HISTORY = [
    {"role": "user", "text": "busco un refri no frost grande"},
    {"role": "tool", "name": "search_products", "result": {"products": [{"name": "Refrigerador Mabe 500 L", "price": "$269.990"}]}},
    {"role": "assistant", "text": "Tengo el Refrigerador Mabe 500 L a $269.990."},
    {"role": "user", "text": "y cuánto cuesta?"},
]


def text_response(text: str):
    content = types.Content(role="model", parts=[types.Part.from_text(text=text)])
    return SimpleNamespace(text=text, function_calls=None, candidates=[SimpleNamespace(content=content)])


@pytest.fixture
def scripted_llm(monkeypatch):
    """Devuelve las respuestas en orden y registra lo que recibió el modelo en cada llamada."""
    calls: list[list[types.Content]] = []

    def install(*replies: str):
        queue = list(replies)

        def fake_generate(contents, config):
            calls.append(list(contents))
            return text_response(queue.pop(0))

        monkeypatch.setattr(subagents, "generate", fake_generate)
        return calls

    return install


def run(state_messages):
    return subagents.run_subagent({"customer_phone": "56900000002", "messages": state_messages}, "faq")


def test_valid_reply_is_sent_on_first_try(scripted_llm):
    calls = scripted_llm("Cuesta $269.990.")
    result = run(HISTORY)
    assert result["last_reply"] == "Cuesta $269.990."
    assert len(calls) == 1


def test_invented_price_is_corrected_on_retry(scripted_llm):
    calls = scripted_llm("Hoy está a $199.990.", "Cuesta $269.990.")
    result = run(HISTORY)
    assert result["last_reply"] == "Cuesta $269.990."
    assert result["consecutive_failures"] == 0
    # En el reintento, el modelo recibió la corrección con el monto rechazado.
    correction = calls[1][-1].parts[0].text
    assert "NO se envió" in correction and "$199.990" in correction


def test_two_invented_prices_send_safe_fallback(scripted_llm):
    scripted_llm("Hoy está a $199.990.", "Te lo dejo en $150.000.")
    result = run(HISTORY)
    assert result["last_reply"] == SAFE_FALLBACK
    assert "$" not in result["last_reply"]
    assert result["consecutive_failures"] == 1  # cuenta como fallo: 2 seguidos derivan a un humano


def test_rejected_draft_is_not_stored(scripted_llm):
    scripted_llm("Hoy está a $199.990.", "Cuesta $269.990.")
    result = run(HISTORY)
    stored = [message["text"] for message in result["messages"] if message["role"] == "assistant"]
    assert stored == ["Cuesta $269.990."]  # el borrador con el precio inventado no queda en la memoria


def test_usage_meter_counts_only_inside_its_block():
    from agent.metering import UsageMeter, record_usage

    record_usage(100, 10, 0.5)  # sin medidor activo: se ignora
    with UsageMeter() as meter:
        record_usage(1_000, 50, 0.001)
        record_usage(2_000, 70, 0.002)
    record_usage(100, 10, 0.5)  # después del bloque: se ignora
    assert (meter.calls, meter.input_tokens, meter.output_tokens) == (2, 3_000, 120)
    assert round(meter.cost_usd, 6) == 0.003


def test_nested_meters_with_equal_counts():
    # Regresión: con igualdad por valor, salir del medidor interno sacaba al externo de la lista.
    from agent.metering import UsageMeter, record_usage

    with UsageMeter() as conversation:
        with UsageMeter() as turn:
            record_usage(10, 1, 0.1)
        record_usage(10, 1, 0.1)
    assert turn.calls == 1 and conversation.calls == 2
