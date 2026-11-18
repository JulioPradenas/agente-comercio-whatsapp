-- Búsqueda semántica: políticas (RAG) y productos.
-- 768 dimensiones: gemini-embedding-001 genera 3072 por defecto, pero permite recortar
-- (Matryoshka). 768 ocupa 4 veces menos espacio con una pérdida de calidad pequeña,
-- y el índice HNSW de pgvector admite como máximo 2000 dimensiones.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policy_chunks (
    chunk_id     TEXT PRIMARY KEY,               -- ej: 'devoluciones#derecho-a-retracto-en-compras-online'
    source       TEXT NOT NULL,                  -- nombre de la política, para citar la fuente
    section      TEXT NOT NULL,
    content      TEXT NOT NULL,
    content_hash TEXT NOT NULL,                  -- si el texto no cambió, no se vuelve a generar el embedding
    embedding    vector(768) NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE products ADD COLUMN IF NOT EXISTS embedding vector(768);
ALTER TABLE products ADD COLUMN IF NOT EXISTS embedding_hash TEXT;

-- HNSW: índice de vecinos aproximados. Con 22 chunks Postgres igual recorre la tabla completa,
-- pero con miles de documentos es lo que mantiene la búsqueda en milisegundos.
-- vector_cosine_ops: distancia coseno, la que corresponde al operador <=>.
CREATE INDEX IF NOT EXISTS idx_policy_chunks_embedding ON policy_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_products_embedding ON products USING hnsw (embedding vector_cosine_ops);

ALTER TABLE policy_chunks ENABLE ROW LEVEL SECURITY;
