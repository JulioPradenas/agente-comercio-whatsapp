# PRD: Agente de compra y postventa por WhatsApp

| | |
|---|---|
| **Producto** | Asistente de IA de HogarTec en WhatsApp |
| **Responsable** | Julio Pradenas · Product Lead de IA conversacional |
| **Estado** | MVP en producción (piloto con número de prueba) |
| **Última actualización** | 19 de noviembre de 2026 |
| **Áreas involucradas** | Producto, Tecnología, Atención a Clientes, Legal, Ciberseguridad, Datos |

> HogarTec es una tienda ficticia. Las cifras de "línea base" vienen de 30 conversaciones simuladas contra
> el agente real. Todo dato del negocio que no se midió en este proyecto está marcado como **supuesto**.

## 1. Resumen

Un asistente de IA en WhatsApp que atiende a los clientes de HogarTec las 24 horas: recomienda productos y
entrega el link de pago, informa el estado de los pedidos, gestiona devoluciones según la política y deriva
a un ejecutivo los casos que requieren a una persona. El objetivo es resolver sin intervención humana la
mayoría de las consultas repetitivas y convertir en ventas las consultas de compra que hoy se pierden por
falta de respuesta. El éxito se mide con la tasa de contención, protegida por métricas de calidad, latencia
y costo.

## 2. Problema y oportunidad

**Del lado del cliente:** quien escribe por WhatsApp espera respuesta en minutos, pero la atención humana
funciona en horario hábil. Saber dónde está un pedido o si se puede devolver un producto obliga a esperar
o a llamar, y una consulta de compra sin respuesta rápida termina en otra tienda.

**Del lado del negocio:** la mayoría de los contactos son preguntas repetitivas (estado de pedido, costo de
despacho, plazos de devolución) que consumen tiempo de ejecutivos, y las consultas de compra fuera de horario
no se atienden.

**Supuestos a validar:**

| Supuesto | Cómo se valida | Estado |
|---|---|---|
| Al menos 50% de los contactos por WhatsApp son de estado de pedido, despacho o devoluciones | Clasificar con el router una muestra de 500 conversaciones históricas anonimizadas | Por validar |
| Un contacto atendido por un ejecutivo cuesta al menos 50 veces más que uno atendido por el bot | Costo hora del equipo ÷ contactos por hora, comparado con US$0,0011 por conversación | Por validar |
| 30% de las consultas de compra llegan fuera de horario hábil | Distribución horaria de mensajes de los últimos 3 meses | Por validar |
| Los clientes aceptan comprar por un link enviado por el bot | Conversión del piloto ≥ 20% en conversaciones de venta | Por validar en el piloto |

## 3. Usuarios

| Usuario | Qué necesita | Cómo lo atiende el agente |
|---|---|---|
| Cliente que quiere comprar | Encontrar un producto según presupuesto y comprarlo rápido | Recomendaciones con filtros de precio y tipo, carrito y link de pago |
| Cliente con un pedido | Saber dónde está su pedido o devolverlo | Estado, fecha estimada calculada en días hábiles, devoluciones según política |
| Cliente con una duda | Despacho, garantía, medios de pago | Respuestas desde las políticas oficiales (RAG) |
| Ejecutivo de atención | Recibir solo los casos que requieren a una persona, con contexto | Ticket con motivo, resumen y transcripción; el bot se pausa |
| Responsable comercial | Saber cuánto vende el canal y dónde se pierden las ventas | Dashboard de conversión, ticket promedio y embudo de ventas |

## 4. Objetivos y no objetivos

**Objetivos del MVP:**
1. Resolver sin ejecutivo al menos el 70% de las conversaciones, sin bajar la fidelidad de las respuestas de 4,5 sobre 5.
2. Convertir al menos el 25% de las conversaciones de venta en un link de pago.
3. Mantener el costo por conversación bajo US$0,01 a precio de lista.

**No objetivos (fuera de alcance a propósito):**
- Cobrar dentro del chat: el pago siempre ocurre en el sitio, por link.
- Mensajes salientes de marketing o carrito abandonado: requieren consentimiento y plantillas aprobadas.
- Audios, imágenes y videos del cliente.
- Cancelar pedidos o cambiar direcciones automáticamente: se derivan a un ejecutivo.
- Canales distintos de WhatsApp (web, Instagram) en esta fase.

