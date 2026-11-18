"""Evalúa el router contra el golden set: ¿clasifica bien y deriva cuando corresponde?

Ruta predicha = "handoff" si las reglas del router derivan; si no, "injection" u "off_topic" si
el guardrail de entrada actúa; si no, la intención.
Las derivaciones por política (ej: garantía) las decide el subagente, no el router:
en esos casos la ruta esperada es la intención (postsale).

Uso:
    uv run python -m evals.router_eval                    # golden set (clasificación y derivación)
    uv run python -m evals.router_eval adversarial_set    # ataques, fuera de tema y falsos positivos
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd

from agent.router import classify, guard_reason, handoff_reason

EVALS_DIR = Path(__file__).parent


def evaluate(dataset: str) -> pd.DataFrame:
    rows = []
    for line in (EVALS_DIR / f"{dataset}.jsonl").read_text().splitlines():
        case = json.loads(line)
        state = {"messages": [*case["context"], {"role": "user", "text": case["message"]}], "consecutive_failures": 0}
        decision = classify(state)
        predicted = "handoff" if handoff_reason(decision, 0) else guard_reason(decision) or decision.intent
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
    dataset = sys.argv[1] if len(sys.argv) > 1 else "golden_set"
    results = evaluate(dataset)
    results["correct"] = results["expected"] == results["predicted"]
    pd.set_option("display.width", 200)

    print(f"[{dataset}] Exactitud del router: {results['correct'].mean():.0%} ({results['correct'].sum()}/{len(results)})\n")
    print("Matriz de confusión (filas = esperado, columnas = predicho):")
    print(pd.crosstab(results["expected"], results["predicted"]).to_string())

    errors = results[~results["correct"]]
    if not errors.empty:
        print("\nErrores:")
        print(errors[["id", "expected", "predicted", "frustration", "message"]].to_string(index=False))
