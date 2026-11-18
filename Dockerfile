# Una imagen para los dos servicios; APP_MODULE elige cuál arranca:
#   webhook + agente:  channels.whatsapp_webhook:app   (por defecto)
#   API de comercio:   commerce_api.main:app
FROM python:3.12-slim

# uv copiado desde su imagen oficial, con versión fija (la misma que en desarrollo).
COPY --from=ghcr.io/astral-sh/uv:0.11.13 /uv /bin/uv

# Usuario sin privilegios creado ANTES de copiar archivos: así se usa COPY --chown.
# (Un `RUN chown -R` posterior duplicaría todo /app en una capa nueva: la imagen pesaba 1,6 GB por eso.)
RUN useradd --create-home appuser && mkdir /app && chown appuser /app
USER appuser
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PYTHONUNBUFFERED=1

# Primero solo las dependencias: esta capa se reutiliza (caché de Docker) mientras uv.lock no cambie,
# así un cambio de código no reinstala todo. UV_NO_CACHE evita dejar los paquetes descargados en la imagen.
COPY --chown=appuser pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=appuser . .
ENV PATH="/app/.venv/bin:$PATH" \
    APP_MODULE=channels.whatsapp_webhook:app

# Cloud Run define PORT (8080). Forma shell para expandir variables; `exec` hace que uvicorn
# reciba directo las señales de apagado (SIGTERM) y cierre ordenadamente.
CMD exec uvicorn ${APP_MODULE} --host 0.0.0.0 --port ${PORT:-8080} --no-access-log
