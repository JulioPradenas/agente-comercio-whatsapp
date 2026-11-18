"""Conexiones a Postgres (Supabase) con pool, leyendo DATABASE_URL del .env.

Abrir una conexión nueva cuesta ~2 s (TCP + TLS + autenticación hasta São Paulo).
El pool mantiene conexiones abiertas y las presta: cada consulta paga solo su propio tiempo.
"""

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    db_pool_min_size: int = 1
    db_pool_max_size: int = 5  # el plan gratuito de Supabase limita las conexiones simultáneas


def _configure(conn: psycopg.Connection) -> None:
    """Se ejecuta una vez por conexión nueva del pool."""
    register_vector(conn)  # numpy <-> tipo vector de pgvector
    conn.commit()


@lru_cache
def get_pool() -> ConnectionPool:
    settings = DatabaseSettings()
    return ConnectionPool(
        settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        # prepare_threshold=None desactiva los prepared statements: el pooler de Supabase
        # (PgBouncer/Supavisor) puede mover la sesión entre conexiones y romperlos.
        kwargs={"prepare_threshold": None},
        configure=_configure,
        # Sin check por préstamo: costaría un viaje extra (~200 ms desde Chile a São Paulo) en cada consulta.
        # En su lugar, las conexiones inactivas por más de 5 minutos se cierran y se reemplazan.
        max_idle=300,
        open=True,
    )


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Presta una conexión del pool. Al salir del bloque hace commit (o rollback si hubo error)."""
    with get_pool().connection() as conn:
        yield conn
