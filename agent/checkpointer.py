"""Memoria del agente en Postgres (Supabase) con PostgresSaver de LangGraph.

En Cloud Run el contenedor se apaga cuando no hay tráfico: con InMemorySaver cada cliente
perdería su conversación y su carrito. PostgresSaver guarda el estado después de cada turno.
"""

from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from db.connection import DatabaseSettings

CHECKPOINT_TABLES = ["checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations"]


@lru_cache
def get_postgres_checkpointer() -> PostgresSaver:
    settings = DatabaseSettings()
    # Pool propio: PostgresSaver exige autocommit y filas como diccionarios.
    pool = ConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=3,
        kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None},
        max_idle=300,
        open=True,
    )
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()  # crea sus tablas si no existen (idempotente)

    # Las tablas quedan en el esquema public: igual que las nuestras, se protegen de la API REST de Supabase.
    with pool.connection() as conn:
        for table in CHECKPOINT_TABLES:
            conn.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    return checkpointer
