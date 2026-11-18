"""API de comercio simulada con la forma de los endpoints de VTEX.

Uso: uv run fastapi dev commerce_api/main.py --port 8001
Docs interactivas: http://localhost:8001/docs
"""

import re
from typing import Annotated

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query

from commerce_api.schemas import (
    CommertialOffer,
    InventoryResponse,
    Item,
    Product,
    Seller,
    WarehouseBalance,
)
from commerce_api.security import PrivateRoute
from commerce_api.store import Store, get_store

app = FastAPI(
    title="HogarTec Commerce API (VTEX-like)",
    description="API simulada que replica la forma de los endpoints de VTEX usados por el agente.",
    version="0.1.0",
)

StoreDep = Annotated[Store, Depends(get_store)]

# VTEX filtra precio con la sintaxis fq=P[min TO max]
PRICE_FILTER = re.compile(r"^P\[(\d+) TO (\d+)\]$")
MAX_PAGE_SIZE = 50  # VTEX no devuelve más de 50 productos por request


def to_vtex_product(row: pd.Series) -> Product:
    """Traduce una fila de nuestro catálogo al formato anidado de VTEX."""
    offer = CommertialOffer(Price=row["sale_price"], ListPrice=row["list_price"], AvailableQuantity=row["stock"])
    return Product(
        productId=row["sku"].removeprefix("SKU-"),
        productName=row["name"],
        brand=row["brand"],
        categories=[f"/{row['category']}/{row['product_type']}/", f"/{row['category']}/"],
        description=row["description"],
        specifications=row["attributes"],
        items=[Item(itemId=row["sku"], name=row["name"], sellers=[Seller(commertialOffer=offer)])],
    )


@app.get("/api/catalog_system/pub/products/search", response_model=list[Product], tags=["Catálogo"])
def search_products(
    store: StoreDep,
    ft: Annotated[str | None, Query(description="Texto libre, ej: 'refrigerador no frost'")] = None,
    fq: Annotated[str | None, Query(description="Filtro de precio, ej: 'P[0 TO 500000]'")] = None,
    from_: Annotated[int, Query(alias="_from", ge=0)] = 0,
    to: Annotated[int, Query(alias="_to", ge=0)] = 9,
) -> list[Product]:
    if to < from_ or to - from_ + 1 > MAX_PAGE_SIZE:
        raise HTTPException(status_code=400, detail=f"_to debe ser >= _from y el rango máximo es {MAX_PAGE_SIZE}")

    min_price = max_price = None
    if fq:
        match = PRICE_FILTER.match(fq)
        if not match:
            raise HTTPException(status_code=400, detail="fq soportado: P[min TO max]")
        min_price, max_price = int(match.group(1)), int(match.group(2))

    results = store.search_products(ft, min_price, max_price, offset=from_, limit=to - from_ + 1)
    return [to_vtex_product(row) for _, row in results.iterrows()]


@app.get(
    "/api/logistics/pvt/inventory/skus/{sku_id}",
    response_model=InventoryResponse,
    dependencies=[PrivateRoute],
    tags=["Inventario"],
)
def get_inventory(sku_id: str, store: StoreDep) -> InventoryResponse:
    product = store.get_product(sku_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} no existe")
    return InventoryResponse(
        skuId=sku_id,
        balance=[
            WarehouseBalance(
                warehouseId="1_1",
                warehouseName="Bodega Central Santiago",
                totalQuantity=int(product["stock"]),
                reservedQuantity=0,
            )
        ],
    )
