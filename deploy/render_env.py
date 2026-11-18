"""Genera .env.render: el bloque de variables para pegar en Render > Environment > "Add from .env".

Toma los secretos del .env local y genera credenciales nuevas para la API de comercio
(en Render queda pública en /commerce; las de desarrollo están en GitHub).
El archivo contiene secretos: está en .gitignore y conviene borrarlo después de pegarlo.

Uso: uv run python -m deploy.render_env
"""

import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_api_key: str
    database_url: str
    whatsapp_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str
    whatsapp_app_secret: str
    whatsapp_graph_version: str = "v25.0"
    whatsapp_demo_customer_phone: str = "56989910085"
    chat_model: str = "gemini-3.5-flash-lite"
    fallback_chat_model: str = "gemini-3.1-flash-lite"


PORT = 8080  # se fija explícitamente: Render usa 10000 por defecto y COMMERCE_API_URL debe apuntar al mismo puerto
OUTPUT = Path(__file__).resolve().parent.parent / ".env.render"


def build_env() -> dict[str, str]:
    settings = DeploySettings()
    return {
        "PORT": str(PORT),
        "APP_MODULE": "server:app",
        "COMMERCE_API_URL": f"http://127.0.0.1:{PORT}/commerce",
        "COMMERCE_APP_KEY": secrets.token_urlsafe(24),
        "COMMERCE_APP_TOKEN": secrets.token_urlsafe(32),
        "GEMINI_API_KEY": settings.gemini_api_key,
        "CHAT_MODEL": settings.chat_model,
        "FALLBACK_CHAT_MODEL": settings.fallback_chat_model,
        "DATABASE_URL": settings.database_url,
        "WHATSAPP_TOKEN": settings.whatsapp_token,
        "WHATSAPP_PHONE_NUMBER_ID": settings.whatsapp_phone_number_id,
        "WHATSAPP_VERIFY_TOKEN": settings.whatsapp_verify_token,
        "WHATSAPP_APP_SECRET": settings.whatsapp_app_secret,
        "WHATSAPP_GRAPH_VERSION": settings.whatsapp_graph_version,
        "WHATSAPP_DEMO_CUSTOMER_PHONE": settings.whatsapp_demo_customer_phone,
    }


if __name__ == "__main__":
    env = build_env()
    OUTPUT.write_text("".join(f"{key}={value}\n" for key, value in env.items()))
    print(f"Generado {OUTPUT.name} con {len(env)} variables: {', '.join(env)}")
