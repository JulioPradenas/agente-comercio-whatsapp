"""Carrito (Checkout API de VTEX). El carrito se llama orderForm."""

import uuid

from fastapi import APIRouter, HTTPException

from commerce_api.config import settings
from commerce_api.schemas import AddItemsRequest, Message, OrderForm, OrderFormItem, Totalizer
from commerce_api.store import Store, StoreDep

router = APIRouter(prefix="/api/checkout/pub/orderForm", tags=["Checkout"])


def to_cents(pesos: int) -> int:
    return int(pesos) * 100


def build_order_form(order_form_id: str, cart: dict[str, int], store: Store, messages: list[Message]) -> OrderForm:
    items = []
    for sku, quantity in cart.items():
        product = store.get_product(sku)
        items.append(
            OrderFormItem(
                id=sku,
                name=product["name"],
                quantity=quantity,
                price=to_cents(product["sale_price"]),
                listPrice=to_cents(product["list_price"]),
            )
        )

    items_total = sum(item.price * item.quantity for item in items)
    # Regla de data/policies/despacho.md: $3.990, gratis desde $49.990 en productos.
    charges_shipping = items and items_total < to_cents(settings.free_shipping_threshold)
    shipping = to_cents(settings.shipping_cost) if charges_shipping else 0

    return OrderForm(
        orderFormId=order_form_id,
        items=items,
        totalizers=[
            Totalizer(id="Items", name="Total de los productos", value=items_total),
            Totalizer(id="Shipping", name="Costo de despacho", value=shipping),
        ],
        value=items_total + shipping,
        messages=messages,
    )


def get_cart_or_404(order_form_id: str, store: Store) -> dict[str, int]:
    if order_form_id not in store.order_forms:
        raise HTTPException(status_code=404, detail=f"orderForm {order_form_id} no existe")
    return store.order_forms[order_form_id]


@router.post("", response_model=OrderForm)
def create_order_form(store: StoreDep) -> OrderForm:
    order_form_id = uuid.uuid4().hex
    store.order_forms[order_form_id] = {}
    return build_order_form(order_form_id, {}, store, messages=[])


@router.get("/{order_form_id}", response_model=OrderForm)
def get_order_form(order_form_id: str, store: StoreDep) -> OrderForm:
    cart = get_cart_or_404(order_form_id, store)
    return build_order_form(order_form_id, cart, store, messages=[])


@router.post("/{order_form_id}/items", response_model=OrderForm)
def add_items(order_form_id: str, body: AddItemsRequest, store: StoreDep) -> OrderForm:
    cart = get_cart_or_404(order_form_id, store)
    messages = []

    for item in body.orderItems:
        product = store.get_product(item.id)
        if product is None:
            messages.append(Message(code="skuNotFound", text=f"El SKU {item.id} no existe"))
            continue

        requested = cart.get(item.id, 0) + item.quantity
        if requested > product["stock"]:
            # Como VTEX: no es un error HTTP; el carrito se devuelve sin ese ítem y con un mensaje.
            messages.append(
                Message(
                    code="withoutStock",
                    text=f"{product['name']} no tiene stock suficiente (disponible: {product['stock']})",
                )
            )
            continue

        cart[item.id] = requested

    return build_order_form(order_form_id, cart, store, messages)
