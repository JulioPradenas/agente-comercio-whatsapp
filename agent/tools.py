"""Herramientas (function calling) que el LLM puede invocar.

Principios:
- El docstring de cada método es la descripción que lee el LLM: dice QUÉ hace y CUÁNDO usarla.
- Las respuestas se aplanan y se formatean en código (pesos, fechas): el LLM no hace aritmética.
- El teléfono del cliente viene de la sesión de WhatsApp y NO es un parámetro de las tools:
  así el modelo no puede ser manipulado para consultar pedidos de otra persona.
"""

from collections.abc import Callable
from datetime import date
from typing import Literal

import numpy as np
from google.genai import types

from agent.commerce_client import CommerceClient, CommerceError
from rag.retriever import search_policies as rag_search_policies
from rag.retriever import search_products_semantic

ProductType = Literal[
    "Refrigerador", "Lavadora", "Smart TV", "Notebook", "Smartphone", "Audífonos", "Microondas", "Aspiradora"
]

# Qué debe hacer el agente ante cada error de negocio de la API.
ERROR_GUIDANCE = {
    "ORDER_NOT_FOUND": "No existe un pedido con ese número asociado a este teléfono. Pide que revise el número.",
    "ORDER_NOT_OWNED": "No existe un pedido con ese número asociado a este teléfono. Pide que revise el número.",
    "SKU_NOT_IN_ORDER": "Ese producto no está en el pedido. Pregunta cuál producto quiere devolver.",
    "ORDER_NOT_DELIVERED": (
        "El pedido aún no se entrega: no aplica devolución. Si todavía no fue despachado, se puede cancelar sin costo: "
        "explícaselo y, si el cliente confirma, usa escalate_to_human para que un ejecutivo procese la cancelación."
    ),
    "RETURN_WINDOW_EXPIRED": "Pasó el plazo de retracto de 10 días. Si el producto tiene falla, aplica la garantía legal.",
    "HYGIENE_PRODUCT": "Los audífonos in-ear abiertos no aplican para retracto. Si tienen falla, aplica la garantía.",
    "RETURN_ALREADY_REQUESTED": "Ya existe una solicitud de devolución para ese producto.",
}


def format_clp(pesos: int) -> str:
    return f"${pesos:,}".replace(",", ".")


def cents_to_pesos(cents: int) -> int:
    return cents // 100


def delivery_timing(status: str, estimated_delivery: str, today: date) -> str | None:
    """Dice en palabras si un pedido en curso está dentro del plazo o atrasado (en días hábiles).
    La política deriva a un ejecutivo solo si el atraso supera 2 días hábiles."""
    if status in {"delivered", "canceled"}:
        return None
    estimated = date.fromisoformat(estimated_delivery)
    if today <= estimated:
        return f"dentro del plazo: llega a más tardar el {estimated.isoformat()}"
    late_days = int(np.busday_count(estimated, today))
    if late_days > 2:
        return f"atrasado {late_days} días hábiles: supera el margen de 2 días hábiles, corresponde derivar"
    return f"atrasado {late_days} días hábiles: aún dentro del margen de 2 días hábiles, no corresponde derivar"


