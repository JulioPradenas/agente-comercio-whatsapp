from tests.conftest import AUTH_HEADERS

# Pedidos reales de data/raw elegidos para cada escenario (fecha de referencia: 20-nov-2026).
RETURNABLE = {"orderId": "1011", "sku": "SKU-100224", "requesterPhone": "56989910085"}  # entregado hace 8 días
EXPIRED = {"orderId": "1001", "sku": "SKU-100104", "requesterPhone": "56949169500"}  # entregado hace 28 días
IN_TRANSIT = {"orderId": "1006", "sku": "SKU-100159", "requesterPhone": "56934889349"}  # despachado
IN_EAR = {"orderId": "1009", "sku": "SKU-100065", "requesterPhone": "56964647678"}  # audífonos in-ear


def first_sku(client, query: str, in_stock: bool) -> dict:
    products = client.get("/api/catalog_system/pub/products/search", params={"ft": query, "_to": 49}).json()
    for product in products:
        offer = product["items"][0]["sellers"][0]["commertialOffer"]
        if (offer["AvailableQuantity"] > 0) == in_stock:
            return {"sku": product["items"][0]["itemId"], "price": offer["Price"], "stock": offer["AvailableQuantity"]}
    raise AssertionError("No hay producto para el escenario")


# --- Checkout ---


def test_add_item_prices_in_cents_and_free_shipping(client):
    product = first_sku(client, "refrigerador", in_stock=True)
    order_form_id = client.post("/api/checkout/pub/orderForm").json()["orderFormId"]

    order_form = client.post(
        f"/api/checkout/pub/orderForm/{order_form_id}/items",
        json={"orderItems": [{"id": product["sku"], "quantity": 1}]},
    ).json()

    assert order_form["items"][0]["price"] == product["price"] * 100
    shipping = next(t for t in order_form["totalizers"] if t["id"] == "Shipping")
    assert shipping["value"] == 0  # un refrigerador supera los $49.990
    assert order_form["messages"] == []


def test_cheap_order_pays_shipping(client):
    products = client.get("/api/catalog_system/pub/products/search", params={"fq": "P[0 TO 49980]", "_to": 49}).json()
    cheap = next(p for p in products if p["items"][0]["sellers"][0]["commertialOffer"]["AvailableQuantity"] > 0)
    order_form_id = client.post("/api/checkout/pub/orderForm").json()["orderFormId"]

    order_form = client.post(
        f"/api/checkout/pub/orderForm/{order_form_id}/items",
        json={"orderItems": [{"id": cheap["items"][0]["itemId"], "quantity": 1}]},
    ).json()

    shipping = next(t for t in order_form["totalizers"] if t["id"] == "Shipping")
    assert shipping["value"] == 3_990 * 100


def test_out_of_stock_returns_message_not_error(client):
    product = first_sku(client, "refrigerador", in_stock=False)
    order_form_id = client.post("/api/checkout/pub/orderForm").json()["orderFormId"]

    response = client.post(
        f"/api/checkout/pub/orderForm/{order_form_id}/items",
        json={"orderItems": [{"id": product["sku"], "quantity": 1}]},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["messages"][0]["code"] == "withoutStock"


def test_unknown_order_form(client):
    assert client.get("/api/checkout/pub/orderForm/no-existe").status_code == 404


# --- OMS ---


def test_get_order_requires_credentials(client):
    assert client.get("/api/oms/pvt/orders/1011").status_code == 401


def test_get_order(client):
    order = client.get("/api/oms/pvt/orders/1006", headers=AUTH_HEADERS).json()
    assert order["status"] == "invoiced"
    assert order["statusDescription"] == "Despachado, en camino"
    assert order["value"] == sum(t["value"] for t in order["totals"])


def test_list_orders_by_phone(client):
    result = client.get("/api/oms/pvt/orders", params={"q": "56989910085"}, headers=AUTH_HEADERS).json()
    assert result["paging"]["total"] >= 1
    assert "1011" in [order["orderId"] for order in result["list"]]


def test_list_orders_unknown_phone(client):
    result = client.get("/api/oms/pvt/orders", params={"q": "56900000000"}, headers=AUTH_HEADERS).json()
    assert result["paging"]["total"] == 0


# --- Devoluciones ---


def test_return_created(client):
    response = client.post("/api/returns", json=RETURNABLE, headers=AUTH_HEADERS)
    assert response.status_code == 201
    assert response.json()["status"] == "requested"


def test_return_duplicate(client):
    client.post("/api/returns", json=RETURNABLE, headers=AUTH_HEADERS)
    response = client.post("/api/returns", json=RETURNABLE, headers=AUTH_HEADERS)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "RETURN_ALREADY_REQUESTED"


def test_return_from_another_phone_is_rejected(client):
    response = client.post("/api/returns", json={**RETURNABLE, "requesterPhone": "56911111111"}, headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ORDER_NOT_OWNED"


def test_return_window_expired(client):
    response = client.post("/api/returns", json=EXPIRED, headers=AUTH_HEADERS)
    assert response.json()["detail"]["code"] == "RETURN_WINDOW_EXPIRED"


def test_return_not_delivered(client):
    response = client.post("/api/returns", json=IN_TRANSIT, headers=AUTH_HEADERS)
    assert response.json()["detail"]["code"] == "ORDER_NOT_DELIVERED"


def test_return_hygiene_product(client):
    response = client.post("/api/returns", json=IN_EAR, headers=AUTH_HEADERS)
    assert response.json()["detail"]["code"] == "HYGIENE_PRODUCT"


def test_return_sku_not_in_order(client):
    response = client.post("/api/returns", json={**RETURNABLE, "sku": "SKU-100000"}, headers=AUTH_HEADERS)
    assert response.json()["detail"]["code"] == "SKU_NOT_IN_ORDER"
