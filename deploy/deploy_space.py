"""Despliega el agente en un Hugging Face Space (Docker), sin pasos manuales.

1. Crea el Space si no existe (público: Meta necesita llegar al webhook sin autenticación de HF).
2. Carga los secretos desde .env (nunca se imprimen) y genera credenciales nuevas para la API de comercio.
3. Sube el código: el Space construye la imagen con nuestro Dockerfile.

Uso: uv run python -m deploy.deploy_space
"""

import secrets
from pathlib import Path

from huggingface_hub import HfApi
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
SPACE_NAME = "agente-comercio-whatsapp"
APP_PORT = 8080  # debe coincidir con app_port de deploy/space_README.md

# Lo mismo que excluye .dockerignore, más lo que solo sirve en desarrollo.
IGNORE_PATTERNS = [
    ".env", ".venv/*", ".git/*", "**/__pycache__/*", "*.pyc", ".pytest_cache/*",
    "tests/*", "evals/*", "postman/*", "docs/*", "README.md",
]


class DeploySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    hf_token: str
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


def deploy() -> None:
    settings = DeploySettings()
    api = HfApi(token=settings.hf_token)
    repo_id = f"{api.whoami()['name']}/{SPACE_NAME}"

    api.create_repo(repo_id, repo_type="space", space_sdk="docker", private=False, exist_ok=True)
    print(f"Space: https://huggingface.co/spaces/{repo_id}")

    # Secretos: encriptados en HF, invisibles en la interfaz y en los logs.
    space_secrets = {
        "GEMINI_API_KEY": settings.gemini_api_key,
        "DATABASE_URL": settings.database_url,
        "WHATSAPP_TOKEN": settings.whatsapp_token,
        "WHATSAPP_PHONE_NUMBER_ID": settings.whatsapp_phone_number_id,
        "WHATSAPP_VERIFY_TOKEN": settings.whatsapp_verify_token,
        "WHATSAPP_APP_SECRET": settings.whatsapp_app_secret,
        # La API de comercio queda pública en /commerce: sus credenciales por defecto están en GitHub,
        # así que en cada despliegue se generan nuevas. Servidor y cliente viven en el mismo Space.
        "COMMERCE_APP_KEY": secrets.token_urlsafe(24),
        "COMMERCE_APP_TOKEN": secrets.token_urlsafe(32),
    }
    for key, value in space_secrets.items():
        api.add_space_secret(repo_id, key, value)
    print(f"Secretos cargados: {', '.join(space_secrets)}")

    # Variables: configuración no sensible, visible en la interfaz del Space.
    space_variables = {
        "APP_MODULE": "server:app",
        "COMMERCE_API_URL": f"http://127.0.0.1:{APP_PORT}/commerce",
        "WHATSAPP_GRAPH_VERSION": settings.whatsapp_graph_version,
        "WHATSAPP_DEMO_CUSTOMER_PHONE": settings.whatsapp_demo_customer_phone,
        "CHAT_MODEL": settings.chat_model,
        "FALLBACK_CHAT_MODEL": settings.fallback_chat_model,
    }
    for key, value in space_variables.items():
        api.add_space_variable(repo_id, key, value)
    print(f"Variables cargadas: {', '.join(space_variables)}")

    api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=ROOT,
        ignore_patterns=IGNORE_PATTERNS,
        commit_message="Despliegue desde deploy/deploy_space.py",
    )
    # El README del Space lleva la configuración de HF (sdk: docker, app_port); el de GitHub es otro.
    api.upload_file(
        repo_id=repo_id,
        repo_type="space",
        path_or_fileobj=ROOT / "deploy" / "space_README.md",
        path_in_repo="README.md",
        commit_message="README del Space",
    )
    space_host = repo_id.replace("/", "-").replace("_", "-").lower()
    print("Código subido. El Space está construyendo la imagen (unos minutos).")
    print(f"Webhook para Meta: https://{space_host}.hf.space/webhook")


if __name__ == "__main__":
    deploy()
