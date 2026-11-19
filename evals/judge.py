"""LLM-as-judge: un segundo modelo califica la respuesta del agente con una rúbrica explícita.

Se usa un modelo distinto al del agente para reducir el sesgo de autopreferencia
(un modelo tiende a calificar mejor respuestas parecidas a las suyas).
"""

import json
from functools import lru_cache

from google.genai import types
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent.llm import get_llm

JUDGE_PROMPT = """Eres un evaluador de calidad de un asistente de WhatsApp de una tienda chilena (HogarTec).
Recibes la conversación, los resultados de las herramientas que consultó el asistente y su respuesta final.
Califica de 1 a 5 cada criterio:

- relevance: ¿responde exactamente lo que el cliente preguntó? 5 = completo y directo; 1 = no responde.
- faithfulness: ¿cada dato concreto (precio, plazo, estado, política) está respaldado por los resultados
  de herramientas? 5 = todo respaldado; 1 = inventa o contradice datos. Si no hay datos concretos, 5.
- tone: cordial, breve (estilo WhatsApp, máximo ~5 líneas), sin códigos internos (SKU), en español de Chile.

Una derivación a un ejecutivo o un rechazo de seguridad es una respuesta válida si corresponde al caso.
Sé estricto y consistente: usa el 5 solo para respuestas sin ningún problema."""


class JudgeVerdict(BaseModel):
    relevance: int = Field(ge=1, le=5)
    faithfulness: int = Field(ge=1, le=5)
    tone: int = Field(ge=1, le=5)
    comment: str = Field(description="Una frase: el principal problema, o 'sin observaciones'")


class JudgeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    judge_model: str = "gemini-3.1-flash-lite"


@lru_cache
def judge_models() -> list[str]:
    _, agent_models = get_llm()
    judge = JudgeSettings().judge_model
    # El juez primero; si está saturado, el resto como respaldo.
    return [judge, *[model for model in agent_models if model != judge]]


def judge_reply(conversation: list[dict], tool_results: list[dict], reply: str) -> JudgeVerdict:
    client, _ = get_llm()
    payload = {
        "conversacion": [f"{m['role']}: {m['text']}" for m in conversation],
        "resultados_de_herramientas": tool_results,
        "respuesta_del_asistente": reply,
    }
    content = types.Content(role="user", parts=[types.Part.from_text(text=json.dumps(payload, ensure_ascii=False)[:6000])])
    config = types.GenerateContentConfig(
        system_instruction=JUDGE_PROMPT,
        response_mime_type="application/json",
        response_schema=JudgeVerdict,
        temperature=0,
    )
    last_error = None
    for model in judge_models():
        try:
            return client.models.generate_content(model=model, contents=[content], config=config).parsed
        except Exception as error:  # 429 / 503: siguiente modelo
            last_error = error
    raise RuntimeError(f"Juez no disponible: {last_error}")
