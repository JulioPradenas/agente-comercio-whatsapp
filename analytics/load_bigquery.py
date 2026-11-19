"""Carga las conversaciones simuladas en BigQuery y crea las vistas de KPIs.

Usa la CLI `bq` (autenticada con gcloud). Proyecto sin facturación = BigQuery Sandbox: gratis, sin tarjeta;
permite cargas por lote (load jobs) y vistas, pero no streaming ni DML, y las tablas expiran a los 60 días.

Uso: uv run python -m analytics.load_bigquery
"""

import subprocess
from pathlib import Path

PROJECT = "torre-control-portafolio"
DATASET = f"{PROJECT}:hogartec_analytics"
DATASET_SQL = f"{PROJECT}.hogartec_analytics"
ANALYTICS_DIR = Path(__file__).parent

# Esquemas explícitos: el autodetect de BigQuery a veces infiere mal (ej. un booleano como STRING).
SCHEMAS = {
    "conversations": (
        "conversation_id:STRING,persona:STRING,customer:STRING,started_at:TIMESTAMP,first_intent:STRING,"
        "n_turns:INT64,handed_off:BOOL,handoff_trigger:STRING,guarded:BOOL,fallback:BOOL,resolved:BOOL,"
        "sales_conversation:BOOL,converted:BOOL,cart_total_clp:FLOAT64,llm_calls:INT64,input_tokens:INT64,"
        "output_tokens:INT64,cost_usd:FLOAT64,avg_latency_s:FLOAT64"
    ),
    "turns": (
        "conversation_id:STRING,turn:INT64,intent:STRING,latency_s:FLOAT64,llm_calls:INT64,input_tokens:INT64,"
        "output_tokens:INT64,cost_usd:FLOAT64,tools:STRING,guarded:BOOL,fallback:BOOL"
    ),
}


def bq(*args: str) -> str:
    result = subprocess.run(["bq", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"bq {' '.join(args[:2])} falló: {result.stderr or result.stdout}")
    return result.stdout


if __name__ == "__main__":
    existing = bq("ls", f"--project_id={PROJECT}")
    if "hogartec_analytics" not in existing:
        bq("mk", "--dataset", "--location=US", "--description=KPIs del agente HogarTec (conversaciones simuladas)", DATASET)
        print(f"Dataset creado: {DATASET_SQL}")

    for table, schema in SCHEMAS.items():
        # --replace: recargar es idempotente (no duplica filas si se corre de nuevo).
        bq("load", "--replace", "--source_format=CSV", "--skip_leading_rows=1",
           f"{DATASET}.{table}", str(ANALYTICS_DIR / "data" / f"{table}.csv"), schema)
        print(f"Tabla cargada: {table}")

    sql = (ANALYTICS_DIR / "sql" / "kpi_views.sql").read_text().replace("{dataset}", DATASET_SQL)
    # Sin las líneas de comentario: `bq` toma un argumento que empieza con "--" como si fuera un flag.
    sql = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    for statement in [s.strip() for s in sql.split(";") if "CREATE" in s]:
        bq("query", "--use_legacy_sql=false", f"--project_id={PROJECT}", statement)
        print("Vista creada:", statement.split("`")[1].split(".")[-1])

    print("\nKPIs:")
    print(bq("query", "--use_legacy_sql=false", f"--project_id={PROJECT}", "--format=pretty",
             f"SELECT * FROM `{DATASET_SQL}.kpi_summary`"))
