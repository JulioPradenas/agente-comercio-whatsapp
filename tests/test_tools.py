"""Tests de las tools contra la API en memoria (sin red, sin LLM).

search_products y search_policies no se testean aquí: dependen de Supabase y Gemini.
"""

from datetime import date

import pytest

from agent.commerce_client import CommerceClient
from agent.tools import CommerceTools, delivery_timing, format_clp

OWNER_PHONE = "56989910085"  # dueño del pedido 1011 (entregado hace 8 días)


@pytest.fixture
def tools(client):
    return CommerceTools(customer_phone=OWNER_PHONE, client=CommerceClient(http=client))


def find_sku(client, in_stock: bool) -> str:
    products = client.get("/api/catalog_system/pub/products/search", params={"ft": "refrigerador", "_to": 49}).json()
    return next(
        p["items"][0]["itemId"]
        for p in products
        if (p["items"][0]["sellers"][0]["commertialOffer"]["AvailableQuantity"] > 0) == in_stock
    )


def test_format_clp():
    assert format_clp(479990) == "$479.990"
    assert format_clp(1169990) == "$1.169.990"


def test_add_to_cart_returns_pesos_and_checkout_link(tools, client):
    result = tools.add_to_cart(find_sku(client, in_stock=True))
    assert result["total"].startswith("$")
    assert "00." not in result["total"]  # no quedaron centavos
    assert result["shipping"] == "Gratis"
    assert result["checkout_url"].endswith(tools.cart_id)


def test_cart_is_reused_within_conversation(tools, client):
    tools.add_to_cart(find_sku(client, in_stock=True))
    first_cart = tools.cart_id
    tools.add_to_cart(find_sku(client, in_stock=True))
    assert tools.cart_id == first_cart


def test_add_out_of_stock_returns_warning(tools, client):
    result = tools.add_to_cart(find_sku(client, in_stock=False))
    assert result["warnings"]
    assert result["checkout_url"] is None


def test_get_own_order(tools):
    result = tools.get_order_status("1011")
    assert result["status"] == "Entregado"
    assert result["delivered_at"] is not None


def test_other_customers_order_looks_like_not_found(tools):
    other_customer_order = tools.get_order_status("1006")
    nonexistent_order = tools.get_order_status("99999")
    assert other_customer_order == nonexistent_order
    assert "1006" not in str(other_customer_order)


def test_list_my_orders_returns_latest_five(tools):
    # Este cliente tiene más de 5 pedidos: al agente solo le llegan los 5 más recientes.
    dates = [order["date"] for order in tools.list_my_orders()["orders"]]
    assert len(dates) == 5
    assert dates == sorted(dates, reverse=True)


def test_request_return_success(tools):
    result = tools.request_return("1011", "SKU-100224")
    assert result["return_id"].startswith("RET-")


def test_request_return_error_includes_guidance(tools):
    result = tools.request_return("1011", "SKU-100000")
    assert result["error"] == "SKU_NOT_IN_ORDER"
    assert result["guidance"]


def test_phone_is_not_exposed_to_the_llm(tools):
    # Lo que ve Gemini es la declaración generada desde la firma: no debe existir un parámetro de teléfono.
    for declaration in tools.declarations():
        parameters = (declaration.parameters_json_schema or {}).get("properties", {})
        assert not any("phone" in name for name in parameters), declaration.name


def test_product_type_is_an_enum_for_the_llm(tools):
    search = next(d for d in tools.declarations() if d.name == "search_products")
    product_type = search.parameters_json_schema["properties"]["product_type"]
    assert "Refrigerador" in product_type["anyOf"][0]["enum"]


# --- Atraso calculado en código (caso edge-01 de la evaluación) ---


TODAY = date(2026, 11, 20)  # viernes


def test_order_before_estimate_is_on_time():
    assert delivery_timing("handling", "2026-11-24", TODAY).startswith("dentro del plazo")


def test_order_late_within_margin_does_not_escalate():
    # Estimado el martes 18; hoy viernes 20 -> 2 días hábiles de atraso: aún no se deriva.
    assert "no corresponde derivar" in delivery_timing("invoiced", "2026-11-18", TODAY)


def test_order_late_beyond_margin_escalates():
    # Estimado el viernes 13; hoy viernes 20 -> 5 días hábiles.
    assert "corresponde derivar" in delivery_timing("invoiced", "2026-11-13", TODAY)
    assert "no corresponde" not in delivery_timing("invoiced", "2026-11-13", TODAY)


def test_delivered_orders_have_no_timing():
    assert delivery_timing("delivered", "2026-11-13", TODAY) is None


def test_list_my_orders_includes_products(tools):
    orders = tools.list_my_orders()["orders"]
    assert all(order["products"] for order in orders)
