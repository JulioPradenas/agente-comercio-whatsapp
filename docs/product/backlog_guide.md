# Backlog en Jira

Archivo: [`backlog_jira.csv`](backlog_jira.csv). 8 épicas y 32 historias, todas con criterios de aceptación,
prioridad y puntos de historia.

| | Hecho | Por hacer |
|---|---|---|
| Épicas | 3 | 5 |
| Historias | 16 (74 puntos: lo construido en este repositorio) | 16 (77 puntos) |

## Cómo se priorizó

Las historias pendientes se priorizaron con **RICE** = Reach × Impact × Confidence ÷ Effort. El cálculo
completo está en la descripción de cada historia.

| Factor | Escala usada |
|---|---|
| Reach | Conversaciones al mes afectadas. **Supuesto:** 10.000 conversaciones mensuales; las derivaciones son ~20% (2.000) y las de venta ~40% (4.000) |
| Impact | 3 masivo · 2 alto · 1 medio · 0,5 bajo |
| Confidence | 100% medido · 80% con evidencia del proyecto · 50% hipótesis |
| Effort | Semanas-persona |

| RICE | Prioridad en Jira |
|---|---|
| ≥ 10.000 | Highest |
| 5.000 – 9.999 | High |
| 1.000 – 4.999 | Medium |
| < 1.000 | Low |

**Ranking de las pendientes:**

| RICE | Prioridad | Historia |
|---|---|---|
| 20.000 | Highest | Dashboard de KPIs en Looker Studio |
| 16.000 | Highest | Reducir la latencia del router |
| 8.000 | High | Migrar a Vertex AI con cuota pagada |
| 8.000 | High | Eventos de producción hacia BigQuery |
| 8.000 | High | Casos de evaluación escritos por Atención a Clientes |
| 8.000 | High | Calibrar el juez contra etiquetas humanas |
| 6.000 | High | Conectar VTEX real |
| 5.600 | High | Encuesta de satisfacción al cerrar la conversación |
| 2.400 | Medium | Mensaje de bienvenida |
| 2.000 | Medium | Botones y listas de WhatsApp |
| 1.600 | Medium | Aviso de cierre de caso |
| 1.067 | Medium | Integrar la bandeja de tickets con la herramienta del equipo |
| 1.000 | Medium | Acuerdo de servicio de primera respuesta humana |
| 960 | Low | Mensaje fuera de horario |
| 375 | Low | Responder varias preguntas en un mensaje |
| 333 | Low | Plantillas para mensajes salientes |

**Lectura del ranking:** primero lo que permite medir y cumplir la meta de latencia (dashboard, router);
después lo que prepara el piloto con clientes reales (Vertex AI, eventos de producción, calidad de la
evaluación, VTEX real). "Botones y listas" queda en Medium por su baja confianza (50%): el embudo indica
que ayudaría, pero el efecto no está medido. Es la primera candidata a subir si el piloto lo confirma.

Las historias hechas tienen prioridad Medium y puntos estimados de forma retroactiva, para mostrar la
velocidad real del proyecto.

## Importar en Jira

Los nombres de los menús pueden variar levemente según la versión de Jira Cloud.

1. Crea un proyecto **Scrum** (por ejemplo, clave `AGT`, nombre "Agente WhatsApp"). Jira Free alcanza.
2. Importa el CSV desde **Configuración (engranaje) → Sistema → Importación de sistemas externos → CSV**.
   En algunos proyectos también aparece en el menú `…` del backlog como **Importar incidencias**.
3. Elige el proyecto `AGT` y el archivo `backlog_jira.csv` (codificación UTF-8).
4. Asigna las columnas a los campos de Jira:

| Columna del CSV | Campo de Jira |
|---|---|
| Issue ID | Issue Id |
| Parent ID | Parent Id (vincula cada historia con su épica) |
| Issue Type | Issue Type |
| Summary | Summary |
| Description | Description |
| Status | Status (asigna `Done` → Listo y `To Do` → Por hacer) |
| Priority | Priority |
| Labels | Labels |
| Story Points | Story point estimate |

5. Revisa la vista previa y confirma. Comprueba que cada historia aparezca bajo su épica.

## Plan de sprints (2 semanas cada uno)

| Sprint | Objetivo | Historias | Puntos |
|---|---|---|---|
| 0 (cerrado) | MVP en producción con evaluación y observabilidad | Las 16 historias hechas | 74 |
| 1 | Medir el producto y cumplir la meta de latencia | Dashboard de KPIs · Reducir la latencia del router · Calibrar el juez · Casos de Atención a Clientes | 13 |
| 2 | Preparar el piloto con clientes | Migrar a Vertex AI · Eventos de producción hacia BigQuery · Encuesta de satisfacción · Mensaje de bienvenida | 17 |
| 3 | Integraciones reales | Conectar VTEX real · Acuerdo de servicio · Aviso de cierre de caso | 18 |

El resto (botones y listas, bandeja de tickets, mensajes fuera de horario, varias preguntas, plantillas)
se repriorizan con los datos del piloto.

Toma una captura del backlog y del tablero, y agrégala a `docs/product/` para el portafolio.
