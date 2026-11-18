"""Cliente de Gemini con timeout, reintentos acotados y modelo de respaldo."""

from functools import lru_cache

from google import genai
from google.genai import errors, types
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_api_key: str
    # Medido el 18-nov-2026 en el tier gratuito: los "flash" respondían 503 (saturados) y los
    # "flash-lite" respondían en ~1,6 s con tools. gemini-2.5-flash ya no se habilita a cuentas nuevas.
    chat_model: str = "gemini-3.5-flash-lite"
    fallback_chat_model: str = "gemini-3.1-flash-lite"
    request_timeout_ms: int = 30_000


@lru_cache
def get_llm() -> tuple[genai.Client, list[str]]:
    settings = LLMSettings()
    client = genai.Client(
        api_key=settings.gemini_api_key,
        # Reintentos del SDK acotados: ante una falla es mejor pasar rápido al modelo de respaldo.
        http_options=types.HttpOptions(
            timeout=settings.request_timeout_ms, retry_options=types.HttpRetryOptions(attempts=2)
        ),
    )
    return client, [settings.chat_model, settings.fallback_chat_model]


def generate(contents: list[types.Content], config: types.GenerateContentConfig) -> types.GenerateContentResponse:
    client, models = get_llm()
    for model in models:
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except errors.ClientError as error:
            # 429 = cuota agotada. En el tier gratuito la cuota es por modelo (15 req/min),
            # así que el modelo de respaldo sí puede responder. Otro 4xx = request mal armado: se propaga.
            if error.code != 429:
                raise
            print(f"   [{model} sin cuota (429), probando el siguiente modelo]")
        except Exception as error:  # 503, timeout, red: problemas del proveedor -> siguiente modelo
            print(f"   [{model} no disponible ({type(error).__name__}), probando el siguiente modelo]")
    raise RuntimeError("Ningún modelo disponible")
