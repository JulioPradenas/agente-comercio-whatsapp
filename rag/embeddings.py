"""Embeddings con Gemini (Google Gen AI SDK).

El mismo código funciona contra Vertex AI cambiando el cliente a
genai.Client(vertexai=True, project=..., location=...).
"""

import time
from functools import lru_cache
from typing import Literal

import numpy as np
from google import genai
from google.genai import errors, types
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent.observability import observe

TaskType = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]
BATCH_SIZE = 50  # textos por request: menos llamadas a la API y menos riesgo de rate limit


class EmbeddingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_api_key: str
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768


@lru_cache
def get_client() -> tuple[genai.Client, EmbeddingSettings]:
    settings = EmbeddingSettings()
    return genai.Client(api_key=settings.gemini_api_key), settings


def _embed_batch(texts: list[str], task_type: TaskType, max_retries: int = 5) -> list[np.ndarray]:
    client, settings = get_client()
    for attempt in range(max_retries):
        try:
            response = client.models.embed_content(
                model=settings.embedding_model,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=settings.embedding_dim),
            )
            return [np.array(embedding.values, dtype=np.float32) for embedding in response.embeddings]
        except errors.ClientError as error:
            # 429 = cuota del tier gratuito agotada por ahora: esperar y reintentar (backoff exponencial).
            if error.code != 429 or attempt == max_retries - 1:
                raise
            wait_seconds = 2 ** (attempt + 2)
            print(f"  rate limit, reintento en {wait_seconds} s")
            time.sleep(wait_seconds)
    raise RuntimeError("unreachable")


def embed_documents(texts: list[str]) -> list[np.ndarray]:
    vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        vectors.extend(_embed_batch(texts[start : start + BATCH_SIZE], "RETRIEVAL_DOCUMENT"))
    return vectors


@observe(name="embed_query", as_type="embedding", capture_output=False)
def embed_query(text: str) -> np.ndarray:
    return _embed_batch([text], "RETRIEVAL_QUERY")[0]
