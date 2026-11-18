"""Autenticación de rutas privadas (/pvt/) con los mismos headers que usa VTEX."""

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from commerce_api.config import settings


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
