"""Búsqueda semántica sobre políticas y productos en pgvector."""

from dataclasses import dataclass

from pgvector.psycopg import register_vector

from db.connection import get_connection
from rag.embeddings import embed_query


@dataclass
class PolicyHit:
    chunk_id: str
    source: str
    section: str
    content: str
    similarity: float


def search_policies(question: str, k: int = 4) -> list[PolicyHit]:
    query_vector = embed_query(question)
    with get_connection() as conn:
        register_vector(conn)
        # <=> es distancia coseno (0 = idéntico); similitud = 1 - distancia.
        rows = conn.execute(
            """
            SELECT chunk_id, source, section, content, 1 - (embedding <=> %(query)s) AS similarity
            FROM policy_chunks
            ORDER BY embedding <=> %(query)s
            LIMIT %(k)s
            """,
            {"query": query_vector, "k": k},
        ).fetchall()
    return [PolicyHit(*row) for row in rows]


def search_products_semantic(question: str, k: int = 5, max_price: int | None = None) -> list[dict]:
    query_vector = embed_query(question)
    with get_connection() as conn:
        register_vector(conn)
        rows = conn.execute(
            """
            SELECT sku, name, sale_price, stock, 1 - (embedding <=> %(query)s) AS similarity
            FROM products
            WHERE %(max_price)s::INTEGER IS NULL OR sale_price <= %(max_price)s
            ORDER BY embedding <=> %(query)s
            LIMIT %(k)s
            """,
            {"query": query_vector, "k": k, "max_price": max_price},
        ).fetchall()
    columns = ["sku", "name", "sale_price", "stock", "similarity"]
    return [dict(zip(columns, row)) for row in rows]
