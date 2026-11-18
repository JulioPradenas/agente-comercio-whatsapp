# Agente de compra y postventa por WhatsApp

Agente conversacional para una tienda online de electro y hogar: busca productos, genera el link de compra,
informa el estado de pedidos, gestiona devoluciones y deriva a un humano cuando corresponde.

> En producción en Render: el agente responde por WhatsApp (número de prueba de Meta).
> Pendiente: guardrails, evaluación completa en CI y dashboard de KPIs.

## Stack

| Capa | Tecnología |
|---|---|
| LLM | Gemini (Google Gen AI SDK, compatible con Vertex AI) |
| Orquestación | LangGraph (router + subagentes + derivación humana) |
| RAG | Postgres + pgvector (Supabase) |
| Canal | WhatsApp Cloud API |
| Backend | FastAPI en Render (Docker; mismo contenedor desplegable en Cloud Run) |
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

## Agente (LangGraph + Gemini)

```bash
uv run fastapi dev commerce_api/main.py --port 8001   # en otra terminal
uv run python -m agent.cli                # conversación de ejemplo
uv run python -m agent.cli --interactive  # conversar
```

Un router clasifica la intención con salida estructurada y deriva a un subagente con su propio prompt
y solo sus herramientas ([diagrama](docs/agent_graph.md)):

| Subagente | Herramientas |
|---|---|
| Ventas | `search_products`, `check_stock`, `add_to_cart`, `search_policies` |
| Postventa | `list_my_orders`, `get_order_status`, `request_return`, `search_policies` |
| FAQ | `search_policies` |

El teléfono del cliente viene de la sesión y nunca es un parámetro que el LLM pueda elegir.
Modelo principal y de respaldo configurables (`CHAT_MODEL`, `FALLBACK_CHAT_MODEL`), con timeout.

### Guardrails de entrada

| Riesgo | Control | Dónde |
|---|---|---|
| Datos personales en el LLM, Postgres y tickets | RUT, tarjeta, email y celular se enmascaran con regex antes de entrar al estado | `agent/guardrails.py` |
| Cliente envía su tarjeta por chat | Respuesta fija de seguridad, sin llamar al LLM | Nodo `guarded_reply` |
| Prompt injection / fuera de tema | El router extrae la señal en su misma llamada; la respuesta es fija | `guard_reason()` |
| Consultar pedidos de otra persona | El teléfono nunca es parámetro del LLM; la API valida dueño | Tools y API |

```bash
uv run python -m evals.router_eval adversarial_set   # 16/16: ataques, fuera de tema y falsos positivos
```

### Guardrails de salida

Antes de enviar una respuesta, `agent/output_guard.py` verifica:
- **Precios respaldados:** todo monto en pesos debe aparecer en un resultado de herramienta o en un mensaje
  del cliente (incluye "700 lucas", "500 mil"). Si no, el subagente recibe una corrección y reintenta una vez;
  si vuelve a fallar se envía una respuesta segura sin montos y cuenta como fallo.
- **Nunca pedir datos de pago** (tarjeta, CVV, clave), salvo en advertencias ("nunca te pediremos...").

### Derivación a atención humana

| Disparador | Quién decide | Ejemplo |
|---|---|---|
| Pide una persona, amenaza legal, frustración alta, 2 fallos seguidos | Reglas en código (`handoff_reason`) sobre señales que extrae el router | "páseme con un ejecutivo", "voy al SERNAC" |
| Lo indica la política | Subagente con la tool `escalate_to_human` | Producto con falla, pedido entregado que no llegó |
| Proveedor LLM caído | Sistema | Todos los modelos fallan |

Cada derivación crea un ticket en `handoff_tickets` con motivo, resumen y transcripción, y el bot queda
en pausa para ese cliente hasta que el ejecutivo cierra el caso.

```bash
uv run python -m evals.router_eval   # exactitud del router sobre evals/golden_set.jsonl (30 casos)
```

## Despliegue (Render, plan gratuito)

Un solo servicio Docker (`server.py`) con el webhook y la API de comercio montada en `/commerce`.
La memoria del agente vive en Postgres (`PostgresSaver`), así que sobrevive a que Render suspenda la instancia.

```bash
uv run python -m deploy.render_env   # genera .env.render (gitignored) para pegar en Render > Environment
```

| Ajuste en Render | Valor |
|---|---|
| Runtime | Docker |
| Instance type | Free (se suspende tras ~15 min sin tráfico; el primer mensaje tarda ~1 min) |
| Health check | `/health` |
| Callback URL en Meta | `https://<servicio>.onrender.com/webhook` |

Las credenciales de la API de comercio se generan aleatorias en cada despliegue: en producción `/commerce` es público
y las credenciales de desarrollo están en este repositorio.

## Canal WhatsApp (Cloud API)

```bash
uv run uvicorn channels.whatsapp_webhook:app --port 8000
```

- `GET /webhook`: verificación de Meta (`hub.verify_token` → `hub.challenge`).
- `POST /webhook`: valida la firma `X-Hub-Signature-256` (HMAC con el App Secret), responde 200 de inmediato
  y procesa en segundo plano; deduplica por `message.id` y procesa en orden los mensajes de un mismo cliente.
- Si un ejecutivo tiene el caso, el bot no responde. Audios e imágenes reciben un aviso de "solo texto".
- Logs propios sin secretos (el access log de uvicorn se desactiva con `--no-access-log` porque escribe la URL completa).

Desarrollo local con túnel:

```bash
uv run uvicorn channels.whatsapp_webhook:app --port 8000 --no-access-log
cloudflared tunnel --url http://localhost:8000   # Callback URL en Meta: <url>/webhook
```

Configuración en Meta que suele faltar:
1. En el formulario del webhook, el **Verify token** es `WHATSAPP_VERIFY_TOKEN`, no el access token.
2. Suscribir el campo `messages` del webhook.
3. Suscribir la cuenta de WhatsApp Business a la app (sin esto Meta verifica el webhook pero no envía mensajes):
   `POST https://graph.facebook.com/v25.0/{WABA_ID}/subscribed_apps` con el access token.

Token permanente (System User en Meta Business Settings), en este orden:
1. Crear el System User y asignarle **todos** los activos antes de generar el token: la app, la
   **WhatsApp account** y también la **Messaging account** (Messaging accounts > Linked accounts).
   Sin la Messaging account, el token falla con `(#10) Viewer cannot access the provided Paid Message Account`.
2. Generar el token: expiración *Never*, permisos `whatsapp_business_messaging` y `whatsapp_business_management`.
3. Verificar antes de usarlo: `GET /debug_token` (tipo `SYSTEM_USER`, `expires_at = 0`) y un envío de prueba.

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