## 5. Métricas de éxito

La métrica principal es la **contención**: mide directamente cuánta atención absorbe el bot. Las de
protección evitan que se suba la contención a costa de respuestas peores, lentas o caras.

| Tipo | Métrica | Definición | Línea base (simulación) | Meta |
|---|---|---|---|---|
| Principal | Contención | Conversaciones sin ejecutivo y sin error ÷ total | 80% | ≥ 70% |
| Apoyo | Conversión de ventas | Conversaciones de venta con link de pago ÷ conversaciones de venta | 33% | ≥ 25% |
| Apoyo | Ticket promedio | Total del carrito en ventas del bot | $190.988 | Referencial: comparar con el ticket del sitio web |
| Protección | Latencia p90 | Percentil 90 del tiempo de respuesta | 18,1 s | ≤ 15 s |
| Protección | Fidelidad (juez) | Datos de la respuesta respaldados por herramientas (1–5) | 5,00 | ≥ 4,5 |
| Protección | Costo por conversación | Suma del costo de LLM a precio de lista | US$0,0011 | ≤ US$0,01 |
| Protección | Satisfacción (CSAT) | % de respuestas 4 o 5 a "¿Resolvimos tu consulta?" (1–5) al cerrar | Sin medición | ≥ 80% · se agrega en el piloto con clientes |

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
| Botones y listas de WhatsApp | Fase 2 | Mejoran la conversión al confirmar la compra con un toque; no bloquean el piloto |
| Mensajes salientes (carrito abandonado) | No incluido | Requiere plantillas aprobadas por Meta y consentimiento |

## 7. Requisitos funcionales

| ID | Requisito | Prioridad |
|---|---|---|
| RF-01 | El agente recomienda hasta 3 productos con stock, respetando el presupuesto indicado | Must |
| RF-02 | Agrega al carrito solo con confirmación explícita del cliente y entrega el link de pago | Must |
| RF-03 | Informa estado y fecha estimada de pedidos del cliente que escribe | Must |
| RF-04 | Crea devoluciones solo dentro de la política (10 días, producto entregado, sin excepción sanitaria) | Must |
| RF-05 | Responde políticas citando solo la información oficial | Must |
| RF-06 | Deriva a un ejecutivo según las reglas de la sección 10 y pausa el bot | Must |
| RF-07 | Envía un mensaje de bienvenida que explica qué puede hacer el asistente | Should |
| RF-08 | Informa el horario de atención cuando la derivación ocurre fuera de horario | Should |
| RF-09 | Confirma la compra y la elección de producto con botones y listas de WhatsApp | Could |
| RF-10 | Pide una calificación (CSAT) al cerrar la conversación | Should |
| RF-11 | Cancela pedidos no despachados sin intervención humana | Won't (esta fase) |

## 8. Requisitos no funcionales

| Área | Requisito | Estado actual |
|---|---|---|
| Latencia | p90 de respuesta ≤ 15 s | 18,1 s · no cumple; es la primera optimización |
| Disponibilidad | Si el proveedor de LLM falla, se usa un modelo de respaldo y, si todos fallan, se deriva | Implementado |
| Privacidad | Datos personales enmascarados antes del LLM, la base de datos y los tickets; teléfono anonimizado en trazas | Implementado |
| Seguridad | Webhook con firma HMAC; credenciales en variables de entorno; nunca se piden datos de pago | Implementado |
| Costo | Costo por conversación ≤ US$0,01 | US$0,0011 |
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

**Acuerdo de servicio con Atención a Clientes (propuesta para acordar):**
- Primera respuesta de un ejecutivo en **máximo 30 minutos** dentro del horario hábil (lunes a viernes, 9:00 a 18:00).
- Casos derivados fuera de horario: se atienden **antes de las 11:00 del siguiente día hábil**.
- Fuera de horario, el cliente recibe el número de caso y la hora estimada de respuesta.
- Amenazas legales y reclamos formales tienen prioridad en la bandeja.

## 11. Dependencias e integraciones

