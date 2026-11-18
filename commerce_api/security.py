"""Autenticación de rutas privadas (/pvt/) con los mismos headers que usa VTEX."""

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from pydantic_settings import BaseSettings, SettingsConfigDict


class CommerceSettings(BaseSettings):
    # Se leen de variables de entorno COMMERCE_APP_KEY / COMMERCE_APP_TOKEN (o del .env).
    # Los valores por defecto existen solo porque es una API simulada local.
    model_config = SettingsConfigDict(env_prefix="COMMERCE_", env_file=".env", extra="ignore")
    app_key: str = "hogartec-dev-key"
    app_token: str = "hogartec-dev-token"


settings = CommerceSettings()


def require_app_credentials(
    app_key: Annotated[str | None, Header(alias="X-VTEX-API-AppKey")] = None,
    app_token: Annotated[str | None, Header(alias="X-VTEX-API-AppToken")] = None,
) -> None:
    # compare_digest compara en tiempo constante: evita adivinar el token midiendo cuánto tarda la respuesta.
    valid = (
        app_key is not None
        and app_token is not None
        and secrets.compare_digest(app_key, settings.app_key)
        and secrets.compare_digest(app_token, settings.app_token)
    )
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")


PrivateRoute = Depends(require_app_credentials)
