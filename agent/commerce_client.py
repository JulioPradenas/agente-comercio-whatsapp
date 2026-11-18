"""Cliente HTTP de la API de comercio con forma VTEX.

Es el único módulo que conoce las rutas de VTEX: para usar VTEX real basta cambiar
COMMERCE_API_URL y las credenciales.
"""

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClientSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COMMERCE_", env_file=".env", extra="ignore")
    api_url: str = "http://localhost:8001"
    app_key: str = "hogartec-dev-key"
    app_token: str = "hogartec-dev-token"
    store_url: str = "https://hogartec.example"


class CommerceError(Exception):
    """Error de negocio de la API (4xx) con su código estable, ej: RETURN_WINDOW_EXPIRED."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(f"{status_code} {code}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message


class CommerceClient:
    def __init__(self, http: httpx.Client | None = None, settings: ClientSettings | None = None) -> None:
        self.settings = settings or ClientSettings()
        # Se puede inyectar otro cliente: en los tests usamos el TestClient de FastAPI (sin red).
        self.http = http or httpx.Client(base_url=self.settings.api_url, timeout=10)
        self.private_headers = {
            "X-VTEX-API-AppKey": self.settings.app_key,
            "X-VTEX-API-AppToken": self.settings.app_token,
        }

    def _request(self, method: str, path: str, private: bool = False, **kwargs) -> dict | list:
        headers = self.private_headers if private else {}
        response = self.http.request(method, path, headers=headers, **kwargs)
        if response.is_client_error:
            detail = response.json().get("detail")
            if isinstance(detail, dict):
                raise CommerceError(response.status_code, detail["code"], detail["message"])
            raise CommerceError(response.status_code, f"HTTP_{response.status_code}", str(detail))
        response.raise_for_status()  # 5xx: error de infraestructura, no de negocio
        return response.json()

    def get_inventory(self, sku: str) -> dict:
        return self._request("GET", f"/api/logistics/pvt/inventory/skus/{sku}", private=True)

    def create_order_form(self) -> dict:
        return self._request("POST", "/api/checkout/pub/orderForm")

    def add_items(self, order_form_id: str, sku: str, quantity: int) -> dict:
        body = {"orderItems": [{"id": sku, "quantity": quantity, "seller": "1"}]}
        return self._request("POST", f"/api/checkout/pub/orderForm/{order_form_id}/items", json=body)

    def get_order(self, order_id: str) -> dict:
        return self._request("GET", f"/api/oms/pvt/orders/{order_id}", private=True)

    def list_orders(self, client_query: str, per_page: int = 5) -> dict:
        return self._request("GET", "/api/oms/pvt/orders", private=True, params={"q": client_query, "per_page": per_page})

    def create_return(self, order_id: str, sku: str, requester_phone: str) -> dict:
        body = {"orderId": order_id, "sku": sku, "requesterPhone": requester_phone}
        return self._request("POST", "/api/returns", private=True, json=body)

    def checkout_url(self, order_form_id: str) -> str:
        return f"{self.settings.store_url}/checkout/?orderFormId={order_form_id}"
