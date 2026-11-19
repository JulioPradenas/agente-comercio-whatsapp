"""Evaluación del agente completo (router + subagentes + tools + RAG + guardrails) sobre el golden set.

Métricas deterministas (exactas, gratis): ruta correcta, tools esperadas, derivaciones indebidas.
Métricas de calidad (LLM-as-judge, 1 a 5): relevancia, fidelidad a los datos y tono.

Es autosuficiente: levanta la API de comercio en un hilo y no escribe tickets reales.
Falla (exit 1) si alguna métrica queda bajo su umbral: así bloquea un PR que empeora el agente.

Uso: uv run python -m evals.agent_eval [--limit N]
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

COMMERCE_PORT = 8765
os.environ["HANDOFF_DRY_RUN"] = "1"
os.environ["COMMERCE_API_URL"] = f"http://127.0.0.1:{COMMERCE_PORT}"

import httpx  # noqa: E402
import pandas as pd  # noqa: E402
import uvicorn  # noqa: E402

from agent.graph import build_graph  # noqa: E402
from agent.guardrails import mask_pii  # noqa: E402
from agent.observability import get_client  # noqa: E402
from commerce_api.main import app as commerce_app  # noqa: E402
from evals.judge import judge_reply  # noqa: E402

EVALS_DIR = Path(__file__).parent
REPORT_PATH = EVALS_DIR / "report.md"
CUSTOMER_PHONE = "56989910085"  # cliente sintético con pedidos (dueño del 1011)
SECONDS_BETWEEN_CASES = 10  # tier gratuito: 15 requests/minuto por modelo

THRESHOLDS = {"route_accuracy": 0.90, "tool_accuracy": 0.90, "faithfulness": 4.0}


def start_commerce_api() -> None:
    server = uvicorn.Server(uvicorn.Config(commerce_app, port=COMMERCE_PORT, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        try:
            httpx.get(f"http://127.0.0.1:{COMMERCE_PORT}/docs", timeout=1)
            return
        except httpx.HTTPError:
            time.sleep(0.2)
    raise RuntimeError("La API de comercio no arrancó")


def run_case(case: dict) -> dict:
    graph = build_graph()  # memoria nueva por caso: los casos no se contaminan entre sí
    context = case["context"]
    current = {"role": "user", "text": mask_pii(case["message"]).text}
    result = graph.invoke(
        {"customer_phone": CUSTOMER_PHONE, "messages": [*context, current], "guard": None},
        {"configurable": {"thread_id": f"eval-{case['id']}"}},
    )

    new_messages = result["messages"][len(context) + 1 :]
    tool_messages = [m for m in new_messages if m["role"] == "tool"]
    tools_called = [m["name"] for m in tool_messages]
    ticket = result.get("handoff_ticket")
    expected = case["expected_route"]

    if expected == "handoff":
        route_ok = bool(ticket) and "router_rule" in ticket
    else:
        route_ok = result.get("intent") == expected
    expects_escalation = any("escalate_to_human" in expected for expected in case["expected_tools"])

    verdict = judge_reply([*context, current], [{"tool": m["name"], "result": m["result"]} for m in tool_messages], result["last_reply"])
    return {
        "id": case["id"],
        "expected_route": expected,
        "intent": result.get("intent"),
        "route_ok": route_ok,
        # "a|b" = cualquiera de las dos es válida (ej: el stock se puede ver con check_stock o search_products).
        "tools_ok": all(any(option in tools_called for option in expected.split("|")) for expected in case["expected_tools"]),
        "unexpected_handoff": bool(ticket) and expected != "handoff" and not expects_escalation,
        "tools_called": ", ".join(tools_called) or "-",
        "relevance": verdict.relevance,
        "faithfulness": verdict.faithfulness,
        "tone": verdict.tone,
        "judge_comment": verdict.comment,
        "reply": result["last_reply"],
    }


def summarize(results: pd.DataFrame) -> dict:
    return {
        "route_accuracy": results["route_ok"].mean(),
        "tool_accuracy": results["tools_ok"].mean(),
        "unexpected_handoffs": int(results["unexpected_handoff"].sum()),
        "relevance": results["relevance"].mean(),
        "faithfulness": results["faithfulness"].mean(),
        "tone": results["tone"].mean(),
    }


def write_report(results: pd.DataFrame, summary: dict, failed: list[str]) -> str:
    lines = [
        "# Evaluación del agente",
        "",
        f"Casos: {len(results)} · Estado: {'FALLA (' + ', '.join(failed) + ')' if failed else 'OK'}",
        "",
        "| Métrica | Valor | Umbral |",
        "|---|---|---|",
        f"| Ruta correcta | {summary['route_accuracy']:.0%} | ≥ {THRESHOLDS['route_accuracy']:.0%} |",
        f"| Tools esperadas | {summary['tool_accuracy']:.0%} | ≥ {THRESHOLDS['tool_accuracy']:.0%} |",
        f"| Derivaciones indebidas | {summary['unexpected_handoffs']} | - |",
        f"| Relevancia (juez, 1-5) | {summary['relevance']:.2f} | - |",
        f"| Fidelidad (juez, 1-5) | {summary['faithfulness']:.2f} | ≥ {THRESHOLDS['faithfulness']:.1f} |",
        f"| Tono (juez, 1-5) | {summary['tone']:.2f} | - |",
        "",
        "## Casos con observaciones",
        "",
        "| Caso | Ruta | Tools | Rel | Fid | Tono | Comentario del juez |",
        "|---|---|---|---|---|---|---|",
    ]
    flagged = results[~results["route_ok"] | ~results["tools_ok"] | results["unexpected_handoff"]
                      | (results[["relevance", "faithfulness", "tone"]].min(axis=1) < 4)]
    for row in flagged.itertuples():
        lines.append(
            f"| {row.id} | {'ok' if row.route_ok else 'X ' + str(row.intent)} | {'ok' if row.tools_ok else 'X ' + row.tools_called} "
            f"| {row.relevance} | {row.faithfulness} | {row.tone} | {row.judge_comment} |"
        )
    if flagged.empty:
        lines.append("| - | - | - | - | - | - | sin observaciones |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cases = [json.loads(line) for line in (EVALS_DIR / "golden_set.jsonl").read_text().splitlines()][:limit]

    start_commerce_api()
    rows = []
    for number, case in enumerate(cases, start=1):
        rows.append(run_case(case))
        row = rows[-1]
        print(f"[{number}/{len(cases)}] {case['id']:11} ruta={'ok' if row['route_ok'] else 'X'} "
              f"tools={'ok' if row['tools_ok'] else 'X'} juez={row['relevance']}/{row['faithfulness']}/{row['tone']}", flush=True)
        if number < len(cases):
            time.sleep(SECONDS_BETWEEN_CASES)

    results = pd.DataFrame(rows)
    summary = summarize(results)
    failed = [metric for metric, threshold in THRESHOLDS.items() if summary[metric] < threshold]
    report = write_report(results, summary, failed)
    REPORT_PATH.write_text(report)
    results.to_csv(EVALS_DIR / "results.csv", index=False)
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):  # en GitHub Actions se muestra en la página del run
        Path(summary_path).write_text(report)
    print("\n" + report)
    get_client().flush()
    sys.exit(1 if failed else 0)
