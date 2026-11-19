# PRD: Agente de compra y postventa por WhatsApp

| | |
|---|---|
| **Producto** | Asistente de IA de HogarTec en WhatsApp |
| **Responsable** | [COMPLETAR: tu nombre y rol] |
| **Estado** | MVP en producción (piloto con número de prueba) |
| **Última actualización** | [COMPLETAR: fecha] |
| **Áreas involucradas** | Producto, Tecnología, Atención a Clientes, Legal, Ciberseguridad, Datos |

> **Cómo completar este documento.** Lo marcado `[COMPLETAR]` son decisiones de producto: escríbelas
> con tu criterio y justifícalas en una línea. Lo demás ya está construido o medido en este repositorio;
> revísalo y ajústalo si no estás de acuerdo. Un PRD bueno es corto: cada sección responde una pregunta.

## 1. Resumen

> Guía: 3–4 líneas. Qué es, para quién, qué problema resuelve y cómo sabremos que funciona.

[COMPLETAR]

## 2. Problema y oportunidad

> Guía: describe el problema desde el cliente y desde el negocio. Usa supuestos explícitos si no tienes datos
> (ej: "supuesto: 40% de los contactos son de estado de pedido"). Un reclutador valora ver que separas datos de supuestos.

**Del lado del cliente:** [COMPLETAR: ej. tiempos de espera en atención, horarios limitados, tener que llamar para saber de un pedido]

**Del lado del negocio:** [COMPLETAR: ej. costo por contacto humano, ventas perdidas por no responder a tiempo]

**Supuestos a validar:**

| Supuesto | Cómo se valida | Estado |
|---|---|---|
| [COMPLETAR] | [COMPLETAR] | Por validar |

## 3. Usuarios

| Usuario | Qué necesita | Cómo lo atiende el agente |
|---|---|---|
| Cliente que quiere comprar | Encontrar un producto según presupuesto y comprarlo rápido | Recomendaciones con filtros de precio y tipo, carrito y link de pago |
| Cliente con un pedido | Saber dónde está su pedido o devolverlo | Estado, fecha estimada calculada en días hábiles, devoluciones según política |
| Cliente con una duda | Despacho, garantía, medios de pago | Respuestas desde las políticas oficiales (RAG) |
| Ejecutivo de atención | Recibir solo los casos que requieren a una persona, con contexto | Ticket con motivo, resumen y transcripción; el bot se pausa |
| [COMPLETAR: ¿falta alguno? ej. responsable comercial que mira conversión] | | |

## 4. Objetivos y no objetivos

**Objetivos del MVP:** [COMPLETAR: 2–3 objetivos medibles, ej. "absorber el X% de las consultas de pedidos sin ejecutivo"]

**No objetivos (fuera de alcance a propósito):**
- [COMPLETAR: ej. pagos dentro del chat, mensajes proactivos de marketing, audios]

## 5. Métricas de éxito

> Guía: separa la métrica principal (north star), las de apoyo y las de protección (las que no pueden
> empeorar). La línea base viene de la simulación; la meta es tu decisión.

| Tipo | Métrica | Definición | Línea base (simulación) | Meta |
|---|---|---|---|---|
| Principal | [COMPLETAR: elige una, ej. contención] | Conversaciones sin ejecutivo y sin error ÷ total | 80% | [COMPLETAR] |
| Apoyo | Conversión de ventas | Conversaciones de venta con link de pago ÷ conversaciones de venta | 33% | [COMPLETAR] |
| Apoyo | Ticket promedio | Total del carrito en ventas del bot | $190.988 | [COMPLETAR] |
| Protección | Latencia p90 | Percentil 90 del tiempo de respuesta | 18,1 s | [COMPLETAR] |
| Protección | Fidelidad (juez) | Datos de la respuesta respaldados por herramientas (1–5) | 5,00 | [COMPLETAR] |
| Protección | Costo por conversación | Suma del costo de LLM a precio de lista | US$0,0011 | [COMPLETAR] |
| [COMPLETAR: ¿satisfacción del cliente (CSAT)? ¿cómo se mediría?] | | | — | |

## 6. Alcance del MVP

| Capacidad | Estado | Notas |
|---|---|---|
| Búsqueda y recomendación de productos | Construido | Búsqueda híbrida: filtros de precio y tipo + similitud semántica |
| Carrito y link de pago | Construido | Checkout tipo VTEX; el pago ocurre en el sitio, nunca en el chat |
| Estado de pedidos | Construido | Solo pedidos del teléfono que escribe |
| Devoluciones por retracto | Construido | Reglas de la política validadas en la API |
| Preguntas de políticas | Construido | RAG sobre despacho, devoluciones, garantía y pagos |
| Derivación a ejecutivo | Construido | Reglas, política y fallas del sistema; ticket con resumen |
| Guardrails | Construido | Datos personales, tarjetas, injection, fuera de tema, precios respaldados |
| Cancelación de pedidos | Parcial | Se explica la política y se deriva; no hay cancelación automática |
| Botones y listas de WhatsApp | No incluido | [COMPLETAR: ¿entra al MVP o a la fase 2?] |
| Mensajes salientes (carrito abandonado) | No incluido | Requiere plantillas aprobadas por Meta y consentimiento |

## 7. Requisitos funcionales

