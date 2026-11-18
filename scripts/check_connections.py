"""Verifica que las credenciales del .env funcionan, sin imprimir ningún secreto.

Uso: uv run python scripts/check_connections.py
"""

import psycopg
from google import genai
from pydantic_settings import BaseSettings, SettingsConfigDict


class Credentials(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_api_key: str = ""
    database_url: str = ""


def check_gemini(api_key: str) -> None:
    client = genai.Client(api_key=api_key)
    models = list(client.models.list())
    generation = [m.name for m in models if "generateContent" in (m.supported_actions or []) and "flash" in m.name]
    embedding = [m.name for m in models if "embedContent" in (m.supported_actions or [])]
    print(f"[OK] Gemini: {len(models)} modelos disponibles")
    print(f"     Flash (chat): {', '.join(generation[:5])}")
    print(f"     Embeddings:   {', '.join(embedding[:5])}")


def check_supabase(database_url: str) -> None:
    with psycopg.connect(database_url, connect_timeout=10) as conn:
        version = conn.execute("SELECT version()").fetchone()[0]
        vector = conn.execute(
            "SELECT default_version, installed_version FROM pg_available_extensions WHERE name = 'vector'"
        ).fetchone()
    print(f"[OK] Supabase: {version.split(',')[0]}")
    if vector:
        state = f"instalada (v{vector[1]})" if vector[1] else f"disponible (v{vector[0]}), aún no activada"
        print(f"     pgvector: {state}")


if __name__ == "__main__":
    credentials = Credentials()
    for name, value, check in [
        ("GEMINI_API_KEY", credentials.gemini_api_key, check_gemini),
        ("DATABASE_URL", credentials.database_url, check_supabase),
    ]:
        if not value:
            print(f"[--] {name} vacío en .env")
            continue
        try:
            check(value)
        except Exception as error:  # el objetivo es diagnosticar, así que mostramos el tipo de error
            print(f"[FALLA] {name}: {type(error).__name__}: {str(error)[:200]}")
