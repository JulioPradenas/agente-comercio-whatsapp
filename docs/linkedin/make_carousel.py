"""Carrusel de LinkedIn (PDF 4:5, 1080 x 1350) para el post con ángulo de datos.

Los números salen de los datos del proyecto: conversaciones simuladas (analytics/data) y los
resultados de las evaluaciones. Los intervalos de confianza se calculan aquí (Wilson, 95%).

Uso: uv run python docs/linkedin/make_carousel.py
"""

import math
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).parent
AUTHOR = "Julio Pradenas"

# Paleta validada para daltonismo (la misma del dashboard)
BG, INK, INK2, INK3, RULE = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e5e4df"
BAND, BLUE, ORANGE, AQUA, BAD = "#11203a", "#2a78d6", "#eb6834", "#1baf7a", "#d03b3b"
FUNNEL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab"]
TITLE_FONT, BODY_FONT, MONO_FONT = "Avenir Next", "Helvetica Neue", "Menlo"
TOTAL_SLIDES = 9


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson: mejor que el intervalo normal con n chico o proporciones cerca de 0 o 1."""
    p = successes / n
    center = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return center - half, center + half


def pct(value: float, decimals: int = 0) -> str:
    return f"{value * 100:.{decimals}f}%".replace(".", ",")


def new_slide(number: int, eyebrow: str | None = None):
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
    fig.patch.set_facecolor(BG)
    if eyebrow:
        fig.text(0.08, 0.915, eyebrow.upper(), fontsize=15, color=BLUE, fontweight="bold", family=BODY_FONT)
    fig.text(0.08, 0.04, f"{AUTHOR} · Agente de IA evaluado como un modelo", fontsize=13, color=INK3, family=BODY_FONT)
    fig.text(0.92, 0.04, f"{number}/{TOTAL_SLIDES}", fontsize=13, color=INK3, family=BODY_FONT, ha="right")
    return fig


def title(fig, text: str, y: float = 0.87, size: int = 40, width: int = 26, color: str = INK) -> float:
    lines = textwrap.wrap(text, width)
    for i, line in enumerate(lines):
        fig.text(0.08, y - i * size * 0.0016, line, fontsize=size, color=color, fontweight="bold", family=TITLE_FONT, va="top")
    return y - len(lines) * size * 0.0016


def body(fig, text: str, y: float, size: int = 21, width: int = 48, color: str = INK2, weight: str = "normal") -> float:
    line_height = size * 0.00165
    for paragraph in text.split("\n"):
        for line in textwrap.wrap(paragraph, width) or [""]:
            fig.text(0.08, y, line, fontsize=size, color=color, family=BODY_FONT, va="top", fontweight=weight)
            y -= line_height
    return y


def style_axis(ax) -> None:
    ax.set_facecolor(BG)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=INK2, labelsize=15, length=0)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_family(BODY_FONT)


def main() -> None:
    conversations = pd.read_csv(ROOT / "analytics" / "data" / "conversations.csv")
    n_total = len(conversations)
    resolved = int(conversations["resolved"].sum())
    sales = conversations[conversations["sales_conversation"]]
    n_sales, converted = len(sales), int(sales["converted"].sum())
    containment, conversion = resolved / n_total, converted / n_sales
    containment_ci, conversion_ci = wilson(resolved, n_total), wilson(converted, n_sales)
    cost = conversations["cost_usd"].mean()

    slides = []

    # 1. Portada
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
    fig.patch.set_facecolor(BAND)
    fig.text(0.08, 0.86, "UN AGENTE DE IA, EVALUADO COMO UN MODELO", fontsize=16, color="#86b6ef", fontweight="bold", family=BODY_FONT)
    fig.text(0.08, 0.74, f"{pct(containment)}", fontsize=150, color="white", fontweight="bold", family=TITLE_FONT, va="top")
    fig.text(0.08, 0.55, "de contención.", fontsize=44, color="white", fontweight="bold", family=TITLE_FONT, va="top")
    fig.text(0.08, 0.47, "El intervalo de confianza va", fontsize=44, color="#86b6ef", fontweight="bold", family=TITLE_FONT, va="top")
    fig.text(0.08, 0.40, f"de {pct(containment_ci[0])} a {pct(containment_ci[1])}.", fontsize=44, color="#86b6ef", fontweight="bold", family=TITLE_FONT, va="top")
    fig.text(0.08, 0.25, "Lo que aprendí midiendo un agente de WhatsApp\ncon las reglas de un data scientist.", fontsize=22, color="#c9d3e3", family=BODY_FONT, va="top", linespacing=1.5)
    fig.text(0.08, 0.06, f"{AUTHOR}  ·  desliza para ver más", fontsize=16, color="#c9d3e3", family=BODY_FONT)
    slides.append(fig)

    # 2. El caso
    fig = new_slide(2, "El caso")
    y = title(fig, "Un agente de WhatsApp para una tienda online")
    y = body(fig, "Tienda ficticia de electro y hogar. El agente recomienda productos, arma el carrito con link de pago, "
                  "consulta pedidos, gestiona devoluciones y deriva a un ejecutivo cuando corresponde.", y - 0.03)
    facts = [("30", "conversaciones simuladas contra el agente real"), ("10", "perfiles de cliente distintos"),
             ("7", "vistas de KPIs en BigQuery"), ("3", "iteraciones de evaluación")]
    for i, (number, label) in enumerate(facts):
        fy = y - 0.07 - i * 0.095
        fig.text(0.08, fy, number, fontsize=56, color=BLUE, fontweight="bold", family=TITLE_FONT, va="top")
        fig.text(0.25, fy - 0.022, label, fontsize=22, color=INK, family=BODY_FONT, va="top")
    body(fig, "El comportamiento del agente, el costo y la latencia son reales. La mezcla de clientes es simulada.",
         0.125, size=17, color=INK3, width=60)
    slides.append(fig)

    # 3. KPIs en SQL
    fig = new_slide(3, "1 · Definir antes de mirar")
    y = title(fig, "Cada KPI se define una sola vez, en SQL")
    y = body(fig, "Antes de ver un resultado, cada métrica tiene una definición exacta en una vista de BigQuery. "
                  "El dashboard solo la muestra.", y - 0.03)
    code = ("-- Contención: termina sin ejecutivo\n-- y sin respuesta de error\n"
            "ROUND(AVG(CAST(resolved AS INT64)), 3)\n    AS containment_rate,\n\n"
            "-- Conversión: solo sobre conversaciones\n-- de venta (no se diluye)\n"
            "SAFE_DIVIDE(COUNTIF(converted),\n    COUNTIF(sales_conversation))\n    AS sales_conversion_rate")
    box_top = y - 0.04
    fig.patches.append(FancyBboxPatch((0.08, box_top - 0.36), 0.84, 0.36, boxstyle="round,pad=0,rounding_size=0.015",
                                      transform=fig.transFigure, facecolor="#f0efea", edgecolor=RULE))
    fig.text(0.11, box_top - 0.03, code, fontsize=17, color=INK, family=MONO_FONT, va="top", linespacing=1.55)
    body(fig, "Si mañana cambia la definición, cambia en un lugar y todos los reportes la heredan.", box_top - 0.40, size=19)
    slides.append(fig)

    # 4. Componentes vs sistema
    fig = new_slide(4, "2 · Componentes y sistema")
    y = title(fig, "Cada pieza aprobó. El sistema completo, no.")
    rows = [("Recuperación (RAG)", "hit@4 = 1,00 · MRR = 0,93"), ("Router de intención", "30/30"), ("Guardrails", "16/16")]
    for i, (component, result) in enumerate(rows):
        ry = y - 0.05 - i * 0.055
        fig.text(0.08, ry, component, fontsize=21, color=INK2, family=BODY_FONT, va="top")
        fig.text(0.92, ry, result, fontsize=21, color=INK, fontweight="bold", family=BODY_FONT, va="top", ha="right")
    ax = fig.add_axes([0.14, 0.17, 0.76, 0.33])
    style_axis(ax)
    iterations, accuracy = [1, 2, 3], [0.90, 0.87, 1.00]
    ax.plot(iterations, accuracy, color=BLUE, linewidth=3, marker="o", markersize=12, markerfacecolor=BLUE, markeredgecolor=BG, markeredgewidth=2)
    for x, value in zip(iterations, accuracy):
        ax.annotate(pct(value), (x, value), textcoords="offset points", xytext=(0, 16), ha="center", fontsize=18, color=INK, fontweight="bold", family=BODY_FONT)
    ax.set_xticks(iterations, ["Corrida 1", "Corrida 2", "Corrida 3"])
    ax.set_ylim(0.82, 1.06)
    ax.set_yticks([0.85, 0.9, 0.95, 1.0], ["85%", "90%", "95%", "100%"])
    ax.tick_params(axis="x", pad=10)
    ax.grid(axis="y", color=RULE)
    ax.set_title("Uso correcto de herramientas, evaluación de punta a punta", fontsize=17, color=INK2, family=BODY_FONT, loc="left", pad=18)
    body(fig, "Encontró 4 fallas que 85 tests no veían. Bajó antes de subir.", 0.12, size=19, color=INK, weight="bold")
    slides.append(fig)

    # 5. Desconfiar de los propios números
    fig = new_slide(5, "3 · Desconfiar de mis números")
    y = title(fig, "Mi evaluación dio 100%. No lo celebré.")
    y = body(fig, "Escribí los casos de prueba sabiendo cómo funciona el agente. Es como evaluar un modelo con sus datos de entrenamiento.", y - 0.03)
    risks = [("Sesgo del set de evaluación", "Los casos los escribe quien construyó el agente.", "Casos escritos por Atención a Clientes, sin ver los prompts."),
             ("Juez sin calibrar", "Un LLM califica las respuestas; nadie validó su criterio.", "20 respuestas etiquetadas por una persona y acuerdo medido (kappa).")]
    ry = y - 0.05
    for name, problem, fix in risks:
        fig.patches.append(FancyBboxPatch((0.08, ry - 0.205), 0.84, 0.205, boxstyle="round,pad=0,rounding_size=0.015",
                                          transform=fig.transFigure, facecolor="white", edgecolor=RULE))
        fig.text(0.11, ry - 0.03, name, fontsize=23, color=INK, fontweight="bold", family=TITLE_FONT, va="top")
        fig.text(0.11, ry - 0.08, "\n".join(textwrap.wrap(problem, 52)), fontsize=18, color=INK2, family=BODY_FONT, va="top", linespacing=1.4)
        fig.text(0.11, ry - 0.145, "\n".join(textwrap.wrap("Solución: " + fix, 52)), fontsize=18, color=BLUE, family=BODY_FONT, va="top", linespacing=1.4)
        ry -= 0.24
    slides.append(fig)

    # 6. Segmentar
    fig = new_slide(6, "4 · Segmentar antes de concluir")
    y = title(fig, f"La contención total era {pct(containment)}. En FAQ, 37,5%.")
    by_intent = (conversations.dropna(subset=["first_intent"]).groupby("first_intent")["resolved"].mean()
                 .reindex(["sales", "postsale", "faq"]))
    labels = ["Ventas", "Postventa", "FAQ"]
    ax = fig.add_axes([0.24, 0.30, 0.64, 0.30])
    style_axis(ax)
    bars = ax.barh(labels[::-1], by_intent.values[::-1], color=[ORANGE, AQUA, AQUA], height=0.55)
    for bar, value in zip(bars, by_intent.values[::-1]):
        ax.text(value + 0.02, bar.get_y() + bar.get_height() / 2, pct(value, 1), va="center", fontsize=19, color=INK, fontweight="bold", family=BODY_FONT)
    ax.set_xlim(0, 1.15)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="y", labelsize=19)
    body(fig, "No era un error del bot. En FAQ caían los \"quiero hablar con una persona\", que se derivan correctamente.",
         0.24, size=20, color=INK)
    body(fig, "Un KPI agregado puede contar la historia equivocada.", 0.135, size=20, color=BLUE, weight="bold")
    slides.append(fig)

    # 7. Embudo
    fig = new_slide(7, "5 · Dónde se pierde la venta")
    y = title(fig, "La venta se pierde antes del pago")
    steps = ["Consulta de compra", "Recibió recomendaciones", "Agregó al carrito", "Recibió link de pago"]
    values = [12, 11, 4, 4]
    ax = fig.add_axes([0.40, 0.27, 0.52, 0.40])
    style_axis(ax)
    ax.barh(steps[::-1], values[::-1], color=FUNNEL[::-1], height=0.6)
    for i, value in enumerate(values[::-1]):
        ax.text(value + 0.2, i, f"{value}  ·  {pct(value / values[0])}", va="center", fontsize=19, color=INK, fontweight="bold", family=BODY_FONT)
    ax.set_xlim(0, 19)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="y", labelsize=17, pad=8)
    body(fig, "De 92% a 33% entre recomendar y agregar al carrito. El pago no es el problema.", 0.20, size=20, color=INK, weight="bold")
    body(fig, "n = 12 conversaciones de venta: el patrón orienta, no confirma.", 0.12, size=17, color=INK3)
    slides.append(fig)

    # 8. Intervalos de confianza
    fig = new_slide(8, "La parte que más importa")
    y = title(fig, "Con n = 30, un KPI es un rango, no un número")
    ax = fig.add_axes([0.30, 0.30, 0.60, 0.28])
    style_axis(ax)
    names = [f"Conversión\n(n = {n_sales})", f"Contención\n(n = {n_total})"]
    points = [conversion, containment]
    intervals = [conversion_ci, containment_ci]
    for i, (point, (low, high)) in enumerate(zip(points, intervals)):
        ax.plot([low, high], [i, i], color=BLUE, linewidth=6, solid_capstyle="round", alpha=0.35)
        ax.plot(point, i, "o", color=BLUE, markersize=16, markeredgecolor=BG, markeredgewidth=2)
        ax.text(low, i + 0.28, pct(low), ha="center", fontsize=16, color=INK2, family=BODY_FONT)
        ax.text(high, i + 0.28, pct(high), ha="center", fontsize=16, color=INK2, family=BODY_FONT)
        ax.text(point, i - 0.36, pct(point), ha="center", fontsize=19, color=INK, fontweight="bold", family=BODY_FONT)
    ax.set_yticks([0, 1], names)
    ax.tick_params(axis="y", labelsize=17)
    ax.set_ylim(-0.7, 1.6)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.grid(axis="x", color=RULE)
    body(fig, "Intervalos de Wilson al 95%.", 0.235, size=16, color=INK3)
    body(fig, "Sirve para encontrar problemas, no para decidir. Eso lo decide el piloto con clientes reales.", 0.18, size=21, color=INK, weight="bold")
    slides.append(fig)

    # 9. Lo medido con precisión + cierre
    fig = new_slide(9, "Medido con precisión")
    y = title(fig, "Lo que sí sé con certeza")
    metrics = [(f"US${cost:.4f}".replace(".", ","), "por conversación, a precio de lista de Gemini", INK),
               ("18,1 s", "de latencia p90. La meta era 15 s: no se cumple.", BAD),
               ("~6 s", "de cada respuesta los toma el router solo para clasificar. Es el próximo sprint.", INK)]
    for i, (value, label, color) in enumerate(metrics):
        my = y - 0.06 - i * 0.165
        fig.text(0.08, my, value, fontsize=50, color=color, fontweight="bold", family=TITLE_FONT, va="top")
        fig.text(0.08, my - 0.075, "\n".join(textwrap.wrap(label, 50)), fontsize=19, color=INK2, family=BODY_FONT, va="top", linespacing=1.4)
    fig.patches.append(FancyBboxPatch((0.08, 0.09), 0.84, 0.12, boxstyle="round,pad=0,rounding_size=0.015",
                                      transform=fig.transFigure, facecolor=BAND, edgecolor=BAND))
    fig.text(0.11, 0.165, "Código, evaluaciones y definiciones de KPIs", fontsize=20, color="white", fontweight="bold", family=BODY_FONT, va="center")
    fig.text(0.11, 0.125, "en el primer comentario.", fontsize=20, color="#c9d3e3", family=BODY_FONT, va="center")
    slides.append(fig)

    pdf_path = OUT_DIR / "carrusel_post1.pdf"
    with PdfPages(pdf_path) as pdf:
        for slide in slides:
            pdf.savefig(slide, facecolor=slide.get_facecolor())
    preview_dir = OUT_DIR / "preview"
    preview_dir.mkdir(exist_ok=True)
    for i, slide in enumerate(slides, start=1):
        slide.savefig(preview_dir / f"lamina_{i}.png", dpi=50, facecolor=slide.get_facecolor())
        plt.close(slide)
    print(f"PDF: {pdf_path} ({len(slides)} láminas)")
    print(f"Contención {pct(containment)} IC95% {pct(containment_ci[0])}–{pct(containment_ci[1])} · "
          f"Conversión {pct(conversion)} IC95% {pct(conversion_ci[0])}–{pct(conversion_ci[1])}")


if __name__ == "__main__":
    main()
