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

## API de comercio (VTEX-like)

```bash
uv run fastapi dev commerce_api/main.py --port 8001   # docs en http://localhost:8001/docs
uv run pytest
```

| Endpoint | Equivalente VTEX | Acceso |
|---|---|---|
| `GET /api/catalog_system/pub/products/search?ft=&fq=P[min TO max]&_from=&_to=` | Catalog API (legacy search) | Público |
| `GET /api/logistics/pvt/inventory/skus/{skuId}` | Logistics API | `X-VTEX-API-AppKey` + `X-VTEX-API-AppToken` |
