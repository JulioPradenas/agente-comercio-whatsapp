"""Mide si el retriever trae el chunk correcto para preguntas reales de clientes.

Métricas:
- hit@1: el chunk correcto es el primero.
- hit@k: el chunk correcto está entre los k que recibe el LLM (k = 4).
- MRR: promedio de 1/posición del chunk correcto (1.0 = siempre primero).

Uso: uv run python -m evals.retrieval_eval
"""

import json
import time
from pathlib import Path

import pandas as pd

from rag.retriever import search_policies

QUESTIONS_PATH = Path(__file__).parent / "retrieval_questions.jsonl"
K = 4


def evaluate() -> pd.DataFrame:
    rows = []
    for line in QUESTIONS_PATH.read_text().splitlines():
        case = json.loads(line)
        hits = search_policies(case["question"], k=K)
        retrieved = [hit.chunk_id for hit in hits]
        rank = retrieved.index(case["expected_chunk"]) + 1 if case["expected_chunk"] in retrieved else None
        rows.append({"question": case["question"], "rank": rank, "top_1": retrieved[0], "similarity_top_1": hits[0].similarity})
        time.sleep(0.7)  # bajo el rate limit del tier gratuito
    return pd.DataFrame(rows)


if __name__ == "__main__":
    results = evaluate()
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 55)
    print(results[["question", "rank", "top_1"]].to_string(index=False))
    print(f"\nhit@1 = {(results['rank'] == 1).mean():.2f}")
    print(f"hit@{K} = {results['rank'].notna().mean():.2f}")
    print(f"MRR   = {(1 / results['rank']).fillna(0).mean():.2f}")
