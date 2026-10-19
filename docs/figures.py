# -*- coding: utf-8 -*-
"""Figuras del informe y la presentación, generadas desde models/metrics.json."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "figures"
M = json.loads((ROOT / "models" / "metrics.json").read_text(encoding="utf-8"))

LEGIT, FRAUD, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
TEXT, TEXT2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#7b7a75", "#e8e7e2", "#fcfcfb"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": TEXT2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlesize": 11.5, "axes.titleweight": "bold",
    "axes.titlecolor": TEXT, "axes.titlelocation": "left", "axes.titlepad": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
    "grid.color": GRID, "grid.linewidth": 0.8, "figure.facecolor": "white", "axes.facecolor": "white",
    "legend.frameon": False, "savefig.dpi": 180, "savefig.bbox": "tight",
})


def pct(x, d=1):
    return f"{x * 100:.{d}f} %".replace(".", ",")


def es(n):
    return f"{n:,.0f}".replace(",", ".")


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name)
    plt.close(fig)


def bars(ax, x, y, color, **kw):
    return ax.bar(x, y, color=color, width=kw.pop("width", 0.6), edgecolor="white", linewidth=1, zorder=3, **kw)


def fig_tipo():
    d = sorted(M["dataset"]["by_type"], key=lambda r: -r["transacciones"])
    t = [r["type"] for r in d]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
    bars(ax[0], t, [r["transacciones"] / 1000 for r in d], LEGIT)
    ax[0].set_title("Volumen por tipo (miles de transacciones)")
    b = bars(ax[1], t, [r["tasa"] * 100 for r in d], FRAUD)
    ax[1].set_title("Tasa de fraude por tipo (%)")
    for rect, r in zip(b, d):
        if r["fraudes"]:
            ax[1].text(rect.get_x() + rect.get_width() / 2, rect.get_height() + .05,
                       f"{pct(r['tasa'], 2)}\n{es(r['fraudes'])} fraudes", ha="center", va="bottom", fontsize=8.5, color=TEXT2)
    ax[1].set_ylim(0, 4.3)
    for a in ax:
        a.tick_params(axis="x", labelsize=8.5)
    fig.tight_layout()
    save(fig, "tipo.png")


def fig_monto():
    h = M["dataset"]["amount_hist"]
    b = np.array(h["bins"])
    c = (b[:-1] + b[1:]) / 2
    w = (b[1] - b[0]) * 0.45
    fig, ax = plt.subplots(figsize=(10, 3.3))
    ax.bar(c - w / 2, np.array(h["legitima"]) * 100, width=w, color=LEGIT, label="Legítima", zorder=3)
    ax.bar(c + w / 2, np.array(h["fraude"]) * 100, width=w, color=FRAUD, label="Fraude", zorder=3)
    ax.set_xlim(2, 17)
    ax.set_title("Distribución de log(1 + monto) por clase (% de transacciones de cada clase)")
    ax.set_xlabel("log(1 + monto)")
    q = M["dataset"]["amount_quantiles"]
    ax.legend(loc="upper left")
    ax.text(0.99, 0.95, f"Mediana fraude: $ {es(q['fraude']['0.5'])}\nMediana legítima: $ {es(q['legitima']['0.5'])}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color=TEXT2)
    save(fig, "monto.png")


def fig_hora():
    d = M["dataset"]["by_hour"]
    fig, ax = plt.subplots(figsize=(10, 3.1))
    bars(ax, [r["hourOfDay"] for r in d], [r["tasa"] * 100 for r in d], FRAUD, width=0.7)
    ax.set_title("Tasa de fraude por hora del día (%)")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("hora")
    save(fig, "hora.png")


def fig_particion():
    d = M["dataset"]["by_day"]
    s = M["splits"]
    days = [r["day"] for r in d]
    fig, ax = plt.subplots(2, 1, figsize=(10, 4.4), sharex=True)
    ax[0].bar(days, [(r["transacciones"] - r["fraudes"]) / 1000 for r in d], color=LEGIT, width=.75, zorder=3)
    ax[0].set_title("Transacciones legítimas por día (miles)")
    ax[1].bar(days, [r["fraudes"] for r in d], color=FRAUD, width=.75, zorder=3)
    ax[1].set_title("Fraudes por día")
    colors = {"train": LEGIT, "validation": AQUA, "test": FRAUD}
    names = {"train": "Entrenamiento", "validation": "Validación", "test": "Prueba"}
    for r in s:
        a, b = (r["step_desde"] - 1) / 24 + .5, r["step_hasta"] / 24 + .5
        for k, a_ in enumerate(ax):
            a_.axvspan(a, b, color=colors[r["conjunto"]], alpha=.10, zorder=1)
        ax[0].text((a + b) / 2, 0.93, names[r["conjunto"]], transform=ax[0].get_xaxis_transform(),
                   ha="center", va="top", fontsize=9, color=TEXT, fontweight="bold")
    ax[1].set_xlabel("día de simulación")
    ax[1].set_xlim(.5, 31.5)
    fig.tight_layout()
    save(fig, "particion.png")


def fig_modelos():
    keys = ["logreg", "tree", "forest", "hgb"]
    names = ["Regresión\nLogística", "Árbol de\nDecisión", "Random\nForest", "Gradient\nBoosting"]
    a = [M["results"][k]["test"]["pr_auc"] for k in keys]
    b = [M["results"][k + "__sin_vaciado"]["test"]["pr_auc"] for k in keys]
    x = np.arange(len(keys))
    fig, ax = plt.subplots(figsize=(10, 3.4))
    r1 = bars(ax, x - .19, a, LEGIT, width=.36, label="Con todas las variables")
    r2 = bars(ax, x + .19, b, FRAUD, width=.36, label="Sin variables de vaciado")
    for rr in (r1, r2):
        for rect in rr:
            ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + .015, f"{rect.get_height():.3f}".replace(".", ","),
                    ha="center", fontsize=8.5, color=TEXT2)
    rule = M["results"]["rule"]["test"]["pr_auc"]
    ax.axhline(rule, color=MUTED, ls="--", lw=1, zorder=2, label=f"Regla base ({rule:.3f})".replace(".", ","))
    ax.set_xticks(x, names)
    ax.set_ylim(0, 1.32)
    ax.set_yticks([0, .2, .4, .6, .8, 1.0])
    ax.set_title("PR-AUC en prueba: con y sin las variables de vaciado de cuenta")
    ax.legend(loc="upper right", ncol=3)
    save(fig, "modelos.png")


def fig_confusion():
    c = M["results"][M["chosen"]]["test"]["confusion"]
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    ax.grid(False)
    cells = [[("Verdaderos\nnegativos", c["tn"], "#f0efec", TEXT2), ("Falsos\npositivos", c["fp"], "#fff4d6", "#9a6700")],
             [("Fraudes no\ndetectados", c["fn"], "#fdecea", "#c62828"), ("Fraudes\ndetectados", c["tp"], "#e6f4ea", "#1a7f37")]]
    for i in range(2):
        for j in range(2):
            lab, v, bg, fg = cells[i][j]
            ax.add_patch(FancyBboxPatch((j + .04, 1 - i + .04), .92, .92, boxstyle="round,pad=0,rounding_size=.06", fc=bg, ec="none"))
            ax.text(j + .5, 1 - i + .58, es(v), ha="center", va="center", fontsize=17, fontweight="bold", color=fg)
            ax.text(j + .5, 1 - i + .27, lab, ha="center", va="center", fontsize=8.5, color=fg)
    ax.set_xlim(0, 2); ax.set_ylim(0, 2)
    ax.set_xticks([.5, 1.5], ["Predicho: legítima", "Predicho: fraude"])
    ax.set_yticks([1.5, .5], ["Real:\nlegítima", "Real:\nfraude"])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(f"Matriz de confusión (prueba)")
    save(fig, "confusion.png")


def fig_umbral():
    tc = M["threshold_curve"]
    t = [d["t"] for d in tc]
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    ax.plot(t, [d["precision"] for d in tc], color=LEGIT, lw=2, label="Precisión")
    ax.plot(t, [d["recall"] for d in tc], color=FRAUD, lw=2, label="Recall")
    ax.plot(t, [d["f2"] for d in tc], color=AQUA, lw=2, ls="--", label="F2")
    ax.axvline(M["threshold"], color=TEXT, lw=1, ls=":")
    ax.text(M["threshold"] - .02, .865, f"umbral\n{M['threshold']:.3f}".replace(".", ","), ha="right", fontsize=8.5, color=TEXT2)
    ax.set_ylim(.85, 1.005)
    ax.set_xlabel("umbral de probabilidad")
    ax.set_title("Métricas según el umbral (validación)")
    ax.legend(loc="lower center", ncol=3)
    save(fig, "umbral.png")


def fig_importancia():
    imp = M["importance"][:8][::-1]
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    ax.grid(axis="x", color=GRID); ax.grid(axis="y", visible=False)
    ax.barh([d["feature"] for d in imp], [max(d["importance"], 1e-6) for d in imp], color=LEGIT, height=.6, zorder=3)
    ax.set_xscale("log")
    ax.set_title("Importancia por permutación (caída de PR-AUC)")
    ax.tick_params(axis="y", labelsize=8.5, colors=TEXT2)
    save(fig, "importancia.png")


def fig_arquitectura():
    fig, ax = plt.subplots(figsize=(10.5, 3.3))
    ax.axis("off"); ax.set_xlim(0, 10.5); ax.set_ylim(0, 3.3)
    boxes = [
        (0.1, "Fraud.csv", "1.362.621 filas\n11 columnas", "#f0efec"),
        (2.15, "Ingeniería de\nvariables", "features.py\n14 variables", "#e3eefb"),
        (4.2, "Pipeline\nscikit-learn", "RobustScaler + OHE\n+ HistGradientBoosting", "#e3eefb"),
        (6.25, "fraud_model\n.joblib", "pipeline + umbral\n+ metadatos", "#fdeee6"),
        (8.3, "API Flask", "POST /api/predict\nDashboard web", "#e6f4ea"),
    ]
    for x, title, sub, bg in boxes:
        ax.add_patch(FancyBboxPatch((x, 1.15), 1.9, 1.5, boxstyle="round,pad=0,rounding_size=.12", fc=bg, ec=GRID, lw=1))
        ax.text(x + .95, 2.17, title, ha="center", va="center", fontsize=10, fontweight="bold", color=TEXT)
        ax.text(x + .95, 1.5, sub, ha="center", va="center", fontsize=7.8, color=TEXT2)
    for x in (2.0, 4.05, 6.1, 8.15):
        ax.annotate("", xy=(x + .15, 1.9), xytext=(x, 1.9), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.4))
    ax.text(2.15, .55, "train.py: partición temporal → 4 algoritmos + regla base → selección por PR-AUC → umbral por F2",
            fontsize=8.8, color=TEXT2)
    ax.annotate("", xy=(6.25, .62), xytext=(5.95, .62), arrowprops=dict(arrowstyle="-", color=GRID))
    ax.text(0.1, 3.05, "Arquitectura de la solución", fontsize=11.5, fontweight="bold", color=TEXT)
    save(fig, "arquitectura.png")


def build_all():
    for f in (fig_tipo, fig_monto, fig_hora, fig_particion, fig_modelos, fig_confusion, fig_umbral,
              fig_importancia, fig_arquitectura):
        f()
    return sorted(p.name for p in FIG.glob("*.png"))


if __name__ == "__main__":
    print(build_all())
