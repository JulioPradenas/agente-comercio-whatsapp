"""Aplica en orden las migraciones de db/migrations que aún no se han aplicado.

Uso: uv run python -m db.migrate
"""

from pathlib import Path

from db.connection import get_connection

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def migrate() -> None:
    with get_connection() as conn:
        # Tabla de control: registra qué archivos ya se ejecutaron para no repetirlos.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute("ALTER TABLE schema_migrations ENABLE ROW LEVEL SECURITY")
        applied = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                print(f"  ya aplicada: {path.name}")
                continue
            # Cada migración en su propia transacción: si falla, no queda a medias.
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            print(f"  aplicada:    {path.name}")


if __name__ == "__main__":
    migrate()
