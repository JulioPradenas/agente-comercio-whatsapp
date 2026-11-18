"""Conversar con el agente desde la terminal.

Requiere la API de comercio corriendo: uv run fastapi dev commerce_api/main.py --port 8001
Uso:
    uv run python -m agent.cli              # conversación de ejemplo
    uv run python -m agent.cli --interactive
"""

import sys

from agent.graph import build_graph

DEMO_PHONE = "56989910085"  # cliente de los datos sintéticos (dueño del pedido 1011)

DEMO_CONVERSATION = [
    "Hola! cuánto cuesta el despacho?",
    "Ya, busco un refri no frost grande, que no pase de 700 lucas",
    "Me gusta el más grande, agrégalo al carro porfa",
    "Otra cosa, en qué va mi último pedido?",
    "Y si me arrepiento de lo que compré en ese pedido, lo puedo devolver?",
]


def chat(graph, phone: str, text: str) -> str:
    # thread_id = teléfono: cada cliente tiene su propia memoria de conversación.
    config = {"configurable": {"thread_id": phone}}
    result = graph.invoke({"customer_phone": phone, "messages": [{"role": "user", "text": text}]}, config)
    return result["last_reply"]


if __name__ == "__main__":
    graph = build_graph()
    if "--interactive" in sys.argv:
        while (text := input("\nCLIENTE: ").strip()) not in {"", "salir"}:
            print(f"AGENTE:  {chat(graph, DEMO_PHONE, text)}")
    else:
        for text in DEMO_CONVERSATION:
            print(f"\nCLIENTE: {text}")
            print(f"AGENTE:  {chat(graph, DEMO_PHONE, text)}")
