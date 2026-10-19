# -*- coding: utf-8 -*-
"""Aplicación web: dashboard de resultados, explicación del proceso y simulador de transacciones.

Uso:  python app/app.py         -> http://127.0.0.1:5000
API:  POST /api/predict  (JSON)  ·  GET /api/metrics  ·  GET /api/health
"""
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from features import TRANSACTION_TYPES, add_transaction_features  # noqa: E402

app = Flask(__name__)


@app.template_filter("es")
def es_number(value):
    """Formato numérico argentino: '1,234.5' -> '1.234,5'."""
    return str(value).replace(",", "_").replace(".", ",").replace("_", ".")

BUNDLE = joblib.load(ROOT / "models" / "fraud_model.joblib")
METRICS = json.loads((ROOT / "models" / "metrics.json").read_text(encoding="utf-8"))
PIPELINE, THRESHOLD, FEATURES = BUNDLE["pipeline"], BUNDLE["threshold"], BUNDLE["features"]

REQUIRED = {"type": str, "amount": float, "oldbalanceOrg": float, "oldbalanceDest": float}


def parse_transaction(payload):
    """Valida el JSON de entrada y devuelve (transacción, errores)."""
    errors, tx = [], {}
    for field, cast in REQUIRED.items():
        if payload.get(field) in (None, ""):
            errors.append(f"Falta el campo '{field}'")
            continue
        try:
            tx[field] = cast(payload[field])
        except (TypeError, ValueError):
            errors.append(f"'{field}' debe ser {'numérico' if cast is float else 'texto'}")
    if tx.get("type") not in TRANSACTION_TYPES:
        errors.append(f"'type' debe ser uno de {', '.join(TRANSACTION_TYPES)}")
    for f in ("amount", "oldbalanceOrg", "oldbalanceDest"):
        if f in tx and tx[f] < 0:
            errors.append(f"'{f}' no puede ser negativo")
    try:
        hour = int(payload.get("hourOfDay", 12))
        if not 0 <= hour <= 23:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("'hourOfDay' debe ser un entero entre 0 y 23")
        hour = 12
    dest = str(payload.get("destPrefix", "M" if tx.get("type") == "PAYMENT" else "C")).upper()[:1]
    if dest not in ("C", "M"):
        errors.append("'destPrefix' debe ser C (cliente) o M (comercio)")
    tx.update({"step": hour + 1, "nameDest": dest + "0", "destPrefix": dest})
    return tx, errors


def explain(row):
    """Señales legibles que acompañan la probabilidad (no son la salida del modelo, la contextualizan)."""
    signals = []
    if row.drainsOrigin:
        pct = METRICS["dataset"]["drain"]["fraude_que_vacia"] * 100
        signals.append(("alto", "La operación vacía exactamente el saldo de la cuenta de origen: "
                                f"patrón presente en el {pct:.1f} % de los fraudes históricos.".replace(".", ",", 1)))
    if row.type in ("TRANSFER", "CASH_OUT"):
        signals.append(("medio", f"{row.type} es uno de los dos únicos tipos con fraude registrado."))
    else:
        signals.append(("bajo", f"No se registraron fraudes de tipo {row.type} en los datos."))
    if row.amount > 1_000_000:
        q = METRICS["dataset"]["amount_quantiles"]
        ratio = q["fraude"]["0.5"] / q["legitima"]["0.5"]
        signals.append(("medio", f"Monto superior a 1 millón (la mediana de los fraudes es {ratio:.0f}x la legítima)."))
    if row.oldbalanceOrg == 0:
        signals.append(("bajo", "La cuenta de origen no informa saldo previo."))
    if row.isNight:
        peak = max(h["tasa"] for h in METRICS["dataset"]["by_hour"]) * 100
        signals.append(("medio", "Operación de madrugada (0–5 h): con poco tráfico legítimo, la tasa de fraude "
                                 f"por hora llega al {peak:.0f} % en el histórico."))
    return [{"nivel": n, "texto": t} for n, t in signals]


@app.route("/")
def index():
    return render_template("index.html", m=METRICS, page="resultados")


@app.route("/proceso")
def proceso():
    return render_template("proceso.html", m=METRICS, page="proceso")


@app.route("/simulador")
def simulador():
    return render_template("simulador.html", m=METRICS, page="simulador", types=TRANSACTION_TYPES)


@app.get("/api/health")
def health():
    return jsonify(status="ok", model=BUNDLE["model_name"], threshold=THRESHOLD)


@app.get("/api/metrics")
def metrics():
    return jsonify(METRICS)


@app.post("/api/predict")
def predict():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Se espera un cuerpo JSON"), 400
    tx, errors = parse_transaction(payload)
    if errors:
        return jsonify(errors=errors), 422
    # Los saldos posteriores no se usan en el modelo (escenario pre-autorización); se completan neutros
    frame = pd.DataFrame([{**tx, "newbalanceOrig": 0.0, "newbalanceDest": 0.0}])
    row = add_transaction_features(frame)
    proba = float(PIPELINE.predict_proba(row[FEATURES])[0, 1])
    r = row.iloc[0]
    return jsonify(
        probabilidad=proba,
        umbral=THRESHOLD,
        es_fraude=proba >= THRESHOLD,
        decision="BLOQUEAR / REVISAR" if proba >= THRESHOLD else "APROBAR",
        modelo=BUNDLE["model_name"],
        senales=explain(r),
    )


if __name__ == "__main__":
    app.run(debug=False, port=5000)
