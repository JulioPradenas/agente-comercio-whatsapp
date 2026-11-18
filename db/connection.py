"""Conexión a Postgres (Supabase) leyendo DATABASE_URL del .env."""

import psycopg
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str


def get_connection() -> psycopg.Connection:
    return psycopg.connect(DatabaseSettings().database_url)
