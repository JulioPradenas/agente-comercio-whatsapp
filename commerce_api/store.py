"""Capa de datos de la API de comercio.

Por ahora lee los CSV de data/raw en memoria. Cuando migremos a Postgres (Supabase),
solo cambia este módulo: los endpoints no saben de dónde vienen los datos.
"""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import pandas as pd
from fastapi import Depends

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def normalize(text: str) -> str:
    """Minúsculas y sin tildes: 'Audífonos' y 'audifonos' deben encontrar lo mismo."""
    without_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return without_accents.lower()


class Store:
    def __init__(self, raw_dir: Path = RAW_DIR) -> None:
        self.products = pd.read_csv(raw_dir / "products.csv")
        self.products["attributes"] = self.products["attributes"].apply(json.loads)
        # Columna precalculada para buscar sin recalcular la normalización en cada request.
        self.products["search_text"] = (self.products["name"] + " " + self.products["description"]).apply(normalize)

        self.customers = pd.read_csv(raw_dir / "customers.csv", dtype={"phone": str})
        self.orders = pd.read_csv(
            raw_dir / "orders.csv",
            dtype={"order_id": str},
            parse_dates=["created_at", "delivered_at", "estimated_delivery"],
        )
        self.order_items = pd.read_csv(raw_dir / "order_items.csv", dtype={"order_id": str})

        # Estado mutable en memoria: carritos y devoluciones creados durante la ejecución.
        # Se pierde al reiniciar y no se comparte entre procesos; suficiente para una API simulada.
        self.order_forms: dict[str, dict[str, int]] = {}  # orderFormId -> {sku: cantidad}
        self.returns: dict[str, dict] = {}  # returnId -> datos de la devolución

    # --- Catálogo ---

    def search_products(
        self, text: str | None, min_price: int | None, max_price: int | None, offset: int, limit: int
    ) -> pd.DataFrame:
        results = self.products
        if text:
            # Todas las palabras deben aparecer (AND), en cualquier orden.
            for term in normalize(text).split():
                results = results[results["search_text"].str.contains(term, regex=False)]
        if min_price is not None:
            results = results[results["sale_price"] >= min_price]
        if max_price is not None:
            results = results[results["sale_price"] <= max_price]
        return results.iloc[offset : offset + limit]

    def get_product(self, sku: str) -> pd.Series | None:
        match = self.products[self.products["sku"] == sku]
        return None if match.empty else match.iloc[0]

    # --- Clientes y pedidos ---

    def get_customer(self, customer_id: str) -> pd.Series:
        return self.customers[self.customers["customer_id"] == customer_id].iloc[0]

    def get_order(self, order_id: str) -> pd.Series | None:
        match = self.orders[self.orders["order_id"] == order_id]
        return None if match.empty else match.iloc[0]

    def get_order_items(self, order_id: str) -> pd.DataFrame:
        return self.order_items[self.order_items["order_id"] == order_id]

    def find_orders_by_client(self, query: str) -> pd.DataFrame:
        """Busca por teléfono, email o RUT exactos, como el parámetro `q` del OMS de VTEX."""
        query = query.strip().lstrip("+")
        matches = self.customers[
            (self.customers["phone"] == query)
            | (self.customers["email"].str.lower() == query.lower())
            | (self.customers["rut"] == query)
        ]
        orders = self.orders[self.orders["customer_id"].isin(matches["customer_id"])]
        return orders.sort_values("created_at", ascending=False)


@lru_cache
def get_store() -> Store:
    """Una sola instancia por proceso (los CSV se leen una vez, no en cada request)."""
    return Store()


StoreDep = Annotated[Store, Depends(get_store)]
