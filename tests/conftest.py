import pytest
from fastapi.testclient import TestClient

from commerce_api.main import app
from commerce_api.store import Store, get_store

AUTH_HEADERS = {"X-VTEX-API-AppKey": "hogartec-dev-key", "X-VTEX-API-AppToken": "hogartec-dev-token"}


@pytest.fixture
def client():
    # Cada test recibe un Store nuevo: carritos y devoluciones de un test no contaminan al siguiente.
    # dependency_overrides reemplaza get_store sin tocar el código de los endpoints.
    fresh_store = Store()
    app.dependency_overrides[get_store] = lambda: fresh_store
    yield TestClient(app)
    app.dependency_overrides.clear()
