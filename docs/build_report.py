# -*- coding: utf-8 -*-
"""Genera docs/Informe_TP_Fraude.pdf a partir de models/metrics.json y docs/figures/.

Uso:  python docs/build_report.py
"""
import json
import os
from datetime import date
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

import figures

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "Informe_TP_Fraude.pdf"
M = json.loads((ROOT / "models" / "metrics.json").read_text(encoding="utf-8"))

INTEGRANTES = ["Ezequiel Diaz Fernandez"]
MATERIA = "Trabajo Práctico Final"
INSTITUCION = "Universidad CAECE"
REPO = "https://github.com/fcaceres-create/caece_ezequiel"
APP_URL = "https://caece-aprendizaje-artificial-ezequiel.onrender.com"

# ---------- tipografía y estilos ----------
FONT_DIR = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Oblique", str(FONT_DIR / "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuMono", str(FONT_DIR / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique",
                              boldItalic="DejaVu-Bold")

INK, INK2, MUTED, LINE = colors.HexColor("#0b0b0b"), colors.HexColor("#52514e"), colors.HexColor("#7b7a75"), colors.HexColor("#e2e1dc")
BLUE, ORANGE, SOFT = colors.HexColor("#2a78d6"), colors.HexColor("#eb6834"), colors.HexColor("#f3f2ef")
BLUE_SOFT, WARN_SOFT = colors.HexColor("#e8f1fc"), colors.HexColor("#fff4d6")

ST = {
    "body": ParagraphStyle("body", fontName="DejaVu", fontSize=9.6, leading=14.2, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=16, leading=20, textColor=INK, spaceBefore=4, spaceAfter=10, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=11.5, leading=15, textColor=INK, spaceBefore=10, spaceAfter=5, keepWithNext=1),
    "bullet": ParagraphStyle("bullet", fontName="DejaVu", fontSize=9.6, leading=14, textColor=INK, leftIndent=14, bulletIndent=3, spaceAfter=2.5),
    "caption": ParagraphStyle("caption", fontName="DejaVu-Oblique", fontSize=8.2, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceBefore=3, spaceAfter=10),
    "cell": ParagraphStyle("cell", fontName="DejaVu", fontSize=8.3, leading=11, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="DejaVu-Bold", fontSize=8.3, leading=11, textColor=INK),
    "head": ParagraphStyle("head", fontName="DejaVu-Bold", fontSize=7.6, leading=10, textColor=MUTED),
    "box": ParagraphStyle("box", fontName="DejaVu", fontSize=9.4, leading=13.6, textColor=INK, alignment=TA_JUSTIFY),
    "code": ParagraphStyle("code", fontName="DejaVuMono", fontSize=7.8, leading=10.5, textColor=INK, backColor=SOFT,
                           borderPadding=7, spaceBefore=4, spaceAfter=10),
}


def num(x, d=0):
    s = f"{x:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def pct(x, d=2):
    return num(x * 100, d) + " %"


def P(text, style="body"):
    return Paragraph(text, ST[style])


def bullets(items):
    return [Paragraph(t, ST["bullet"], bulletText="•") for t in items]


def fig(name, width_cm, caption):
    path = DOCS / "figures" / name if (DOCS / "figures" / name).exists() else DOCS / "img" / name
    img = Image(str(path))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = width_cm * cm, width_cm * cm * ratio
    return KeepTogether([img, P(caption, "caption")])


