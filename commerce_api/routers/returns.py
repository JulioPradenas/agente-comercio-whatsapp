"""Solicitudes de devolución por derecho a retracto.

NO es un endpoint nativo de VTEX (allí se resuelve con apps de terceros).
Las reglas implementan data/policies/devoluciones.md: la API es la fuente de verdad,
así que aunque el agente se equivoque, una devolución inválida nunca se crea.
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from commerce_api.config import settings
from commerce_api.routers.checkout import to_cents
from commerce_api.schemas import ReturnRequest, ReturnResponse
from commerce_api.security import PrivateRoute
from commerce_api.store import StoreDep

router = APIRouter(prefix="/api/returns", tags=["Devoluciones"], dependencies=[PrivateRoute])


def reject(http_status: int, code: str, message: str) -> HTTPException:
    """Error de negocio con código estable: el agente decide qué decir según `code`, no según el texto."""
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})


@router.post("", response_model=ReturnResponse, status_code=status.HTTP_201_CREATED)
def create_return(body: ReturnRequest, store: StoreDep) -> ReturnResponse:
    order = store.get_order(body.orderId)
    if order is None:
        raise reject(404, "ORDER_NOT_FOUND", f"El pedido {body.orderId} no existe")

    # Solo el dueño del pedido puede devolver: el teléfono de WhatsApp debe coincidir con el del cliente.
    customer = store.get_customer(order["customer_id"])
    if body.requesterPhone.lstrip("+") != customer["phone"]:
        raise reject(403, "ORDER_NOT_OWNED", "El pedido no pertenece a este número de teléfono")

    items = store.get_order_items(body.orderId)
    item = items[items["sku"] == body.sku]
    if item.empty:
        raise reject(422, "SKU_NOT_IN_ORDER", f"El producto {body.sku} no está en el pedido {body.orderId}")

    if order["status"] != "delivered":
        raise reject(422, "ORDER_NOT_DELIVERED", f"El pedido está '{order['status_label']}'; solo se devuelven pedidos entregados")

    days_since_delivery = (settings.today - order["delivered_at"].date()).days
    if days_since_delivery > settings.return_window_days:
        raise reject(
            422,
            "RETURN_WINDOW_EXPIRED",
            f"Pasaron {days_since_delivery} días desde la entrega; el plazo de retracto es de {settings.return_window_days} días",
        )

    product = store.get_product(body.sku)
    if product["product_type"] == "Audífonos" and product["attributes"].get("tipo") == "In-ear":
        raise reject(422, "HYGIENE_PRODUCT", "Los audífonos in-ear no aplican para retracto por razones sanitarias")

    already_requested = any(r["orderId"] == body.orderId and r["sku"] == body.sku for r in store.returns.values())
    if already_requested:
        raise reject(409, "RETURN_ALREADY_REQUESTED", "Ya existe una solicitud de devolución para este producto")

    return_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
    quantity = int(item.iloc[0]["quantity"])
    refund = to_cents(item.iloc[0]["unit_price"]) * quantity
    store.returns[return_id] = {"orderId": body.orderId, "sku": body.sku, "refundValue": refund}

    return ReturnResponse(
        returnId=return_id,
        orderId=body.orderId,
        sku=body.sku,
        status="requested",
        refundValue=refund,
        message="Solicitud creada. Recibirás por correo la etiqueta para enviar el producto sin costo.",
    )
