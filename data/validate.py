"""Chequeos de calidad e integridad de los datos sintéticos.

Uso: uv run python data/validate.py
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).parent / "raw"

products = pd.read_csv(RAW_DIR / "products.csv")
customers = pd.read_csv(RAW_DIR / "customers.csv", dtype={"phone": str})
orders = pd.read_csv(RAW_DIR / "orders.csv", dtype={"order_id": str}, parse_dates=["created_at", "delivered_at"])
order_items = pd.read_csv(RAW_DIR / "order_items.csv", dtype={"order_id": str})

for name, df in [("products", products), ("customers", customers), ("orders", orders), ("order_items", order_items)]:
    nulls = df.isna().sum()
    print(f"{name:12} shape={df.shape}  columnas con nulos={nulls[nulls > 0].to_dict()}")

checks = {
    "claves primarias únicas": products["sku"].is_unique and customers["customer_id"].is_unique and orders["order_id"].is_unique,
    "teléfonos únicos (identifican al cliente en WhatsApp)": customers["phone"].is_unique,
    "todo pedido tiene un cliente existente": orders["customer_id"].isin(customers["customer_id"]).all(),
    "todo ítem apunta a un pedido existente": order_items["order_id"].isin(orders["order_id"]).all(),
    "todo ítem apunta a un SKU existente": order_items["sku"].isin(products["sku"]).all(),
    "todo pedido tiene al menos un ítem": orders["order_id"].isin(order_items["order_id"]).all(),
    "items_total = suma de los ítems": (
        order_items.assign(subtotal=order_items["quantity"] * order_items["unit_price"])
        .groupby("order_id")["subtotal"].sum()
        .reindex(orders["order_id"]).to_numpy() == orders["items_total"].to_numpy()
    ).all(),
    "delivered_at solo en pedidos entregados": (orders["delivered_at"].notna() == (orders["status"] == "delivered")).all(),
    "entrega posterior a la compra": (orders["delivered_at"].dropna() >= orders.loc[orders["delivered_at"].notna(), "created_at"]).all(),
}

print()
for description, passed in checks.items():
    print(f"[{'OK' if passed else 'FALLA'}] {description}")

print("\nDistribución de estados:")
print(orders["status"].value_counts().to_string())
print("\nPedidos por cliente (describe):")
print(orders.groupby("customer_id").size().describe().round(1).to_string())
print("\nTicket promedio (CLP):", round(orders.loc[orders["status"] != "canceled", "order_total"].mean()))

if not all(checks.values()):
    raise SystemExit("Hay chequeos fallidos")
