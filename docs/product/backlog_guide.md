# Backlog en Jira

Archivo: [`backlog_jira.csv`](backlog_jira.csv). 8 épicas y 29 historias:

| | Hecho | Por hacer |
|---|---|---|
| Épicas | 4 | 4 |
| Historias | 16 (lo construido en este repositorio) | 13 (próximos pasos) |

Cada historia tiene criterios de aceptación en la descripción. Las 13 pendientes empiezan con `[COMPLETAR]`:
el criterio propuesto es un punto de partida, no una decisión.

## 1. Completa antes de importar

Abre el CSV en Google Sheets o Excel y completa dos columnas. Son decisiones tuyas:

**Priority** (`Highest`, `High`, `Medium`, `Low`). Sugerencia: prioriza las 13 pendientes con RICE y
anota el puntaje en la descripción, para poder defender el orden en una entrevista:

| Factor | Pregunta | Escala |
|---|---|---|
| Reach (alcance) | ¿Cuántas conversaciones al mes afecta? | Número estimado |
| Impact (impacto) | ¿Cuánto mueve la métrica principal? | 3 masivo · 2 alto · 1 medio · 0,5 bajo |
| Confidence (confianza) | ¿Qué tan seguro estás de alcance e impacto? | 100% · 80% · 50% |
| Effort (esfuerzo) | ¿Cuántas semanas-persona? | Número |

RICE = Reach × Impact × Confidence ÷ Effort.

**Story Points** (1, 2, 3, 5, 8, 13). Estima en relación con una historia de referencia que ya conoces,
por ejemplo: "Mensaje fuera de horario" = 2 puntos. Las historias ya hechas pueden quedar sin puntos o
con una estimación retroactiva.

Revisa también los criterios de aceptación con `[COMPLETAR]`: reemplaza el texto entre corchetes por tu
criterio y borra la marca.

## 2. Importa en Jira

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

## 3. Organiza los sprints

- **Sprint 0 (cerrado):** las 16 historias hechas. Muestra la velocidad real del proyecto.
- **Sprint 1:** las historias pendientes de mayor puntaje RICE que quepan en 2 semanas.
- Agrega un **objetivo de sprint** de una línea, por ejemplo: "Bajar la latencia p90 a la meta sin perder exactitud del router".

Toma una captura del backlog y del tablero, y agrégala a `docs/product/` para el portafolio.