class CommerceTools:
    def __init__(self, customer_phone: str, client: CommerceClient | None = None) -> None:
        self.customer_phone = customer_phone
        self.client = client or CommerceClient()
        self.cart_id: str | None = None  # el carrito vive mientras dure la conversación
        self.escalation_reason: str | None = None  # lo marca escalate_to_human; lo lee el subagente

    def functions(self) -> list[Callable]:
        return [
            self.search_products,
            self.check_stock,
            self.add_to_cart,
            self.list_my_orders,
            self.get_order_status,
            self.request_return,
            self.search_policies,
            self.escalate_to_human,
        ]

    def declarations(self) -> list[types.FunctionDeclaration]:
        """Lo que ve el LLM. use_json_schema=True conserva los enum de Literal (ej: product_type);
        sin él, product_type sería un string libre y el modelo podría inventar 'Nevera'."""
        return [
            types.FunctionDeclaration.from_callable_with_api_option(callable=function, use_json_schema=True)
            for function in self.functions()
        ]

    # --- Ventas ---

    def search_products(
        self,
        query: str,
        product_type: ProductType | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
    ) -> dict:
        """Busca productos del catálogo de HogarTec que tienen stock. Usar cuando el cliente busca o pide
        recomendaciones de productos. `query` describe lo que busca en palabras (ej: 'refrigerador no frost
        grande'). Usa product_type si el tipo es claro y min_price/max_price en pesos chilenos si el cliente
        menciona presupuesto (ej: 'bajo 500 mil' -> max_price=500000). Devuelve SKU, precio y especificaciones;
        compara las especificaciones para responder preguntas como 'el más grande'."""
        products = search_products_semantic(
            query, k=6, product_type=product_type, min_price=min_price, max_price=max_price, in_stock_only=True
        )
        return {
            "products": [
                {
                    "sku": product["sku"],
                    "name": product["name"],
                    "price": format_clp(product["sale_price"]),
                    "normal_price": format_clp(product["list_price"]) if product["list_price"] > product["sale_price"] else None,
                    "specifications": product["attributes"],
                }
                for product in products
            ]
        }

    def check_stock(self, sku: str) -> dict:
        """Consulta el stock disponible de un producto por su SKU (ej: 'SKU-100123'). Usar antes de confirmar
        disponibilidad al cliente."""
        try:
            inventory = self.client.get_inventory(sku)
        except CommerceError:
            return {"error": f"El SKU {sku} no existe"}
        available = sum(warehouse["totalQuantity"] - warehouse["reservedQuantity"] for warehouse in inventory["balance"])
        return {"sku": sku, "available_units": available, "in_stock": available > 0}

    def add_to_cart(self, sku: str, quantity: int = 1) -> dict:
        """Agrega un producto al carrito del cliente y devuelve el total y el link de pago. Usar solo cuando
        el cliente confirma explícitamente que quiere comprar ese producto."""
        if self.cart_id is None:
            self.cart_id = self.client.create_order_form()["orderFormId"]
        order_form = self.client.add_items(self.cart_id, sku, quantity)

        totals = {totalizer["id"]: cents_to_pesos(totalizer["value"]) for totalizer in order_form["totalizers"]}
        return {
            "cart_items": [
                {"name": item["name"], "quantity": item["quantity"], "unit_price": format_clp(cents_to_pesos(item["price"]))}
                for item in order_form["items"]
            ],
            "products_total": format_clp(totals.get("Items", 0)),
            "shipping": "Gratis" if totals.get("Shipping", 0) == 0 else format_clp(totals["Shipping"]),
            "total": format_clp(cents_to_pesos(order_form["value"])),
            # VTEX avisa la falta de stock en `messages` con HTTP 200: hay que revisarlo siempre.
            "warnings": [message["text"] for message in order_form["messages"]],
            "checkout_url": self.client.checkout_url(self.cart_id) if order_form["items"] else None,
        }

    # --- Postventa ---

    def list_my_orders(self) -> dict:
        """Lista los últimos pedidos del cliente que escribe, con sus productos. Usar cuando pregunta por
        'mi pedido' sin dar el número, o se refiere a un pedido por su fecha ('el de ayer') o por un
        producto ('los audífonos que compré')."""
        result = self.client.list_orders(self.customer_phone)
        orders = []
        for order in result["list"]:
            # El listado del OMS no trae productos: sin ellos, el agente tenía que abrir pedido por pedido
            # para encontrar "los audífonos" y agotaba sus rondas (caso post-03 de la evaluación).
            detail = self.client.get_order(order["orderId"])
            orders.append(
                {
                    "order_id": order["orderId"],
                    "date": order["creationDate"][:10],
                    "status": order["statusDescription"],
                    "products": [item["name"] for item in detail["items"]],
                    "total": format_clp(cents_to_pesos(order["totalValue"])),
                }
            )
        return {"today": self.client.settings.today.isoformat(), "orders": orders}

    def get_order_status(self, order_id: str) -> dict:
        """Consulta el estado, la fecha estimada de entrega y los productos de un pedido del cliente por su
        número (ej: '1045')."""
        try:
            order = self.client.get_order(order_id)
        except CommerceError:
            return {"error": "ORDER_NOT_FOUND", "guidance": ERROR_GUIDANCE["ORDER_NOT_FOUND"]}

        # Mismo mensaje si no existe o si es de otra persona: no se revela que el pedido existe.
        if order["clientProfileData"]["phone"] != self.customer_phone:
            return {"error": "ORDER_NOT_FOUND", "guidance": ERROR_GUIDANCE["ORDER_NOT_FOUND"]}

        logistics = order["shippingData"]["logisticsInfo"][0]
        return {
            "order_id": order_id,
            "customer_first_name": order["clientProfileData"]["firstName"].split()[0],
            "status": order["statusDescription"],
            "order_date": order["creationDate"][:10],
            "estimated_delivery": logistics["shippingEstimateDate"],
            # Calculado en código: el LLM no sabe qué día es hoy ni cuenta bien días hábiles (caso edge-01).
            "delivery_timing": delivery_timing(order["status"], logistics["shippingEstimateDate"], self.client.settings.today),
            "delivered_at": logistics["deliveredDate"][:10] if logistics["deliveredDate"] else None,
            "items": [{"sku": item["id"], "name": item["name"], "quantity": item["quantity"]} for item in order["items"]],
            "total": format_clp(cents_to_pesos(order["value"])),
        }

    def request_return(self, order_id: str, sku: str) -> dict:
        """Crea una solicitud de devolución por derecho a retracto para un producto de un pedido. Usar solo
        cuando el cliente confirma que quiere devolver ese producto. Si el producto tiene una falla, no usar:
        corresponde garantía."""
        try:
            created = self.client.create_return(order_id, sku, self.customer_phone)
        except CommerceError as error:
            return {"error": error.code, "guidance": ERROR_GUIDANCE.get(error.code, error.message)}
        return {
            "return_id": created["returnId"],
            "refund_amount": format_clp(cents_to_pesos(created["refundValue"])),
            "next_steps": created["message"],
        }

    # --- Información ---

    def search_policies(self, question: str) -> dict:
        """Busca en las políticas oficiales de HogarTec (despacho, devoluciones, garantía, medios de pago).
        Usar para cualquier pregunta sobre plazos, costos, condiciones o procedimientos. Responder solo con
        lo que digan estos fragmentos."""
        hits = rag_search_policies(question, k=4)
        return {"fragments": [{"source": f"{hit.source} > {hit.section}", "text": hit.content} for hit in hits]}

    # --- Derivación ---

    def escalate_to_human(self, reason: str) -> dict:
        """Deriva la conversación a un ejecutivo humano. Usar cuando la política lo indica: casos de
        garantía o producto con falla, pedido atrasado o que figura entregado pero no llegó, cambio de
        dirección de un pedido ya en preparación, o cuando las políticas no responden la consulta.
        `reason` resume el caso en una frase para el ejecutivo."""
        self.escalation_reason = reason
        return {"escalated": True}
