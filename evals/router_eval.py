"""Evalúa el router contra el golden set: ¿clasifica bien y deriva cuando corresponde?

Ruta predicha = "handoff" si las reglas del router derivan; si no, la intención.
Las derivaciones por política (ej: garantía) las decide el subagente, no el router:
en esos casos la ruta esperada es la intención (postsale).

Uso: uv run python -m evals.router_eval
"""

import json
import time
from pathlib import Path

import pandas as pd

from agent.router import classify, handoff_reason

GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"


def evaluate() -> pd.DataFrame:
    rows = []
    for line in GOLDEN_SET.read_text().splitlines():
        case = json.loads(line)
        state = {"messages": [*case["context"], {"role": "user", "text": case["message"]}], "consecutive_failures": 0}
        decision = classify(state)
        predicted = "handoff" if handoff_reason(decision, 0) else decision.intent
        rows.append(
            {
                "id": case["id"],
                "expected": case["expected_route"],
                "predicted": predicted,
                "frustration": decision.frustration,
                "message": case["message"][:60],
            }
        )
        time.sleep(4)  # tier gratuito: 15 requests por minuto por modelo
    return pd.DataFrame(rows)


if __name__ == "__main__":
    results = evaluate()
    results["correct"] = results["expected"] == results["predicted"]
    pd.set_option("display.width", 200)

    print(f"Exactitud del router: {results['correct'].mean():.0%} ({results['correct'].sum()}/{len(results)})\n")
    print("Matriz de confusión (filas = esperado, columnas = predicho):")
    print(pd.crosstab(results["expected"], results["predicted"]).to_string())

    errors = results[~results["correct"]]
    if not errors.empty:
        print("\nErrores:")
        print(errors[["id", "expected", "predicted", "frustration", "message"]].to_string(index=False))
