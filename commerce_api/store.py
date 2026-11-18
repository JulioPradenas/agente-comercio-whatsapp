"""Capa de datos de la API de comercio.

Por ahora lee los CSV de data/raw en memoria. Cuando migremos a Postgres (Supabase),
solo cambia este módulo: los endpoints no saben de dónde vienen los datos.
"""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd

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
        self.orders = pd.read_csv(raw_dir / "orders.csv", dtype={"order_id": str})
        self.order_items = pd.read_csv(raw_dir / "order_items.csv", dtype={"order_id": str})

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


@lru_cache
def get_store() -> Store:
    """Una sola instancia por proceso (los CSV se leen una vez, no en cada request)."""
    return Store()
