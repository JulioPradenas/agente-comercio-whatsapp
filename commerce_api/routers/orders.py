"""Pedidos (OMS API de VTEX). Rutas privadas: contienen datos personales."""

import math
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from commerce_api.routers.checkout import to_cents
from commerce_api.schemas import (
    Address,
    ClientProfile,
    LogisticsInfo,
    Order,
    OrderItem,
    OrderList,
    OrderSummary,
    Paging,
    ShippingData,
    Totalizer,
)
from commerce_api.security import PrivateRoute
from commerce_api.store import StoreDep

router = APIRouter(prefix="/api/oms/pvt/orders", tags=["Pedidos"], dependencies=[PrivateRoute])


def split_name(full_name: str) -> tuple[str, str]:
    """'Margarita Daniela Mansilla Concha' -> ('Margarita Daniela', 'Mansilla Concha')."""
    parts = full_name.split()
    return " ".join(parts[:-2]) or parts[0], " ".join(parts[-2:])


@router.get("/{order_id}", response_model=Order)
def get_order(order_id: str, store: StoreDep) -> Order:
    order = store.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Pedido {order_id} no existe")

    customer = store.get_customer(order["customer_id"])
    first_name, last_name = split_name(customer["full_name"])
    items = store.get_order_items(order_id)

    return Order(
        orderId=order_id,
        status=order["status"],
        statusDescription=order["status_label"],
        creationDate=order["created_at"],
        value=to_cents(order["order_total"]),
        totals=[
            Totalizer(id="Items", name="Total de los productos", value=to_cents(order["items_total"])),
            Totalizer(id="Shipping", name="Costo de despacho", value=to_cents(order["shipping_cost"])),
        ],
        items=[
            OrderItem(id=item["sku"], name=item["product_name"], quantity=item["quantity"], price=to_cents(item["unit_price"]))
            for _, item in items.iterrows()
        ],
        clientProfileData=ClientProfile(
            firstName=first_name,
            lastName=last_name,
            email=customer["email"],
            phone=customer["phone"],
            document=customer["rut"],
        ),
        shippingData=ShippingData(
            address=Address(street=customer["address"], city=customer["city"], state=customer["region"]),
            logisticsInfo=[
                LogisticsInfo(
                    shippingEstimateDate=order["estimated_delivery"].date(),
                    deliveredDate=None if pd.isna(order["delivered_at"]) else order["delivered_at"],
                )
            ],
        ),
    )


@router.get("", response_model=OrderList)
def list_orders(
    store: StoreDep,
    q: Annotated[str, Query(min_length=3, description="Teléfono (569...), email o RUT del cliente")],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 15,
) -> OrderList:
    orders = store.find_orders_by_client(q)
    page_orders = orders.iloc[(page - 1) * per_page : page * per_page]

    return OrderList(
        list=[
            OrderSummary(
                orderId=order["order_id"],
                creationDate=order["created_at"],
                status=order["status"],
                statusDescription=order["status_label"],
                totalValue=to_cents(order["order_total"]),
            )
            for _, order in page_orders.iterrows()
        ],
        paging=Paging(
            total=len(orders), pages=math.ceil(len(orders) / per_page), currentPage=page, perPage=per_page
        ),
    )
