-- Vistas de KPIs del agente (BigQuery, SQL estándar).
-- Cada KPI se define UNA vez aquí: el dashboard y cualquier reporte usan la misma definición.
-- Tablas base (cargadas desde analytics/data): conversations, turns.

-- Resumen general: los KPIs del cargo en una fila.
CREATE OR REPLACE VIEW `{dataset}.kpi_summary` AS
WITH conversation_base AS (
    SELECT
        conversation_id,
        resolved,
        handed_off,
        sales_conversation,
        converted,
        cart_total_clp,
        cost_usd
    FROM `{dataset}.conversations`
),
turn_latency AS (
    SELECT
        APPROX_QUANTILES(latency_s, 100)[OFFSET(50)] AS latency_p50_s,
        APPROX_QUANTILES(latency_s, 100)[OFFSET(90)] AS latency_p90_s
    FROM `{dataset}.turns`
)
SELECT
    COUNT(*) AS conversations,
    -- Contención: termina sin ejecutivo y sin respuesta de error.
    ROUND(AVG(CAST(resolved AS INT64)), 3) AS containment_rate,
    ROUND(AVG(CAST(handed_off AS INT64)), 3) AS handoff_rate,
    -- Conversión: solo sobre conversaciones de ventas (no se diluye con consultas de pedidos).
    ROUND(SAFE_DIVIDE(COUNTIF(converted), COUNTIF(sales_conversation)), 3) AS sales_conversion_rate,
    ROUND(AVG(IF(converted, cart_total_clp, NULL))) AS avg_ticket_clp,
    ROUND(AVG(cost_usd), 5) AS cost_per_conversation_usd,
    ANY_VALUE(turn_latency.latency_p50_s) AS latency_p50_s,
    ANY_VALUE(turn_latency.latency_p90_s) AS latency_p90_s
FROM conversation_base
CROSS JOIN turn_latency;

-- Serie diaria: para ver tendencias en el dashboard.
CREATE OR REPLACE VIEW `{dataset}.kpi_daily` AS
WITH daily AS (
    SELECT
        DATE(TIMESTAMP(started_at)) AS conversation_date,
        resolved,
        handed_off,
        sales_conversation,
        converted,
        cost_usd
    FROM `{dataset}.conversations`
)
SELECT
    conversation_date,
    COUNT(*) AS conversations,
    COUNTIF(resolved) AS resolved_conversations,
    COUNTIF(handed_off) AS handed_off_conversations,
    ROUND(AVG(CAST(resolved AS INT64)), 3) AS containment_rate,
    COUNTIF(converted) AS conversions,
    ROUND(SUM(cost_usd), 5) AS cost_usd
FROM daily
GROUP BY conversation_date;

-- Por intención de entrada: dónde se resuelve, dónde se deriva y cuánto cuesta cada tipo de consulta.
CREATE OR REPLACE VIEW `{dataset}.kpi_by_intent` AS
SELECT
    COALESCE(first_intent, 'sin_intencion') AS first_intent,
    COUNT(*) AS conversations,
    ROUND(AVG(CAST(resolved AS INT64)), 3) AS containment_rate,
    ROUND(AVG(CAST(handed_off AS INT64)), 3) AS handoff_rate,
    ROUND(AVG(cost_usd), 5) AS cost_per_conversation_usd,
    ROUND(AVG(avg_latency_s), 1) AS avg_latency_s
FROM `{dataset}.conversations`
GROUP BY first_intent;

-- Motivos de derivación: qué le llega al equipo humano.
CREATE OR REPLACE VIEW `{dataset}.kpi_handoff_reasons` AS
SELECT
    handoff_trigger,
    COUNT(*) AS conversations,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 3) AS share
FROM `{dataset}.conversations`
WHERE handed_off
GROUP BY handoff_trigger;

-- Embudo de ventas: en qué etapa se pierden las conversaciones de compra.
CREATE OR REPLACE VIEW `{dataset}.kpi_sales_funnel` AS
WITH sales_conversations AS (
    SELECT
        conversations.conversation_id,
        conversations.converted,
        LOGICAL_OR(turns.tools LIKE '%search_products%') AS searched,
        LOGICAL_OR(turns.tools LIKE '%add_to_cart%') AS added_to_cart
    FROM `{dataset}.conversations` AS conversations
    JOIN `{dataset}.turns` AS turns
        ON turns.conversation_id = conversations.conversation_id
    WHERE conversations.sales_conversation
    GROUP BY conversations.conversation_id, conversations.converted
),
funnel AS (
    SELECT 1 AS step_order, '1. Consulta de compra' AS step, COUNT(*) AS conversations FROM sales_conversations
    UNION ALL
    SELECT 2, '2. Recibió recomendaciones', COUNTIF(searched) FROM sales_conversations
    UNION ALL
    SELECT 3, '3. Agregó al carrito', COUNTIF(added_to_cart) FROM sales_conversations
    UNION ALL
    SELECT 4, '4. Recibió link de pago', COUNTIF(converted) FROM sales_conversations
)
SELECT
    step_order,
    step,
    conversations,
    ROUND(SAFE_DIVIDE(conversations, FIRST_VALUE(conversations) OVER (ORDER BY step_order)), 3) AS share_of_start
FROM funnel;

-- Eficiencia por intención (nivel turno): latencia, llamadas al LLM, tokens y costo.
CREATE OR REPLACE VIEW `{dataset}.kpi_efficiency_by_intent` AS
SELECT
    COALESCE(intent, 'guardrail') AS intent,
    COUNT(*) AS turns,
    APPROX_QUANTILES(latency_s, 100)[OFFSET(50)] AS latency_p50_s,
    APPROX_QUANTILES(latency_s, 100)[OFFSET(90)] AS latency_p90_s,
    ROUND(AVG(llm_calls), 2) AS avg_llm_calls,
    ROUND(AVG(input_tokens)) AS avg_input_tokens,
    ROUND(AVG(output_tokens)) AS avg_output_tokens,
    ROUND(AVG(cost_usd), 6) AS avg_cost_per_turn_usd
FROM `{dataset}.turns`
GROUP BY intent;

-- Calidad y seguridad: cómo termina cada conversación (una sola categoría por conversación).
CREATE OR REPLACE VIEW `{dataset}.kpi_outcomes` AS
WITH classified AS (
    SELECT
        CASE
            WHEN handed_off THEN 'Derivada a ejecutivo'
            WHEN guarded THEN 'Bloqueada por guardrail'
            WHEN fallback THEN 'Respuesta de error'
            WHEN converted THEN 'Venta (link de pago)'
            ELSE 'Resuelta por el bot'
        END AS outcome
    FROM `{dataset}.conversations`
)
SELECT
    outcome,
    COUNT(*) AS conversations,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 3) AS share
FROM classified
GROUP BY outcome;