> Guía: prioriza con MoSCoW (Must / Should / Could / Won't). La prioridad es tu decisión.

| ID | Requisito | Prioridad |
|---|---|---|
| RF-01 | El agente recomienda hasta 3 productos con stock, respetando el presupuesto indicado | [COMPLETAR] |
| RF-02 | Agrega al carrito solo con confirmación explícita del cliente y entrega el link de pago | [COMPLETAR] |
| RF-03 | Informa estado y fecha estimada de pedidos del cliente que escribe | [COMPLETAR] |
| RF-04 | Crea devoluciones solo dentro de la política (10 días, producto entregado, sin excepción sanitaria) | [COMPLETAR] |
| RF-05 | Responde políticas citando solo la información oficial | [COMPLETAR] |
| RF-06 | Deriva a un ejecutivo según las reglas de la sección 10 y pausa el bot | [COMPLETAR] |
| RF-07 | [COMPLETAR] | |

## 8. Requisitos no funcionales

| Área | Requisito | Estado actual |
|---|---|---|
| Latencia | p90 de respuesta ≤ [COMPLETAR] s | 18,1 s |
| Disponibilidad | Si el proveedor de LLM falla, se usa un modelo de respaldo y, si todos fallan, se deriva | Implementado |
| Privacidad | Datos personales enmascarados antes del LLM, la base de datos y los tickets; teléfono anonimizado en trazas | Implementado |
| Seguridad | Webhook con firma HMAC; credenciales en variables de entorno; nunca se piden datos de pago | Implementado |
| Costo | Costo por conversación ≤ [COMPLETAR] | US$0,0011 |
| Calidad | Evaluación automática en cada cambio con umbrales que bloquean la integración | Implementado |

## 9. Experiencia conversacional

Ver [Diseño conversacional](conversation_design.md): tono, flujos, mensajes del sistema y casos borde.

## 10. Derivación a atención humana

| Disparador | Ejemplo | Implementado |
|---|---|---|
| El cliente pide una persona | "quiero hablar con un ejecutivo" | Sí |
| Amenaza legal o reclamo formal | "voy al SERNAC" | Sí |
| Frustración alta | Insultos, mayúsculas | Sí |
| Dos fallos seguidos del bot | — | Sí |
| Política: garantía, pedido no recibido, atraso > 2 días hábiles, cambio de dirección en preparación | "mi lavadora no enciende" | Sí |
| Falla del proveedor de LLM | — | Sí |

**Acuerdo de servicio con Atención a Clientes:** [COMPLETAR: tiempo máximo de primera respuesta del ejecutivo, horario de atención, qué ve el cliente fuera de horario]

## 11. Dependencias e integraciones

| Sistema | Uso | Riesgo |
|---|---|---|
| VTEX (hoy simulado) | Catálogo, stock, carrito, pedidos | [COMPLETAR: ¿quién es el dueño de la integración real?] |
| WhatsApp Cloud API (Meta) | Canal | Verificación del negocio, calidad del número, costos por conversación |
| Gemini (AI Studio, compatible con Vertex AI) | LLM y embeddings | Cuotas, saturación (mitigado con modelo de respaldo) |
| Supabase (Postgres + pgvector) | Memoria, políticas, tickets | Plan gratuito con límites de conexión |
| Langfuse | Trazas y costo | — |
| BigQuery + Looker Studio | KPIs | Tablas del sandbox expiran a los 60 días |

## 12. Riesgos

| Riesgo | Impacto | Mitigación actual | Responsable |
|---|---|---|---|
| El agente informa un precio incorrecto | Reclamo, obligación de respetar el precio | Guardrail de salida: todo monto debe venir de una herramienta | [COMPLETAR] |
| Se filtran datos de otro cliente | Legal y reputacional | El teléfono no es parámetro del LLM; la API valida el dueño | [COMPLETAR] |
| Prompt injection | Respuestas fuera de política | Detección en el router y reglas de negocio en la API | [COMPLETAR] |
| Caída del proveedor de LLM | Sin atención | Modelo de respaldo y derivación automática | [COMPLETAR] |
| [COMPLETAR] | | | |

## 13. Cumplimiento y legal

> Guía: valida cada punto con Legal y Compliance. Estas son preguntas, no respuestas legales.

- **Ley del Consumidor (Ley 19.496):** derecho a retracto de 10 días y garantía legal de 6 meses. Las políticas
  del bot los reflejan. [COMPLETAR: ¿Legal aprobó los textos?]
- **Protección de datos personales:** [COMPLETAR: revisar con Legal la ley vigente de protección de datos
  y qué exige sobre consentimiento, finalidad y retención de las conversaciones]
- **Políticas de WhatsApp Business:** consentimiento (opt-in) para mensajes salientes y opción de darse de baja.
  [COMPLETAR]
- **Retención de datos:** [COMPLETAR: cuánto tiempo se guardan conversaciones, checkpoints y tickets]

## 14. Plan de lanzamiento

| Fase | Alcance | Criterio para avanzar |
|---|---|---|
| Piloto interno | [COMPLETAR] | [COMPLETAR] |
| Piloto con clientes | [COMPLETAR: ej. % del tráfico o un segmento] | [COMPLETAR] |
| Lanzamiento general | [COMPLETAR] | [COMPLETAR] |

## 15. Preguntas abiertas

| Pregunta | Quién responde | Fecha |
|---|---|---|
| [COMPLETAR] | | |
