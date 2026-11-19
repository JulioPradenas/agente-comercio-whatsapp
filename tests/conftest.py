import os

# Antes de importar el agente: los tests no deben enviar trazas a Langfuse (ensuciarían el costo
# por conversación y los KPIs). load_dotenv() no sobrescribe variables ya definidas, así que esto gana.
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from commerce_api.main import app  # noqa: E402
from commerce_api.store import Store, get_store  # noqa: E402

AUTH_HEADERS = {"X-VTEX-API-AppKey": "hogartec-dev-key", "X-VTEX-API-AppToken": "hogartec-dev-token"}


@pytest.fixture
def client():
    # Cada test recibe un Store nuevo: carritos y devoluciones de un test no contaminan al siguiente.
    # dependency_overrides reemplaza get_store sin tocar el código de los endpoints.
    fresh_store = Store()
    app.dependency_overrides[get_store] = lambda: fresh_store
    yield TestClient(app)
    app.dependency_overrides.clear()
