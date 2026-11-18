from fastapi.testclient import TestClient

from commerce_api.main import app

client = TestClient(app)
AUTH_HEADERS = {"X-VTEX-API-AppKey": "hogartec-dev-key", "X-VTEX-API-AppToken": "hogartec-dev-token"}
SEARCH_URL = "/api/catalog_system/pub/products/search"


def test_search_returns_vtex_shape():
    response = client.get(SEARCH_URL, params={"ft": "refrigerador"})
    assert response.status_code == 200
    product = response.json()[0]
    offer = product["items"][0]["sellers"][0]["commertialOffer"]
    assert set(offer) == {"Price", "ListPrice", "AvailableQuantity"}
    assert "Refrigerador" in product["productName"]


def test_search_ignores_accents_and_case():
    with_accent = client.get(SEARCH_URL, params={"ft": "Audífonos"}).json()
    without_accent = client.get(SEARCH_URL, params={"ft": "audifonos"}).json()
    assert len(with_accent) > 0
    assert with_accent == without_accent


def test_search_requires_all_terms():
    results = client.get(SEARCH_URL, params={"ft": "refrigerador no frost", "_to": 49}).json()
    assert results
    assert all("No Frost" in product["productName"] for product in results)


def test_price_filter():
    results = client.get(SEARCH_URL, params={"ft": "smart tv", "fq": "P[0 TO 500000]", "_to": 49}).json()
    prices = [product["items"][0]["sellers"][0]["commertialOffer"]["Price"] for product in results]
    assert prices
    assert max(prices) <= 500_000


def test_page_size_limit():
    assert client.get(SEARCH_URL, params={"_from": 0, "_to": 50}).status_code == 400


def test_inventory_requires_credentials():
    assert client.get("/api/logistics/pvt/inventory/skus/SKU-100000").status_code == 401


def test_inventory_with_credentials():
    response = client.get("/api/logistics/pvt/inventory/skus/SKU-100000", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["balance"][0]["totalQuantity"] >= 0


def test_inventory_unknown_sku():
    assert client.get("/api/logistics/pvt/inventory/skus/SKU-999999", headers=AUTH_HEADERS).status_code == 404
