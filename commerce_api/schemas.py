"""Modelos de respuesta con la misma forma (simplificada) que la API de VTEX.

Los nombres de campo respetan los de VTEX, incluso los raros: `commertialOffer`
está mal escrito en la API original y ahí se queda; `Price` va con mayúscula.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


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


# --- Checkout: /api/checkout/pub/orderForm ---
# Todos los montos del Checkout y del OMS de VTEX van en centavos (enteros): $479.990 -> 47999000.


class OrderFormItemInput(BaseModel):
    id: str = Field(description="SKU")
    quantity: int = Field(ge=1, le=10)
    seller: str = "1"


class AddItemsRequest(BaseModel):
    orderItems: list[OrderFormItemInput]


class OrderFormItem(BaseModel):
    id: str
    name: str
    quantity: int
    seller: str = "1"
    price: int  # centavos
    listPrice: int  # centavos


class Totalizer(BaseModel):
    id: str  # "Items" o "Shipping"
    name: str
    value: int  # centavos


class Message(BaseModel):
    code: str  # ej: "withoutStock"
    text: str
    status: str = "error"


class OrderForm(BaseModel):
    orderFormId: str
    items: list[OrderFormItem]
    totalizers: list[Totalizer]
    value: int  # total en centavos
    messages: list[Message]


# --- OMS: /api/oms/pvt/orders ---


class OrderItem(BaseModel):
    id: str
    name: str
    quantity: int
    price: int  # centavos


class ClientProfile(BaseModel):
    firstName: str
    lastName: str
    email: str
    phone: str
    document: str  # RUT


class Address(BaseModel):
    street: str
    city: str
    state: str


class LogisticsInfo(BaseModel):
    shippingEstimateDate: date
    deliveredDate: datetime | None  # simplificación: en VTEX viene del tracking del transportista


class ShippingData(BaseModel):
    address: Address
    logisticsInfo: list[LogisticsInfo]


class Order(BaseModel):
    orderId: str
    status: str
    statusDescription: str
    creationDate: datetime
    value: int  # centavos
    totals: list[Totalizer]
    items: list[OrderItem]
    clientProfileData: ClientProfile
    shippingData: ShippingData


class OrderSummary(BaseModel):
    orderId: str
    creationDate: datetime
    status: str
    statusDescription: str
    totalValue: int  # centavos


class Paging(BaseModel):
    total: int
    pages: int
    currentPage: int
    perPage: int


class OrderList(BaseModel):
    list: list[OrderSummary]
    paging: Paging


# --- Devoluciones: /api/returns (NO es un endpoint nativo de VTEX) ---


class ReturnRequest(BaseModel):
    orderId: str
    sku: str
    requesterPhone: str = Field(description="Teléfono de quien pide la devolución, en formato 569XXXXXXXX")


class ReturnResponse(BaseModel):
    returnId: str
    orderId: str
    sku: str
    status: str
    refundValue: int  # centavos
    message: str
