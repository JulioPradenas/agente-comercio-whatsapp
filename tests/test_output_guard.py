"""Guardrails de salida (sin LLM): precios respaldados y nunca pedir datos de pago."""

from agent.output_guard import asks_for_payment_data, check_reply, extract_budgets

SEARCH_RESULT = {
    "role": "tool",
    "name": "search_products",
    "result": {"products": [{"name": "Refrigerador Mabe No Frost 500 L", "price": "$269.990", "normal_price": None}]},
}
POLICY_RESULT = {
    "role": "tool",
    "name": "search_policies",
    "result": {"fragments": [{"text": "El despacho cuesta $3.990 y es gratis desde $49.990."}]},
}


# --- Precios ---


def test_price_from_tool_is_allowed():
    history = [{"role": "user", "text": "busco un refri"}, SEARCH_RESULT]
    assert check_reply("Tengo el Refrigerador Mabe 500 L a *$269.990*.", history) == []


def test_invented_price_is_blocked():
    history = [{"role": "user", "text": "busco un refri"}, SEARCH_RESULT]
    violations = check_reply("Lo tengo en oferta a $199.990.", history)
    assert violations and "$199.990" in violations[0]


def test_policy_amounts_are_allowed():
    history = [{"role": "user", "text": "cuánto cuesta el despacho?"}, POLICY_RESULT]
    assert check_reply("Cuesta $3.990 y es gratis desde $49.990.", history) == []


def test_customer_budget_can_be_repeated():
    history = [{"role": "user", "text": "un refri que no pase de 700 lucas"}, SEARCH_RESULT]
    assert check_reply("Bajo $700.000 tengo el Mabe 500 L a $269.990.", history) == []


def test_amounts_from_earlier_turns_are_allowed():
    history = [{"role": "user", "text": "busco un refri"}, SEARCH_RESULT, {"role": "user", "text": "cuánto era?"}]
    assert check_reply("Era $269.990.", history) == []


def test_reply_without_amounts_passes():
    assert check_reply("¿Qué capacidad necesitas?", []) == []


def test_budget_formats():
    assert extract_budgets("700 lucas") == {700_000}
    assert extract_budgets("hasta 500 mil") == {500_000}
    assert extract_budgets("1,5 millones") == {1_500_000}


# --- Datos de pago ---


def test_asking_for_card_is_blocked():
    assert asks_for_payment_data("Para terminar, envíame el número de tu tarjeta y el CVV.")


def test_security_warning_is_allowed():
    assert not asks_for_payment_data("Nunca te pediremos la clave ni los datos de tu tarjeta por chat.")
    assert not asks_for_payment_data("Paga con este link seguro: https://hogartec.example/checkout")
