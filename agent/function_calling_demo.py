"""Loop de function calling escrito a mano, para ver cada ida y vuelta con el modelo.

En el paso siguiente LangGraph reemplaza este loop; la mecánica es la misma.

Requiere la API de comercio corriendo: uv run fastapi dev commerce_api/main.py --port 8001
Uso: uv run python -m agent.function_calling_demo
"""

import json

from google import genai
from google.genai import errors, types
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent.tools import CommerceTools

MAX_TOOL_ROUNDS = 5  # corta loops infinitos si el modelo insiste en llamar herramientas

SYSTEM_PROMPT = """Eres el asistente de HogarTec por WhatsApp, una tienda online chilena de electro y hogar.
- Responde en español de Chile, cordial y breve (es WhatsApp: máximo 4-5 líneas).
- Precios, stock, estados de pedido y políticas SIEMPRE salen de una herramienta. Nunca los inventes.
- Antes de agregar al carrito o crear una devolución, confirma con el cliente.
- Si una herramienta devuelve `error`, sigue su `guidance`."""


class ChatSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_api_key: str
    # Medido el 18-nov-2026 en el tier gratuito: los "flash" respondían 503 (saturados) y los
    # "flash-lite" respondían en ~1,6 s con tools. gemini-2.5-flash ya no se habilita a cuentas nuevas.
    chat_model: str = "gemini-3.5-flash-lite"
    # Si el modelo principal falla, se usa este: el agente no puede quedarse mudo.
    fallback_chat_model: str = "gemini-3.1-flash-lite"


def generate_with_fallback(
    client: genai.Client, models: list[str], history: list[types.Content], config: types.GenerateContentConfig
) -> types.GenerateContentResponse:
    for model in models:
        try:
            return client.models.generate_content(model=model, contents=history, config=config)
        except errors.ClientError:
            raise  # 4xx: el request está mal; otro modelo no lo arreglaría
        except Exception as error:  # 503, timeout, red: problemas del proveedor -> siguiente modelo
            print(f"   [{model} no disponible ({type(error).__name__}), probando el siguiente modelo]")
    raise RuntimeError("Ningún modelo disponible")


def preview(data: dict, limit: int = 220) -> str:
    text = json.dumps(data, ensure_ascii=False)
    return text if len(text) <= limit else f"{text[:limit]}..."


def run_turn(client: genai.Client, models: list[str], tools: CommerceTools, history: list[types.Content], user_text: str) -> str:
    history.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))
    functions = {function.__name__: function for function in tools.functions()}
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=tools.declarations())],
        # Desactivado a propósito: queremos ejecutar las funciones nosotros y ver cada paso.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.2,
    )

    for _ in range(MAX_TOOL_ROUNDS):
        response = generate_with_fallback(client, models, history, config)
        # Se guarda el turno completo del modelo (incluye firmas internas que Gemini necesita después).
        history.append(response.candidates[0].content)

        if not response.function_calls:
            return response.text

        # 1) El modelo pidió una o más funciones; 2) las ejecutamos; 3) le devolvemos los resultados.
        result_parts = []
        for call in response.function_calls:
            arguments = dict(call.args or {})
            print(f"   [modelo pide]  {call.name}({preview(arguments)})")
            result = functions[call.name](**arguments)
            print(f"   [resultado]    {preview(result)}")
            result_parts.append(types.Part.from_function_response(name=call.name, response=result))
        history.append(types.Content(role="user", parts=result_parts))

    return "Disculpa, no pude resolver tu consulta. Te derivo con un ejecutivo."


CONVERSATION = [
    "Hola! busco un refri no frost grande, que no pase de 700 lucas",
    "Me gusta el más grande, agrégalo al carro porfa",
    "Y si no me convence, cuántos días tengo para devolverlo?",
    "Otra cosa, en qué va mi último pedido?",
    "Y el pedido 1006, me dices en qué estado está?",
]

if __name__ == "__main__":
    settings = ChatSettings()
    # Reintentos del SDK acotados: ante un 503 es mejor pasar rápido al modelo de respaldo.
    client = genai.Client(
        api_key=settings.gemini_api_key,
        # timeout en ms: una respuesta que tarda más de 30 s ya es una mala experiencia en WhatsApp.
        http_options=types.HttpOptions(timeout=30_000, retry_options=types.HttpRetryOptions(attempts=2)),
    )
    models = [settings.chat_model, settings.fallback_chat_model]
    # El teléfono viene de WhatsApp (aquí, el dueño del pedido 1011). El modelo nunca lo elige.
    tools = CommerceTools(customer_phone="56989910085")
    history: list[types.Content] = []

    for message in CONVERSATION:
        print(f"\nCLIENTE: {message}")
        answer = run_turn(client, models, tools, history, message)
        print(f"AGENTE:  {answer}")