def box(text, bg=BLUE_SOFT, edge=BLUE):
    t = Table([[P(text, "box")]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 2.5, edge),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return KeepTogether([t, Spacer(1, 8)])


def table(rows, widths, highlight=None, align_right_from=1):
    data = [[P(c, "head") for c in rows[0]]] + [[P(str(c), "cellb" if i == highlight else "cell") for c in r]
                                                 for i, r in enumerate(rows[1:], start=1)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    style = [("LINEBELOW", (0, 0), (-1, 0), 0.8, INK2), ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4.5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if highlight:
        style.append(("BACKGROUND", (0, highlight), (-1, highlight), BLUE_SOFT))
    t.setStyle(TableStyle(style))
    return KeepTogether([t, Spacer(1, 10)])


def on_page(canvas, doc):
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(2.3 * cm, 1.3 * cm, "Predicción de fraude en transacciones · " + MATERIA)
    canvas.drawRightString(A4[0] - 2.3 * cm, 1.3 * cm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(2.3 * cm, 1.7 * cm, A4[0] - 2.3 * cm, 1.7 * cm)
    canvas.restoreState()


def cover():
    d, r = M["dataset"], M["results"][M["chosen"]]["test"]
    s = []
    s.append(Spacer(1, 3.2 * cm))
    s.append(P(f'<font color="#7b7a75">{INSTITUCION.upper()} · {MATERIA.upper()}</font>', "head"))
    s.append(Spacer(1, 10))
    s.append(Paragraph("Predicción de fraude<br/>en transacciones", ParagraphStyle("t", fontName="DejaVu-Bold", fontSize=30, leading=36, textColor=INK)))
    s.append(Spacer(1, 12))
    s.append(Paragraph("Comprensión del negocio, preparación de datos, comparación de algoritmos, evaluación temporal y aplicación web para consumir el modelo.",
                       ParagraphStyle("st", fontName="DejaVu", fontSize=12, leading=17, textColor=INK2)))
    s.append(Spacer(1, 1.4 * cm))
    kpis = [[P("TRANSACCIONES", "head"), P("FRAUDES DETECTADOS (PRUEBA)", "head"), P("FALSOS POSITIVOS", "head")],
            [Paragraph(num(d["rows"]), ParagraphStyle("k", fontName="DejaVu-Bold", fontSize=18, leading=22)),
             Paragraph(f'{num(r["confusion"]["tp"])} / {num(r["confusion"]["tp"] + r["confusion"]["fn"])}', ParagraphStyle("k", fontName="DejaVu-Bold", fontSize=18, leading=22)),
             Paragraph(num(r["confusion"]["fp"]), ParagraphStyle("k", fontName="DejaVu-Bold", fontSize=18, leading=22))]]
    t = Table(kpis, colWidths=[5.0 * cm, 6.6 * cm, 4.8 * cm])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 2, ORANGE), ("TOPPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    s.append(t)
    s.append(Spacer(1, 4.5 * cm))
    meta = [["Autor" if len(INTEGRANTES) == 1 else "Integrantes", "<br/>".join(INTEGRANTES)], ["Modelo final", M["chosen_name"]],
            ["Aplicación", f'<link href="{APP_URL}" color="#2a78d6">{APP_URL}</link>'],
            ["Repositorio", f'<link href="{REPO}" color="#2a78d6">{REPO}</link>'],
            ["Fecha", date.today().strftime("%d/%m/%Y")]]
    t = Table([[P(a, "head"), P(b, "cell")] for a, b in meta], colWidths=[3.2 * cm, 13 * cm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    s.append(t)
    s.append(PageBreak())
    return s


def build():
    figures.build_all()
    d, smp, R = M["dataset"], M["dataset"]["sampling"], M["results"]
    ch, chn = M["chosen"], M["chosen_name"]
    T, TW = R[ch]["test"], R[ch]["test_window"]
    rule = R["rule"]["test"]
    sp = {s["conjunto"]: s for s in M["splits"]}
    hour_peak = max(M["dataset"]["by_hour"], key=lambda h: h["tasa"])
    qf, ql = d["amount_quantiles"]["fraude"], d["amount_quantiles"]["legitima"]
    s = cover()

    # ---------------- Resumen ----------------
    s += [P("Resumen ejecutivo", "h1"),
          P(f"El objetivo del trabajo es construir un modelo que estime si una transacción es fraudulenta (<i>isFraud</i>) a partir del "
            f"dataset <i>Fraud.csv</i> ({num(d['rows'])} transacciones simuladas en 743 horas, {num(d['frauds'])} fraudes). Se siguió la metodología "
            "CRISP-DM: comprensión del negocio, auditoría y análisis exploratorio de los datos, ingeniería de variables, validación temporal, "
            "comparación de cuatro algoritmos contra una regla base, análisis crítico de los resultados y despliegue en una aplicación web."),
          box(f"<b>Resultado.</b> El modelo elegido, <b>{chn}</b>, detecta en el período de prueba (últimos 8 días, nunca vistos durante el "
              f"entrenamiento) <b>{num(T['confusion']['tp'])} de {num(T['confusion']['tp'] + T['confusion']['fn'])} fraudes</b> (recall {pct(T['recall'])}) "
              f"con <b>{num(T['confusion']['fp'])} falsos positivos</b> sobre {num(T['confusion']['tn'] + T['confusion']['fp'])} operaciones legítimas, "
              f"y evita el {pct(T['fraud_amount_detected'] / T['fraud_amount_total'])} del monto defraudado. Sólo usa información disponible "
              "<i>antes</i> de autorizar la operación."),
          P("Hallazgos principales:", "body")]
    s += bullets([
        f"El fraude ocurre únicamente en <b>TRANSFER</b> y <b>CASH_OUT</b>, y en el {pct(d['drain']['fraude_que_vacia'], 1)} de los casos "
        f"<b>vacía exactamente la cuenta de origen</b>. Una regla basada sólo en ese patrón ya alcanza un recall de {pct(rule['recall'], 1)} con precisión "
        f"{pct(rule['precision'], 1)}; se usó como línea base que todo modelo debía superar.",
        f"El archivo provisto <b>no es una muestra uniforme</b>: contiene el tramo final del simulador más todos los fraudes anteriores. Los steps 1–{smp['legit_steps'][0] - 1} "
        f"sólo tienen fraudes. La tasa real en la ventana con ambas clases es {pct(smp['window_rate'])} (no {pct(d['fraud_rate'])}). Se controló que el modelo no "
        "aproveche este artefacto.",
        f"Random Forest y {chn} empataron en PR-AUC; se eligió {chn} porque es el más <b>robusto</b> cuando se le quitan las variables de vaciado "
        f"(PR-AUC {num(R[ch + '__sin_vaciado']['test']['pr_auc'], 4)} contra {num(R['forest__sin_vaciado']['test']['pr_auc'], 4)}), además de entrenar en "
        f"{num(R[ch]['fit_seconds'], 1)} s.",
        "Los resultados casi perfectos son razonables <b>para este simulador</b>, pero no deben extrapolarse a datos bancarios reales: allí el patrón no "
        "es tan nítido y habría que monitorear la deriva y reentrenar.",
        "El modelo se sirve mediante una <b>API REST en Flask</b> con un dashboard de resultados, una explicación del proceso y un simulador de transacciones.",
    ])
    s.append(PageBreak())

    # ---------------- 1. Negocio ----------------
    s += [P("1. Comprensión del negocio", "h1"),
          P("Una entidad que procesa pagos necesita decidir, al momento de recibir una operación, si la autoriza o la retiene para revisión. "
            "Los dos errores posibles tienen costos distintos:")]
    s += bullets([
        "<b>Falso negativo</b> (fraude no detectado): pérdida directa del monto, más costos de reclamo y exposición reputacional. Es el error más caro.",
        "<b>Falso positivo</b> (operación legítima retenida): costo de revisión manual y fricción con el cliente. Es tolerable en baja proporción.",
    ])
    s += [P("De esta asimetría se derivan tres decisiones técnicas que atraviesan el trabajo:"),
          *bullets([
              "La <b>accuracy no sirve</b> como métrica: con una tasa de fraude menor al 1 %, un modelo que nunca predice fraude tendría más de 99 % de accuracy.",
              "La métrica de comparación es <b>PR-AUC</b> (área bajo la curva precisión-recall), que se concentra en la clase minoritaria y no se infla con los "
              "verdaderos negativos como la ROC-AUC.",
              "El umbral de decisión se elige maximizando <b>F2</b>, que pondera el recall el doble que la precisión.",
              "El modelo sólo puede usar información <b>conocida antes de autorizar</b>: no se usan los saldos posteriores a la transacción.",
          ])]

    # ---------------- 2. Datos ----------------
    s += [P("2. Comprensión de los datos", "h1"),
          P(f"El archivo contiene {num(d['rows'])} filas y 11 columnas útiles: <i>step</i> (hora de simulación, 1 a 743), <i>type</i>, <i>amount</i>, "
            "identificadores de origen y destino, saldos antes y después para ambas cuentas, la etiqueta <i>isFraud</i> y la columna <i>isFlaggedFraud</i>, "
            f"que la consigna indica no utilizar. La auditoría estructural no encontró valores faltantes ({d['missing']}) ni filas duplicadas ({d['duplicates']})."),
          P("2.1 Tipo de transacción", "h2"),
          fig("tipo.png", 16.4, "Figura 1. Volumen y tasa de fraude por tipo de transacción."),
          P(f"El fraude aparece <b>sólo en TRANSFER y CASH_OUT</b>. Aun así se conservan todos los tipos: eliminarlos cambiaría el universo de decisión y el "
            "modelo debe saber reconocer como legítimas las operaciones de otros tipos."),
          P("2.2 Monto", "h2"),
          fig("monto.png", 16.4, "Figura 2. Distribución de log(1 + monto) por clase."),
          P(f"El monto es muy asimétrico. Los fraudes son sensiblemente mayores (mediana $ {num(qf['0.5'])} contra $ {num(ql['0.5'])} en legítimas; "
            f"percentil 99 de $ {num(qf['0.99'])}, el tope del simulador). Los valores extremos <b>no se eliminan</b>, porque son precisamente señal. Se usa "
            "la transformación logarítmica para reducir la asimetría."),
          P("2.3 Hora del día", "h2"),
          fig("hora.png", 16.4, "Figura 3. Tasa de fraude por hora (ventana con ambas clases)."),
          P(f"El fraude se distribuye de forma pareja a lo largo del día, mientras que el tráfico legítimo cae de madrugada. Por eso la tasa por hora llega "
            f"al {pct(hour_peak['tasa'], 1)} a las {hour_peak['hourOfDay']} h. La hora del día es una variable útil y se calcula como <i>(step − 1) mod 24</i>."),
          P("2.4 Saldos y el patrón de vaciado", "h2"),
          P(f"Los saldos en cero son frecuentes ({pct(d['zero_rates']['oldbalanceOrg'], 1)} de los saldos de origen previos), por lo que no se tratan como faltantes. "
            f"El hallazgo más relevante es que el <b>{pct(d['drain']['fraude_que_vacia'], 1)} de los fraudes extrae exactamente todo el saldo disponible</b> de la cuenta de origen "
            f"(<i>amount = oldbalanceOrg</i>). De las {num(d['drain']['n_vacia'])} operaciones con ese comportamiento, el {pct(d['drain']['p_fraude_si_vacia'])} son fraude. "
            "Es coherente con el negocio (quien toma control de una cuenta intenta vaciarla), pero en datos reales sería mucho menos nítido: es una "
            "característica del simulador PaySim con que se generó el dataset."),
          P("2.5 Hallazgo de calidad: muestreo no uniforme", "h2"),
          fig("particion.png", 16.4, "Figura 4. Legítimas y fraudes por día, con los períodos de entrenamiento, validación y prueba."),
          P(f"La columna de índice exportada (<i>Unnamed: 0</i>) revela que el archivo es el <b>tramo final</b> de una simulación más grande, al que se le agregaron "
            f"<b>todos los fraudes</b> previos. Por eso las transacciones legítimas sólo existen entre los steps {smp['legit_steps'][0]} y {smp['legit_steps'][1]}: los "
            f"steps anteriores contienen {num(smp['fraud_only_before'])} fraudes y ninguna legítima, y los posteriores, {num(smp['fraud_only_after'])} fraudes. La tasa global "
            f"de {pct(d['fraud_rate'])} está inflada: dentro de la ventana con ambas clases es <b>{pct(smp['window_rate'])}</b>."),
          box(f"<b>Cómo se trató.</b> (1) No se usan <i>step</i> ni el día como variables, para que el modelo no aprenda “temprano = fraude”. "
              f"(2) Se verificó que esos fraudes son representativos: vacían la cuenta en un {pct(smp['drain_before'], 1)} de los casos (contra {pct(smp['drain_window'], 1)} en la ventana) "
              "y tienen la misma distribución horaria; por eso se conservan para entrenar. (3) La evaluación se informa también restringida a la ventana con ambas clases. "
              f"(4) Un modelo entrenado sin esos fraudes logra PR-AUC {num(R[ch + '__solo_ventana']['test']['pr_auc'], 4)}: el resultado no depende del artefacto.",
              WARN_SOFT, colors.HexColor("#9a6700")),
          P("2.6 Identificadores", "h2"),
          P("<i>nameOrig</i> tiene prácticamente un valor distinto por fila, y <i>nameDest</i> más del 90 %. Codificarlos llevaría a memorizar cuentas "
            "en lugar de aprender comportamientos. Se descartan y sólo se conserva el prefijo del destino (C = cliente, M = comercio)."),
          ]

    # ---------------- 3. Preparación ----------------
    feats = [
        ["Variable", "Definición", "Justificación"],
        ["type", "Tipo de operación (One-Hot)", "El fraude sólo ocurre en dos tipos"],
        ["destPrefix", "Prefijo del destinatario C/M (One-Hot)", "Los comercios (M) nunca reciben fraude"],
        ["amount, logAmount", "Monto y log(1 + monto)", "Los fraudes son de mayor monto; el log reduce la asimetría"],
        ["hourOfDay, isNight", "Hora del día y franja 0–5 h", "La tasa de fraude es mucho mayor de madrugada"],
        ["oldbalanceOrg, oldbalanceDest", "Saldos previos", "Conocidos antes de autorizar"],
        ["origZeroBefore, destZeroBefore", "Indicadores de saldo previo cero", "Los ceros son frecuentes y tienen significado propio"],
        ["amountToOrigBalance, amountToDestBalance", "Monto / (saldo + 1)", "Escala el monto respecto de la capacidad de la cuenta"],
        ["amountMinusOrigBalance", "Monto − saldo de origen", "Distancia al vaciado total"],
        ["drainsOrigin", "1 si el monto = saldo de origen (> 0)", f"Patrón presente en el {pct(d['drain']['fraude_que_vacia'], 1)} de los fraudes"],
    ]
    s += [P("3. Preparación de los datos", "h1"),
          P("Se reutilizó la ingeniería de variables de la etapa de preparación (notebook incluido en el repositorio). Se agregaron las dos variables de vaciado y se "
            "separaron dos conjuntos de variables. El escenario <b>A</b> (desplegado) usa sólo información previa a la autorización. El escenario <b>B</b> agrega "
            "saldos posteriores y errores contables y se evaluó sólo como control de fuga de información. Todas las transformaciones están en "
            "<i>src/features.py</i>, que comparten el entrenamiento y la aplicación web."),
          table(feats, [5.0, 5.4, 6.0]),
          P("Se excluyeron <i>isFlaggedFraud</i> (indicación de la consigna), <i>Unnamed: 0</i> (índice), los identificadores crudos, <i>step</i> y <i>day</i> (en una "
            "partición temporal el modelo vería días que nunca existieron en el entrenamiento, además del artefacto de muestreo) y los saldos posteriores. "
            "Las variables numéricas se escalan con <b>RobustScaler</b> (mediana y rango intercuartílico), menos sensible a las colas extremas de montos y saldos "
            "que la estandarización clásica. Las categóricas se codifican con <b>One-Hot Encoding</b>. El preprocesamiento vive dentro de un <i>Pipeline</i> de "
            "scikit-learn, que se ajusta sólo con los datos de entrenamiento.")]

    # ---------------- 4. Validación ----------------
    split_rows = [["Conjunto", "Steps", "Filas", "Fraudes", "Tasa", "Uso"]]
    usos = {"train": "Ajuste de modelos", "validation": "Selección de modelo y umbral", "test": "Evaluación final (una vez)"}
    for k in ("train", "validation", "test"):
        x = sp[k]
        split_rows.append([k, f"{x['step_desde']}–{x['step_hasta']}", num(x["filas"]), num(x["fraudes"]), pct(x["tasa"]), usos[k]])
    s += [P("4. Estrategia de validación", "h1"),
          P("Se mantuvo la <b>partición temporal</b> definida en la etapa de preparación. Una partición aleatoria mezclaría pasado y futuro y daría una estimación "
            "optimista. En producción el modelo siempre se entrena con datos anteriores a los que va a evaluar."),
          table(split_rows, [2.4, 2.0, 2.4, 2.0, 2.0, 5.6]),
          P("El desbalance se trató con <b>ponderación de clases</b> (<i>class_weight</i>) en lugar de sobremuestreo (SMOTE) o submuestreo. La ponderación no "
            "fabrica ni descarta observaciones y no altera los conjuntos de validación y prueba. Además, con más de 4.500 fraudes en entrenamiento no hace falta "
            "generar ejemplos sintéticos. El conjunto de prueba se usó <b>una sola vez</b>, después de fijar el modelo y el umbral.")]

    # ---------------- 5. Modelado ----------------
    algos = [["Algoritmo", "Por qué se incluye", "Configuración"],
             ["Regla base", "Referencia sin aprendizaje: si un modelo no la supera, no se justifica su complejidad", "drainsOrigin = 1 → fraude"],
             ["Regresión Logística", "Lineal e interpretable; mide cuánto se logra con relaciones simples", "class_weight balanced, C = 1"],
             ["Árbol de Decisión", "Reglas no lineales explicables al negocio", "profundidad 8, hoja mínima 20, balanced"],
             ["Random Forest", "Bagging de árboles: reduce la varianza y es robusto a outliers", "150 árboles, profundidad 14, balanced_subsample"],
             ["Gradient Boosting (HistGB)", "Boosting: corrige errores en forma secuencial; muy eficiente en tablas grandes", "hasta 300 iteraciones, early stopping, balanced"]]
    s += [P("5. Modelado", "h1"),
          P("Se compararon cuatro algoritmos de familias distintas, de menor a mayor complejidad, para poder justificar la elección por desempeño y no por "
            "costumbre. Todos se entrenaron con el mismo pipeline de preprocesamiento y el mismo conjunto de variables."),
          table(algos, [3.6, 7.6, 5.2]),
          P("Para cada modelo se eligió en validación el umbral que maximiza F2. Con ese umbral fijo se midió el desempeño en prueba. Además, cada algoritmo se "
            "reentrenó <b>sin las variables de vaciado</b> (ablación) para medir cuánto depende de ese único patrón: es la evidencia de robustez que se usó como "
            "criterio de desempate.")]

    # ---------------- 6. Evaluación ----------------
    rows = [["Modelo", "PR-AUC valid.", "PR-AUC prueba", "Recall", "Precisión", "F2", "FN", "FP", "PR-AUC sin vaciado"]]
    keys = ["rule", "logreg", "tree", "forest", "hgb"]
    for k in keys:
        x = R[k]
        abl = R.get(k + "__sin_vaciado")
        rows.append([x["name"].replace(" (vacía la cuenta)", ""), num(x["valid"]["pr_auc"], 4), num(x["test"]["pr_auc"], 4), pct(x["test"]["recall"]),
                     pct(x["test"]["precision"]), num(x["test"]["f2"], 4), num(x["test"]["confusion"]["fn"]), num(x["test"]["confusion"]["fp"]),
                     num(abl["test"]["pr_auc"], 4) if abl else "—"])
    s += [P("6. Evaluación y selección", "h1"),
          P("6.1 Comparación de modelos", "h2"),
          table(rows, [3.1, 1.65, 1.65, 1.85, 1.95, 1.5, 0.9, 0.9, 1.85], highlight=keys.index(ch) + 1),
          P("FN = fraudes no detectados; FP = operaciones legítimas marcadas como fraude. Métricas de prueba con el umbral elegido en validación.", "caption"),
          fig("modelos.png", 16.4, "Figura 5. Robustez: PR-AUC en prueba con y sin las variables de vaciado."),
          P(f"<b>Regla de selección.</b> (1) Mayor PR-AUC en validación. (2) Ante empate, mayor PR-AUC en la ablación sin variables de vaciado (robustez). "
            f"(3) Ante nuevo empate, el modelo más simple. Random Forest y {chn} empataron en el primer criterio. {chn} se impuso en el segundo: sin las variables "
            f"de vaciado mantiene PR-AUC {num(R[ch + '__sin_vaciado']['valid']['pr_auc'], 4)} en validación, frente a {num(R['forest__sin_vaciado']['valid']['pr_auc'], 4)} de Random Forest. "
            f"En cambio, la Regresión Logística ({num(R['logreg__sin_vaciado']['valid']['pr_auc'], 3)}) y el Árbol ({num(R['tree__sin_vaciado']['valid']['pr_auc'], 3)}) "
            "colapsan, porque dependen casi por completo de esa señal. Es decir, el boosting aprende el patrón de vaciado a partir del monto y el saldo aunque no se le dé "
            f"explícitamente. Como ventaja operativa adicional, entrena en {num(R[ch]['fit_seconds'], 1)} s y su artefacto pesa {num((ROOT / 'models' / 'fraud_model.joblib').stat().st_size / 1024)} KB."),
          P("6.2 Umbral y matriz de confusión", "h2")]
    t2 = Table([[Image(str(DOCS / "figures" / "umbral.png"), 8.4 * cm, 8.4 * cm * 0.66), Image(str(DOCS / "figures" / "confusion.png"), 7.2 * cm, 7.2 * cm * 0.80)]],
               colWidths=[8.6 * cm, 7.8 * cm])
    s += [t2, P("Figura 6. Métricas según el umbral (validación) y matriz de confusión del modelo elegido (prueba).", "caption"),
          P(f"El umbral que maximiza F2 en validación es <b>{num(M['threshold'], 3)}</b>. La meseta de la curva muestra que el resultado no es sensible al valor "
            f"exacto. En prueba, el modelo no genera falsos positivos y deja pasar {T['confusion']['fn']} fraudes. Ninguno de ellos vacía la cuenta de origen (mediana "
            f"de $ {num(M['missed_profile']['monto_mediano'])}): son los casos que escapan al patrón dominante, coherente con lo esperado."),
          P("6.3 Importancia de variables", "h2"),
          fig("importancia.png", 11.5, "Figura 7. Importancia por permutación: caída de PR-AUC al desordenar cada variable (escala logarítmica)."),
          P("<i>drainsOrigin</i> domina con amplitud. Le siguen la relación monto/saldo del destino, el tipo de operación y los saldos de origen. La lectura es "
            "consistente con el análisis exploratorio, lo que da confianza en que el modelo aprende relaciones con sentido de negocio y no ruido."),
          P("6.4 Controles adicionales", "h2")]
    ctrl = [["Control", "Resultado", "Lectura"],
            ["Prueba sólo en la ventana con ambas clases", f"{num(TW['confusion']['tp'])}/{num(TW['confusion']['tp'] + TW['confusion']['fn'])} detectados, {TW['confusion']['fp']} FP",
             "El desempeño no se debe a los fraudes aislados del final"],
            ["Entrenar sin el período sólo-fraude", f"PR-AUC {num(R[ch + '__solo_ventana']['test']['pr_auc'], 4)} ({R[ch + '__solo_ventana']['train_frauds']} fraudes)",
             "El artefacto de muestreo no es la fuente del resultado"],
            ["Escenario B (con saldos posteriores)", f"PR-AUC {num(R[ch + '__B']['test']['pr_auc'], 4)}, {R[ch + '__B']['test']['confusion']['fn']} FN",
             "No mejora al A: no hay fuga por información posterior"],
            ["Regla base", f"Recall {pct(rule['recall'], 1)}, {rule['confusion']['fn']} FN", f"El modelo recupera {rule['confusion']['fn'] - T['confusion']['fn']} fraudes adicionales"]]
    s += [table(ctrl, [5.2, 5.0, 6.2])]

    # ---------------- 7. Razonabilidad ----------------
    s += [P("7. Razonabilidad de los resultados y limitaciones", "h1"),
          P("Una PR-AUC de 1,000 debe despertar sospechas antes que celebración. Por eso se buscó activamente una explicación:"),
          *bullets([
              "<b>La causa es identificable y tiene sentido de negocio.</b> El fraude simulado vacía la cuenta de origen y casi ninguna operación legítima lo hace. "
              "Ese patrón solo explica el 97 % del resultado, como muestra la regla base.",
              "<b>No hay fuga de información.</b> El modelo desplegado no usa saldos posteriores, identificadores ni el step. El escenario con saldos posteriores no "
              "rinde más, y los controles sobre el artefacto de muestreo no cambian la conclusión.",
              "<b>La validación es temporal.</b> El modelo se evalúa sobre días futuros que nunca vio.",
          ]),
          P("Limitaciones:", "body"),
          *bullets([
              "Los datos son <b>sintéticos</b>. En un entorno bancario real los defraudadores adaptan su comportamiento, y no cabe esperar métricas de este nivel. "
              "El valor del trabajo está en la metodología, que es trasladable.",
              "El archivo es una muestra no uniforme, por lo que la prevalencia y la deriva temporal observadas están parcialmente distorsionadas.",
              "No se dispone del costo real de cada error. Si el negocio lo cuantifica, el umbral debería elegirse minimizando el costo esperado en lugar de maximizar F2.",
              "Sin historial por cliente no se pueden construir variables de comportamiento (velocidad de operaciones, montos habituales), que en la práctica son las "
              "más valiosas.",
          ])]

    # ---------------- 8. Aplicación ----------------
    s += [P("8. Aplicación web", "h1"),
          fig("arquitectura.png", 16.4, "Figura 8. Arquitectura de la solución."),
          P("El pipeline completo (preprocesamiento, modelo y umbral) se serializa con <i>joblib</i> y lo carga una aplicación <b>Flask</b>, publicada en "
            f'<link href="{APP_URL}" color="#2a78d6">{APP_URL}</link> (Render, servidor gunicorn). Ofrece:'),
          *bullets([
              "<b>Resultados</b>: indicadores clave, comparación de modelos, robustez, matriz de confusión, umbral e importancia de variables.",
              "<b>Proceso</b>: recorrido CRISP-DM con los gráficos exploratorios interactivos y las decisiones tomadas.",
              "<b>Simulador</b>: formulario que consulta la API con una transacción (o con ejemplos reales del período de prueba) y muestra la probabilidad, la "
              "decisión sugerida y las señales que la contextualizan.",
              "<b>API REST</b>: <i>POST /api/predict</i>, <i>GET /api/metrics</i> y <i>GET /api/health</i>, con validación de entradas.",
          ]),
          fig("app_resultados.png", 15.5, "Figura 9. Página de resultados."),
          fig("app_simulador.png", 15.5, "Figura 10. Simulador: un fraude real de $ 10 M que no vacía la cuenta y el modelo detecta igual."),
          P("Ejemplo de consumo de la API:", "body"),
          Paragraph('curl -X POST http://localhost:5000/api/predict -H "Content-Type: application/json" \\<br/>'
                    '&nbsp;&nbsp;-d \'{"type":"TRANSFER","amount":181000,"oldbalanceOrg":181000,"oldbalanceDest":0,"hourOfDay":3,"destPrefix":"C"}\'<br/><br/>'
                    '{"probabilidad": 0.9999, "umbral": %s, "es_fraude": true, "decision": "BLOQUEAR / REVISAR", "senales": [...]}' % f"{M['threshold']:.3f}",
                    ST["code"])]

    # ---------------- 9. Conclusiones ----------------
    s += [P("9. Conclusiones", "h1")]
    s += bullets([
        f"Se construyó un modelo de <b>{chn}</b> que, con información disponible antes de autorizar, detecta el {pct(T['recall'])} de los fraudes del período "
        "de prueba sin bloquear operaciones legítimas.",
        "La elección del algoritmo se basó en tres criterios explícitos: desempeño (PR-AUC), robustez (ablación) y simplicidad. El umbral se fijó por F2, "
        "acorde al mayor costo del fraude no detectado.",
        "El análisis crítico permitió detectar dos características del dataset que condicionan la lectura de los resultados: el patrón de vaciado de cuenta "
        "y el muestreo no uniforme. Ambas se cuantificaron y se controlaron.",
        "La solución es reproducible de punta a punta (<i>src/train.py</i>) y está disponible como aplicación web y API.",
    ])
    s += [P("Trabajo futuro", "h2")]
    s += bullets([
        "Definir con el negocio el costo de cada tipo de error y optimizar el umbral por costo esperado.",
        "Incorporar variables de comportamiento por cuenta (frecuencia, montos habituales, antigüedad) con datos reales.",
        "Monitorear la deriva (tasa de alertas, distribución de scores) y reentrenar periódicamente.",
        "Agregar explicaciones por predicción (por ejemplo, valores SHAP) para los analistas que revisan las alertas.",
    ])

    # ---------------- Anexo ----------------
    s += [P("Anexo A. Reproducibilidad", "h1"),
          P(f'Código fuente: <link href="{REPO}" color="#2a78d6">{REPO}</link>. El dataset no se incluye en el repositorio por su tamaño (120 MB); '
            "se descarga desde el enlace de la consigna y se guarda como <i>data/Fraud.csv</i>."),
          Paragraph("pip install -r requirements.txt<br/>"
                    "python src/train.py            # entrena, compara y guarda models/<br/>"
                    "python app/app.py              # http://127.0.0.1:5000<br/>"
                    "python docs/build_report.py    # regenera este informe<br/>"
                    "python docs/build_slides.py    # regenera la presentación", ST["code"]),
          table([["Ruta", "Contenido"],
                 ["notebooks/", "Etapa de preparación de datos (auditoría, EDA, variables, partición)"],
                 ["src/features.py", "Ingeniería de variables compartida por entrenamiento y app"],
                 ["src/train.py", "Partición temporal, entrenamiento, comparación, selección, métricas"],
                 ["models/", "fraud_model.joblib (pipeline + umbral) y metrics.json (resultados)"],
                 ["app/", "Aplicación Flask: API, dashboard, proceso y simulador"],
                 ["docs/", "Informe PDF, presentación HTML, figuras y scripts que los generan"]], [4.2, 12.2]),
          P(f"Semilla aleatoria: 42. Entorno: Python, scikit-learn, pandas, Flask. Métricas generadas el {M['generated']}.", "caption")]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm, topMargin=2.0 * cm, bottomMargin=2.2 * cm,
                            title="Predicción de fraude en transacciones", author=", ".join(INTEGRANTES), subject=MATERIA)
    doc.build(s, onFirstPage=on_page, onLaterPages=on_page)
    print("PDF:", OUT, f"{os.path.getsize(OUT) / 1024:.0f} KB")


if __name__ == "__main__":
    build()
