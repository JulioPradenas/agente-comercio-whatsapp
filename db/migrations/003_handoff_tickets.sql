-- Derivaciones a atención humana.
-- El ejecutivo recibe el motivo, un resumen y la transcripción: el cliente no debe repetir todo.

CREATE TABLE IF NOT EXISTS handoff_tickets (
    ticket_id      TEXT PRIMARY KEY,
    customer_phone TEXT NOT NULL,
    trigger        TEXT NOT NULL CHECK (trigger IN ('router_rule', 'agent_policy', 'system_failure')),
    reason         TEXT NOT NULL,
    summary        TEXT NOT NULL,
    transcript     JSONB NOT NULL,
    status         TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at      TIMESTAMPTZ
);

-- La bandeja del ejecutivo consulta los tickets abiertos, del más antiguo al más nuevo.
CREATE INDEX IF NOT EXISTS idx_handoff_tickets_open ON handoff_tickets (created_at) WHERE status = 'open';

ALTER TABLE handoff_tickets ENABLE ROW LEVEL SECURITY;
