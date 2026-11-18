"""Modelos de respuesta con la misma forma (simplificada) que la API de VTEX.

Los nombres de campo respetan los de VTEX, incluso los raros: `commertialOffer`
está mal escrito en la API original y ahí se queda; `Price` va con mayúscula.
"""

from pydantic import BaseModel


# --- Catálogo: GET /api/catalog_system/pub/products/search ---


class CommertialOffer(BaseModel):
    Price: int  # precio de venta (con descuento si lo hay)
    ListPrice: int  # precio normal, tachado en la web cuando hay descuento
    AvailableQuantity: int


class Seller(BaseModel):
    sellerId: str = "1"  # "1" es la tienda principal en VTEX; otros IDs serían marketplace
    sellerName: str = "HogarTec"
    commertialOffer: CommertialOffer


class Item(BaseModel):
    """Un SKU: la variante comprable de un producto."""

    itemId: str
    name: str
    sellers: list[Seller]


class Product(BaseModel):
    productId: str
    productName: str
    brand: str
    categories: list[str]  # VTEX usa rutas tipo "/Línea blanca/"
    description: str
    specifications: dict[str, str | int | float]  # simplificación: VTEX las pone como claves sueltas
    items: list[Item]


# --- Inventario: GET /api/logistics/pvt/inventory/skus/{skuId} ---


class WarehouseBalance(BaseModel):
    warehouseId: str
    warehouseName: str
    totalQuantity: int
    reservedQuantity: int


class InventoryResponse(BaseModel):
    skuId: str
    balance: list[WarehouseBalance]
