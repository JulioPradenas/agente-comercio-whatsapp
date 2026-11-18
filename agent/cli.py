"""Conversar con el agente desde la terminal.

Requiere la API de comercio corriendo: uv run fastapi dev commerce_api/main.py --port 8001
Uso:
    uv run python -m agent.cli              # escenarios de ejemplo
    uv run python -m agent.cli --interactive
"""

import sys

from agent.graph import build_graph, resume_bot

# Clientes reales de los datos sintéticos. Cada teléfono es una conversación (thread) distinta.
SCENARIOS = {
    "Pide una persona (regla del router)": (
        "56989910085",
        ["hola, quiero hablar con una persona por favor", "hola? hay alguien?"],
    ),
    "Producto con falla (política -> el subagente deriva)": (
        "56949169500",
        ["Hola, el refrigerador que me llegó hace dos meses dejó de enfriar, qué hago?"],
    ),
    "Amenaza legal (regla del router)": (
        "56934889349",
        ["Llevo una semana esperando y nadie me responde, voy a poner un reclamo en el SERNAC"],
    ),
    # Su último pedido (1291) va en camino y llega hoy: queja normal, el bot la resuelve.
    "Queja normal con pedido en camino (no debe derivar)": (
        "56948971371",
        ["pucha, mi pedido no ha llegado, en qué va?"],
    ),
    # Su último pedido (1009) figura entregado: la política manda derivar.
    "Pedido entregado que no llegó (política -> deriva)": (
        "56964647678",
        ["pucha, mi pedido no ha llegado, en qué va?"],
    ),
}


def chat(graph, phone: str, text: str) -> str:
    # thread_id = teléfono: cada cliente tiene su propia memoria de conversación.
    config = {"configurable": {"thread_id": phone}}
    result = graph.invoke({"customer_phone": phone, "messages": [{"role": "user", "text": text}]}, config)
    return result["last_reply"] or f"(bot en pausa: el caso {result['handoff_ticket']} lo atiende un ejecutivo)"


if __name__ == "__main__":
    graph = build_graph()
    if "--interactive" in sys.argv:
        phone = "56989910085"
        while (text := input("\nCLIENTE: ").strip()) not in {"", "salir"}:
            if text == "/reanudar":
                resume_bot(graph, phone)
                print("(el ejecutivo cerró el caso; el bot vuelve a atender)")
                continue
            print(f"AGENTE:  {chat(graph, phone, text)}")
    else:
        for title, (phone, messages) in SCENARIOS.items():
            print(f"\n=== {title} ===")
            for text in messages:
                print(f"CLIENTE: {text}")
                print(f"AGENTE:  {chat(graph, phone, text)}")
