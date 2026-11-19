"""Medidor local de uso del LLM: tokens, costo y número de llamadas de un bloque de código.

Uso:
    with UsageMeter() as meter:
        respond(graph, phone, text)
    meter.cost_usd, meter.input_tokens, meter.calls

Registro global (con lock) y no ContextVar: LangGraph ejecuta los nodos en hilos propios donde un
ContextVar activado en el hilo principal no se ve (el medidor marcaba 0 llamadas). Limitación: mide
todo lo que ocurre mientras está activo, así que no separa conversaciones que corren en paralelo.
Se usa en la simulación y la evaluación, que procesan una conversación a la vez.
"""

import threading
from dataclasses import dataclass

_active_meters: list["UsageMeter"] = []
_lock = threading.Lock()


# eq=False: igualdad por identidad. Con el __eq__ por valores de dataclass, dos medidores anidados con
# los mismos conteos son "iguales" y list.remove() sacaba de la lista el medidor equivocado.
@dataclass(eq=False)
class UsageMeter:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def __enter__(self) -> "UsageMeter":
        with _lock:
            _active_meters.append(self)
        return self

    def __exit__(self, *exc_info) -> None:
        with _lock:
            _active_meters.remove(self)


def record_usage(input_tokens: int, output_tokens: int, cost_usd: float) -> None:
    """La llama agent/llm.py en cada respuesta de Gemini. Suma a todos los medidores activos
    (permite anidar: uno por conversación y otro por turno)."""
    with _lock:
        for meter in _active_meters:
            meter.calls += 1
            meter.input_tokens += input_tokens
            meter.output_tokens += output_tokens
            meter.cost_usd += cost_usd
