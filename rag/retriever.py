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


def search_products_semantic(
    question: str,
    k: int = 5,
    product_type: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    in_stock_only: bool = False,
) -> list[dict]:
    """Búsqueda híbrida: los filtros estructurados van en el WHERE y el embedding solo ordena."""
    query_vector = embed_query(question)
    with get_connection() as conn:
        register_vector(conn)
        rows = conn.execute(
            """
            SELECT sku, name, product_type, brand, list_price, sale_price, stock, attributes,
                   1 - (embedding <=> %(query)s) AS similarity
            FROM products
            WHERE (%(product_type)s::TEXT IS NULL OR product_type = %(product_type)s)
              AND (%(min_price)s::INTEGER IS NULL OR sale_price >= %(min_price)s)
              AND (%(max_price)s::INTEGER IS NULL OR sale_price <= %(max_price)s)
              AND (NOT %(in_stock_only)s OR stock > 0)
            ORDER BY embedding <=> %(query)s
            LIMIT %(k)s
            """,
            {
                "query": query_vector,
                "k": k,
                "product_type": product_type,
                "min_price": min_price,
                "max_price": max_price,
                "in_stock_only": in_stock_only,
            },
        ).fetchall()
    columns = ["sku", "name", "product_type", "brand", "list_price", "sale_price", "stock", "attributes", "similarity"]
    return [dict(zip(columns, row)) for row in rows]
