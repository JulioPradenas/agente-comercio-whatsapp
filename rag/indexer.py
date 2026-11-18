"""Genera y guarda embeddings de políticas y productos. Solo procesa lo que cambió.

Uso: uv run python -m rag.indexer
"""

import hashlib

from pgvector.psycopg import register_vector

from db.connection import get_connection
from rag.chunking import load_policy_chunks
from rag.embeddings import embed_documents


def index_policies(conn) -> None:
    chunks = load_policy_chunks()
    stored = dict(conn.execute("SELECT chunk_id, content_hash FROM policy_chunks").fetchall())
    pending = [chunk for chunk in chunks if stored.get(chunk.chunk_id) != chunk.content_hash]

    if pending:
        vectors = embed_documents([chunk.content for chunk in pending])
        with conn.transaction():
            for chunk, vector in zip(pending, vectors):
                conn.execute(
                    """
                    INSERT INTO policy_chunks (chunk_id, source, section, content, content_hash, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        source = EXCLUDED.source,
                        section = EXCLUDED.section,
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        embedding = EXCLUDED.embedding,
                        updated_at = now()
                    """,
                    (chunk.chunk_id, chunk.source, chunk.section, chunk.content, chunk.content_hash, vector),
                )

    # Secciones que ya no existen en los .md se borran: si no, el agente citaría políticas eliminadas.
    current_ids = [chunk.chunk_id for chunk in chunks]
    deleted = conn.execute("DELETE FROM policy_chunks WHERE chunk_id <> ALL(%s)", (current_ids,)).rowcount
    print(f"  políticas: {len(chunks)} chunks, {len(pending)} con embedding nuevo, {deleted} eliminados")


def index_products(conn) -> None:
    products = conn.execute("SELECT sku, description, embedding_hash FROM products").fetchall()
    pending = [
        (sku, description, hashlib.sha256(description.encode()).hexdigest())
        for sku, description, stored_hash in products
        if stored_hash != hashlib.sha256(description.encode()).hexdigest()
    ]

    if pending:
        vectors = embed_documents([description for _, description, _ in pending])
        with conn.transaction():
            for (sku, _, content_hash), vector in zip(pending, vectors):
                conn.execute(
                    "UPDATE products SET embedding = %s, embedding_hash = %s WHERE sku = %s",
                    (vector, content_hash, sku),
                )
    print(f"  productos: {len(products)} en total, {len(pending)} con embedding nuevo")


if __name__ == "__main__":
    with get_connection() as conn:
        register_vector(conn)  # enseña a psycopg a enviar arrays de numpy como tipo vector
        index_policies(conn)
        index_products(conn)
