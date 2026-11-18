"""Guardrails de entrada: enmascaramiento de datos personales (sin LLM)."""

import pytest

from agent.guardrails import mask_pii


@pytest.mark.parametrize(
    ("text", "expected_type"),
    [
        ("mi rut es 12.345.678-5", "RUT"),
        ("rut 12345678-K para la factura", "RUT"),
        ("mi tarjeta es 4111 1111 1111 1111", "TARJETA"),
        ("4111-1111-1111-1111 vence 12/28", "TARJETA"),
        ("escríbeme a juan.perez+compras@gmail.com", "EMAIL"),
        ("llámame al +56 9 8765 4321", "TELEFONO"),
        ("mi número es 56987654321", "TELEFONO"),
    ],
)
def test_sensitive_data_is_masked(text, expected_type):
    result = mask_pii(text)
    assert expected_type in result.found
    assert f"[{expected_type}]" in result.text


@pytest.mark.parametrize(
    "text",
    [
        "en qué va mi pedido 1045?",  # número de pedido
        "busco un refri que no pase de 700000",  # presupuesto
        "un tv de 55 pulgadas por $479.990",  # precio con puntos
        "quiero 2 unidades del SKU-100272",  # código de producto
    ],
)
def test_business_numbers_are_not_masked(text):
    result = mask_pii(text)
    assert result.found == []
    assert result.text == text


def test_card_is_not_read_as_phone():
    result = mask_pii("4111 1111 1111 1111")
    assert result.found == ["TARJETA"]


def test_values_are_never_returned():
    result = mask_pii("rut 12.345.678-5, tarjeta 4111111111111111")
    assert "12.345.678" not in result.text and "4111" not in result.text