| Sistema | Uso | Riesgo |
|---|---|---|
| VTEX (hoy simulado) | Catálogo, stock, carrito, pedidos | El equipo de Plataforma es dueño de la integración real; se necesita un ambiente de pruebas de VTEX y credenciales de solo lectura para el piloto |
| WhatsApp Cloud API (Meta) | Canal | Verificación del negocio, calidad del número, costos por conversación |
| Gemini (AI Studio, compatible con Vertex AI) | LLM y embeddings | Cuotas, saturación (mitigado con modelo de respaldo) |
| Supabase (Postgres + pgvector) | Memoria, políticas, tickets | Plan gratuito con límites de conexión |
| Langfuse | Trazas y costo | — |
| BigQuery + Looker Studio | KPIs | Tablas del sandbox expiran a los 60 días |

## 12. Riesgos

| Riesgo | Impacto | Mitigación actual | Responsable |
|---|---|---|---|
| El agente informa un precio incorrecto | Reclamo, obligación de respetar el precio | Guardrail de salida: todo monto debe venir de una herramienta | Producto + Tecnología |
| Se filtran datos de otro cliente | Legal y reputacional | El teléfono no es parámetro del LLM; la API valida el dueño | Ciberseguridad |
| Prompt injection | Respuestas fuera de política | Detección en el router y reglas de negocio en la API | Ciberseguridad + Tecnología |
| Caída del proveedor de LLM | Sin atención | Modelo de respaldo y derivación automática | Tecnología |
| Latencia alta en horas punta | Abandono de la conversación | Medición p90 en Langfuse; optimización del router en el backlog | Tecnología |
| Saturación del equipo humano por derivaciones | Incumplimiento del acuerdo de servicio | Tasa de derivación monitoreada en el dashboard; límite de alerta en 30% | Atención a Clientes |

## 13. Cumplimiento y legal

> Estos puntos se validan con Legal y Compliance antes del piloto con clientes; no son asesoría legal.

- **Ley del Consumidor (Ley 19.496):** derecho a retracto de 10 días y garantía legal de 6 meses. Las políticas
  del bot los reflejan. Pendiente: que Legal apruebe los textos de `data/policies/` antes del piloto con clientes.
- **Protección de datos personales:** revisar con Legal la Ley 21.719, que moderniza el régimen de la Ley 19.628
  y entra en vigencia en diciembre de 2026: base de licitud del tratamiento, finalidad declarada y derechos del
  titular sobre sus conversaciones.
- **Políticas de WhatsApp Business:** el MVP solo responde mensajes iniciados por el cliente. Los mensajes
  salientes requerirán consentimiento (opt-in) registrado y una forma simple de darse de baja.
- **Retención de datos:** propuesta para validar con Legal: conversaciones y memoria del agente por 90 días;
  tickets de derivación por 12 meses; trazas de observabilidad por 30 días. Los datos de tarjetas nunca se
  almacenan porque se enmascaran antes de guardarse.

## 14. Plan de lanzamiento

| Fase | Alcance | Criterio para avanzar |
|---|---|---|
| Piloto interno | 2 semanas con 10 colaboradores de Atención a Clientes y Ventas usando el número de prueba | Evaluación en CI en verde, 0 incidentes de privacidad y aprobación de los textos por Legal |
| Piloto con clientes | 10% de los contactos entrantes por WhatsApp durante 4 semanas | Contención ≥ 70%, CSAT ≥ 80%, latencia p90 ≤ 15 s y acuerdo de servicio cumplido |
| Lanzamiento general | 100% de los contactos por WhatsApp | Métricas del piloto estables 2 semanas seguidas y equipo humano dimensionado para la tasa de derivación |

## 15. Preguntas abiertas

| Pregunta | Quién responde | Fecha |
|---|---|---|
| ¿Legal aprueba las políticas de retracto y garantía tal como las comunica el bot? | Legal | 4 de diciembre de 2026 |
| ¿Qué herramienta de atención recibirá los tickets (Zendesk, Freshdesk u otra)? | Atención a Clientes | 4 de diciembre de 2026 |
| ¿Hay un ambiente de pruebas de VTEX disponible para el piloto? | Plataforma | 11 de diciembre de 2026 |
| ¿Cuál es la base legal para guardar las conversaciones con fines de mejora del modelo? | Legal + Datos | 11 de diciembre de 2026 |
| ¿El presupuesto permite migrar a Vertex AI con cuota pagada para el lanzamiento general? | Producto + Finanzas | 18 de diciembre de 2026 |
