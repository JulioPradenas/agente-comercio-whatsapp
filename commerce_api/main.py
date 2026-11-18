"""API de comercio simulada con la forma de los endpoints de VTEX.

Uso: uv run fastapi dev commerce_api/main.py --port 8001
Docs interactivas: http://localhost:8001/docs
"""

from fastapi import FastAPI

from commerce_api.routers import catalog, checkout, orders, returns

app = FastAPI(
    title="HogarTec Commerce API (VTEX-like)",
    description="API simulada que replica la forma de los endpoints de VTEX usados por el agente.",
    version="0.2.0",
)

app.include_router(catalog.router)
app.include_router(checkout.router)
app.include_router(orders.router)
app.include_router(returns.router)
