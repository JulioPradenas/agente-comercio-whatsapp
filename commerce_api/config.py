"""Configuración de la API, leída de variables de entorno con prefijo COMMERCE_ (o del .env)."""

from datetime import date

from pydantic_settings import BaseSettings, SettingsConfigDict


class CommerceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COMMERCE_", env_file=".env", extra="ignore")

    # Los valores por defecto existen solo porque es una API simulada local.
    app_key: str = "hogartec-dev-key"
    app_token: str = "hogartec-dev-token"

    # "Hoy" para las reglas de negocio. Los datos sintéticos están congelados al 20-nov-2026;
    # con date.today() los plazos de devolución vencerían solos con el paso del tiempo.
    today: date = date(2026, 11, 20)

    store_url: str = "https://hogartec.example"
    return_window_days: int = 10
    free_shipping_threshold: int = 49_990
    shipping_cost: int = 3_990


settings = CommerceSettings()
