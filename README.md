# Agente de compra y postventa por WhatsApp

Agente conversacional para una tienda online de electro y hogar: busca productos, genera el link de compra,
informa el estado de pedidos, gestiona devoluciones y deriva a un humano cuando corresponde.

> En construcción. Avance actual: datos sintéticos del comercio.

## Stack previsto

| Capa | Tecnología |
|---|---|
| LLM | Gemini (Google Gen AI SDK, compatible con Vertex AI) |
| Orquestación | LangGraph (router + subagentes + derivación humana) |
| RAG | Postgres + pgvector (Supabase) |
| Canal | WhatsApp Cloud API |
| Backend | FastAPI en Cloud Run |
| Comercio | API simulada con la forma de los endpoints de VTEX |
| Calidad | Golden set + LLM-as-judge en CI, guardrails de entrada/salida |
| Analítica | BigQuery + Looker Studio (resolución, conversión, ticket promedio, costo por conversación) |

## Datos

Todos los datos son sintéticos y reproducibles (semilla fija). No hay datos personales reales.

| Tabla | Filas | Descripción |
|---|---|---|
| `products` | 300 | Catálogo con reglas por tipo de producto, descuentos y quiebres de stock |
| `customers` | 200 | Clientes con RUT y celular en formato WhatsApp (`569XXXXXXXX`) |
| `orders` | 1.000 | Pedidos con estados del OMS de VTEX según antigüedad |
| `order_items` | 1.391 | Ítems con el precio del momento de la compra |

```bash
uv sync
uv run python data/generate_catalog.py
uv run python data/generate_orders.py
uv run python data/validate.py
```

### Base de datos (Supabase / Postgres)

```bash
cp .env.example .env                      # completar DATABASE_URL y GEMINI_API_KEY
uv run python scripts/check_connections.py
uv run python -m db.migrate                # aplica db/migrations/*.sql pendientes
uv run python -m db.load_data              # carga los CSV con COPY (reemplaza el contenido)
```

Las restricciones del esquema (CHECK, llaves foráneas, UNIQUE) replican las reglas de `data/validate.py`
y RLS está activo en todas las tablas para que la API REST pública de Supabase no exponga datos.

### RAG (pgvector + embeddings de Gemini)

```bash
uv run python -m rag.indexer            # chunking + embeddings; solo procesa lo que cambió
uv run python -m evals.retrieval_eval   # hit@1, hit@4 y MRR sobre preguntas reales
```

Políticas divididas por sección (22 chunks) y descripciones de productos, con `gemini-embedding-001`
a 768 dimensiones e índice HNSW. Evaluación inicial de recuperación (16 preguntas):
hit@1 = 0,88 · hit@4 = 1,00 · MRR = 0,93.

## API de comercio (VTEX-like)

```bash
uv run fastapi dev commerce_api/main.py --port 8001   # docs en http://localhost:8001/docs
uv run pytest
```

| Endpoint | Equivalente VTEX | Acceso |
|---|---|---|
| `GET /api/catalog_system/pub/products/search?ft=&fq=P[min TO max]&_from=&_to=` | Catalog API (legacy search) | Público |
| `GET /api/logistics/pvt/inventory/skus/{skuId}` | Logistics API | `X-VTEX-API-AppKey` + `X-VTEX-API-AppToken` |
| `POST /api/checkout/pub/orderForm` | Checkout API (crear carrito) | Público |
| `GET /api/checkout/pub/orderForm/{orderFormId}` | Checkout API | Público |
| `POST /api/checkout/pub/orderForm/{orderFormId}/items` | Checkout API (agregar ítems) | Público |
| `GET /api/oms/pvt/orders/{orderId}` | OMS API | Credenciales |
| `GET /api/oms/pvt/orders?q={teléfono\|email\|RUT}` | OMS API (listar) | Credenciales |
| `POST /api/returns` | Propio (VTEX no lo trae nativo) | Credenciales |

Montos de Checkout y OMS en centavos, como VTEX. Las reglas de devolución de `data/policies/devoluciones.md`
se validan en la API y responden con códigos estables (`RETURN_WINDOW_EXPIRED`, `ORDER_NOT_OWNED`, etc.).

Colección Postman con tests: [`postman/hogartec_commerce_api.postman_collection.json`](postman/hogartec_commerce_api.postman_collection.json).
