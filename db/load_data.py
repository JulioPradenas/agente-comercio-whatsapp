"""Carga los CSV de data/raw en Supabase reemplazando el contenido anterior.

Uso: uv run python -m db.load_data
"""

import time
from pathlib import Path

import pandas as pd

from db.connection import get_connection

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Orden importante: primero las tablas "padre" (sin llaves foráneas hacia otras).
TABLES = ["products", "customers", "orders", "order_items"]
STRING_COLUMNS = {"phone": str, "order_id": str}


def load_table(conn, table: str) -> int:
    df = pd.read_csv(RAW_DIR / f"{table}.csv", dtype=STRING_COLUMNS)
    # NaN de pandas -> None, que psycopg convierte en NULL de SQL.
    rows = df.astype(object).where(df.notna(), None).itertuples(index=False, name=None)
    columns = ", ".join(df.columns)

    with conn.cursor().copy(f"COPY {table} ({columns}) FROM STDIN") as copy:
        for row in rows:
            copy.write_row(row)
    return len(df)


def load_all() -> None:
    with get_connection() as conn, conn.transaction():
        # Las fechas del CSV no tienen zona horaria: se interpretan como hora de Chile.
        conn.execute("SET LOCAL timezone = 'America/Santiago'")
        # TRUNCATE + carga dentro de una transacción: si algo falla, la base queda como estaba.
        conn.execute(f"TRUNCATE {', '.join(TABLES)}")
        for table in TABLES:
            start = time.perf_counter()
            n_rows = load_table(conn, table)
            print(f"  {table:12} {n_rows:>5} filas en {time.perf_counter() - start:.2f} s")


if __name__ == "__main__":
    load_all()
