"""Genera clientes, pedidos e ítems de pedido a partir del catálogo.

Requiere: data/raw/products.csv (ejecutar antes data/generate_catalog.py)
Salida:   data/raw/customers.csv, data/raw/orders.csv, data/raw/order_items.csv
Uso:      uv run python data/generate_orders.py
"""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
N_CUSTOMERS = 200
N_ORDERS = 1_000
# Fecha fija en vez de datetime.now(): si no, cada ejecución cambiaría
# los estados de los pedidos y los casos de evaluación dejarían de ser válidos.
REFERENCE_DATE = datetime(2026, 11, 20, 12, 0)
RAW_DIR = Path(__file__).parent / "raw"

# Estados de pedido con los nombres que usa el OMS de VTEX.
# "delivered" no es un estado nativo de VTEX (allí viene del tracking),
# pero lo incluimos porque es lo que el cliente pregunta.
STATUS_LABELS_ES = {
    "payment-pending": "Pago pendiente",
    "ready-for-handling": "Pago aprobado, en preparación",
    "handling": "Preparando tu pedido",
    "invoiced": "Despachado, en camino",
    "delivered": "Entregado",
    "canceled": "Cancelado",
}


def chilean_mobile(rng: np.random.Generator) -> str:
    """Celular en formato E.164 sin '+', igual al `wa_id` que envía WhatsApp."""
    return f"569{rng.integers(10_000_000, 100_000_000)}"


def generate_customers(n_customers: int, fake: Faker, rng: np.random.Generator) -> pd.DataFrame:
    customers = [
        {
            "customer_id": f"C{1_000 + i}",
            "full_name": fake.name(),
            "rut": fake.rut(),
            "email": fake.free_email(),
            "phone": chilean_mobile(rng),
            "region": fake.administrative_unit(),
            "city": fake.city(),
            "address": fake.street_address(),
        }
        for i in range(n_customers)
    ]
    return pd.DataFrame(customers)


def status_for_age(days_old: float, rng: np.random.Generator) -> str:
    """El estado depende de la antigüedad del pedido, como en la vida real."""
    if rng.random() < 0.05:
        return "canceled"
    if days_old < 1:
        return str(rng.choice(["payment-pending", "ready-for-handling"]))
    if days_old < 3:
        return str(rng.choice(["ready-for-handling", "handling"]))
    if days_old < 6:
        return str(rng.choice(["handling", "invoiced"], p=[0.3, 0.7]))
    if days_old < 10:
        return str(rng.choice(["invoiced", "delivered"], p=[0.3, 0.7]))
    return "delivered"


def generate_orders(
    customers: pd.DataFrame, products: pd.DataFrame, n_orders: int, rng: np.random.Generator
) -> tuple[pd.DataFrame, pd.DataFrame]:
    in_stock = products[products["stock"] > 0]

    # Algunos clientes compran mucho más que otros (Pareto): pesos con distribución exponencial.
    customer_weights = rng.exponential(1.0, len(customers))
    customer_weights /= customer_weights.sum()

    orders, items = [], []
    for i in range(n_orders):
        order_id = str(1_001 + i)
        customer = customers.iloc[rng.choice(len(customers), p=customer_weights)]

        days_old = rng.uniform(0, 90)
        created_at = REFERENCE_DATE - timedelta(days=days_old)
        status = status_for_age(days_old, rng)

        # 1 a 3 productos distintos; la mayoría de los pedidos tiene 1.
        n_items = rng.choice([1, 2, 3], p=[0.70, 0.22, 0.08])
        chosen = in_stock.sample(n=n_items, random_state=int(rng.integers(0, 2**31)))
        order_total = 0
        for _, product in chosen.iterrows():
            quantity = int(rng.choice([1, 2], p=[0.9, 0.1]))
            items.append(
                {
                    "order_id": order_id,
                    "sku": product["sku"],
                    "product_name": product["name"],
                    "quantity": quantity,
                    # Se copia el precio del momento de la compra: si el catálogo cambia
                    # mañana, el pedido histórico no debe cambiar.
                    "unit_price": product["sale_price"],
                }
            )
            order_total += quantity * product["sale_price"]

        shipping_cost = 0 if order_total >= 49_990 else 3_990
        estimated_delivery = created_at + timedelta(days=int(rng.integers(3, 8)))
        delivered_at = (
            min(estimated_delivery + timedelta(days=int(rng.integers(-1, 3))), REFERENCE_DATE)
            if status == "delivered"
            else None
        )

        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "created_at": created_at.replace(microsecond=0),
                "status": status,
                "status_label": STATUS_LABELS_ES[status],
                "items_total": order_total,
                "shipping_cost": shipping_cost,
                "order_total": order_total + shipping_cost,
                "estimated_delivery": estimated_delivery.date(),
                "delivered_at": delivered_at.replace(microsecond=0) if delivered_at else None,
                "shipping_address": f"{customer['address']}, {customer['city']}",
            }
        )

    return pd.DataFrame(orders), pd.DataFrame(items)


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    fake = Faker("es_CL")
    Faker.seed(SEED)

    products = pd.read_csv(RAW_DIR / "products.csv")
    customers = generate_customers(N_CUSTOMERS, fake, rng)
    orders, order_items = generate_orders(customers, products, N_ORDERS, rng)

    for table_name, df in [("customers", customers), ("orders", orders), ("order_items", order_items)]:
        df.to_csv(RAW_DIR / f"{table_name}.csv", index=False)
        print(f"Guardado: {table_name}.csv {df.shape}")
