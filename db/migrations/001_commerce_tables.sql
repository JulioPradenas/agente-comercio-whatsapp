-- Tablas transaccionales del comercio.
-- Las restricciones (CHECK, FOREIGN KEY, UNIQUE) replican las reglas de data/validate.py
-- dentro de la base: un dato inválido se rechaza al insertarlo, no después.

CREATE TABLE IF NOT EXISTS products (
    sku          TEXT PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    product_type TEXT NOT NULL,
    category     TEXT NOT NULL,
    brand        TEXT NOT NULL,
    list_price   INTEGER NOT NULL CHECK (list_price > 0),
    sale_price   INTEGER NOT NULL CHECK (sale_price > 0 AND sale_price <= list_price),
    stock        INTEGER NOT NULL CHECK (stock >= 0),
    attributes   JSONB NOT NULL,
    description  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    full_name   TEXT NOT NULL,
    rut         TEXT NOT NULL UNIQUE,
    email       TEXT NOT NULL,
    phone       TEXT NOT NULL UNIQUE CHECK (phone ~ '^569[0-9]{8}$'),
    region      TEXT NOT NULL,
    city        TEXT NOT NULL,
    address     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id           TEXT PRIMARY KEY,
    customer_id        TEXT NOT NULL REFERENCES customers (customer_id),
    created_at         TIMESTAMPTZ NOT NULL,
    status             TEXT NOT NULL CHECK (
        status IN ('payment-pending', 'ready-for-handling', 'handling', 'invoiced', 'delivered', 'canceled')
    ),
    status_label       TEXT NOT NULL,
    items_total        INTEGER NOT NULL CHECK (items_total > 0),
    shipping_cost      INTEGER NOT NULL CHECK (shipping_cost >= 0),
    order_total        INTEGER NOT NULL,
    estimated_delivery DATE NOT NULL,
    delivered_at       TIMESTAMPTZ,
    shipping_address   TEXT NOT NULL,
    CHECK (order_total = items_total + shipping_cost),
    CHECK ((status = 'delivered') = (delivered_at IS NOT NULL))
);

-- El agente busca "los pedidos de este teléfono": sin este índice sería un scan de toda la tabla.
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);

CREATE TABLE IF NOT EXISTS order_items (
    order_id     TEXT NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    sku          TEXT NOT NULL REFERENCES products (sku),
    product_name TEXT NOT NULL,
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    unit_price   INTEGER NOT NULL CHECK (unit_price > 0),
    PRIMARY KEY (order_id, sku)
);

-- Supabase expone automáticamente las tablas del esquema public por una API REST.
-- Con RLS activado y sin políticas, esa API no puede leer nada; nuestra conexión
-- directa como usuario postgres no se ve afectada.
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
