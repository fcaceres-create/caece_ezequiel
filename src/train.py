# -*- coding: utf-8 -*-
"""Entrenamiento, comparación y selección del modelo de fraude.

Uso:  python src/train.py [ruta/a/Fraud.csv]

Genera:
  models/fraud_model.joblib  -> pipeline elegido + umbral + metadatos (lo consume la app web)
  models/metrics.json        -> resultados, curvas y datos del análisis exploratorio (dashboard, informe)
"""
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, fbeta_score,
                             precision_recall_curve, precision_score, recall_score,
                             roc_auc_score, roc_curve)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import (CATEGORICAL, FEATURES_NO_DRAIN, FEATURES_POST, FEATURES_PRE, TARGET,
                      TRAIN_MAX_STEP, VALID_MAX_STEP, add_transaction_features, temporal_split)

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "Fraud.csv"
MODELS = ROOT / "models"
SEED = 42
# Orden de simplicidad: ante empate se prefiere el modelo más simple de explicar y operar
MODEL_ORDER = ["logreg", "tree", "forest", "hgb"]
MODEL_NAMES = {
    "rule": "Regla base (vacía la cuenta)",
    "logreg": "Regresión Logística",
    "tree": "Árbol de Decisión",
    "forest": "Random Forest",
    "hgb": "Gradient Boosting (HistGB)",
}


def make_estimator(key):
    if key == "logreg":
        return LogisticRegression(class_weight="balanced", max_iter=3000, C=1.0)
    if key == "tree":
        return DecisionTreeClassifier(class_weight="balanced", max_depth=8, min_samples_leaf=20, random_state=SEED)
    if key == "forest":
        return RandomForestClassifier(n_estimators=150, max_depth=14, min_samples_leaf=5,
                                      class_weight="balanced_subsample", n_jobs=-1, random_state=SEED)
    if key == "hgb":
        return HistGradientBoostingClassifier(class_weight="balanced", learning_rate=0.1, max_iter=300,
                                              early_stopping=True, random_state=SEED)
    raise ValueError(key)


def make_pipeline(key, features):
    numeric = [c for c in features if c not in CATEGORICAL]
    pre = ColumnTransformer([
        ("numeric", RobustScaler(), numeric),
        ("categorical", OneHotEncoder(handle_unknown="ignore"), [c for c in features if c in CATEGORICAL]),
    ])
    return Pipeline([("prep", pre), ("model", make_estimator(key))])


def best_threshold(y, scores):
    """Umbral que maximiza F2 (el recall pesa el doble que la precisión: un fraude no detectado cuesta más)."""
    prec, rec, thr = precision_recall_curve(y, scores)
    f2 = (5 * prec * rec) / np.clip(4 * prec + rec, 1e-12, None)
    i = int(np.nanargmax(f2[:-1]))
    return float(thr[i])


def evaluate(y, scores, thr, amount=None):
    pred = (scores >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    out = {
        "pr_auc": float(average_precision_score(y, scores)),
        "roc_auc": float(roc_auc_score(y, scores)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred)),
        "f1": float(fbeta_score(y, pred, beta=1)),
        "f2": float(fbeta_score(y, pred, beta=2)),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "threshold": float(thr),
    }
    if amount is not None:
        fraud = y == 1
        out["fraud_amount_total"] = float(amount[fraud].sum())
        out["fraud_amount_detected"] = float(amount[fraud & (pred == 1)].sum())
        out["fraud_amount_missed"] = float(amount[fraud & (pred == 0)].sum())
    return out


def downsample_curve(x, y, n=150):
    idx = np.unique(np.linspace(0, len(x) - 1, min(n, len(x))).astype(int))
    return [[round(float(x[i]), 5), round(float(y[i]), 5)] for i in idx]


def legit_window(df):
    """Rango de steps con transacciones legítimas: fuera de él el archivo provisto sólo contiene fraudes."""
    legit_steps = df.loc[df[TARGET].eq(0), "step"]
    return int(legit_steps.min()), int(legit_steps.max())


def eda_summary(df):
    """Datos agregados para el dashboard y el informe (no se exportan filas individuales salvo ejemplos)."""
    lo, hi = legit_window(df)
    window = df[df.step.between(lo, hi)]
    by_type = df.groupby("type").agg(transacciones=(TARGET, "size"), fraudes=(TARGET, "sum"),
                                     tasa=(TARGET, "mean"), monto_mediano=("amount", "median")).reset_index()
    # La tasa por hora se calcula en la ventana con ambas clases para no inflarla con el período sólo-fraude
    by_hour = window.groupby("hourOfDay").agg(transacciones=(TARGET, "size"), fraudes=(TARGET, "sum"),
                                          tasa=(TARGET, "mean")).reset_index()
    by_day = df.groupby("day").agg(transacciones=(TARGET, "size"), fraudes=(TARGET, "sum"),
                                   tasa=(TARGET, "mean")).reset_index()
    bins = np.linspace(0, 17, 35)
    hist = {}
    for label, cls in (("legitima", 0), ("fraude", 1)):
        counts, _ = np.histogram(df.loc[df[TARGET].eq(cls), "logAmount"], bins=bins)
        hist[label] = (counts / counts.sum()).round(5).tolist()
    quant = df.groupby(TARGET).amount.quantile([.5, .9, .99]).unstack()
    risky = df[df.type.isin(["TRANSFER", "CASH_OUT"])]
    drain = {
        "fraude_que_vacia": float(df.loc[df[TARGET].eq(1), "drainsOrigin"].mean()),
        "legit_riesgo_que_vacia": float(risky.loc[risky[TARGET].eq(0), "drainsOrigin"].mean()),
        "p_fraude_si_vacia": float(df.loc[df.drainsOrigin.eq(1), TARGET].mean()),
        "n_vacia": int(df.drainsOrigin.sum()),
    }
    sampling = {
        "legit_steps": [lo, hi],
        "fraud_only_before": int(df.step.lt(lo).sum()),
        "fraud_only_after": int(df.step.gt(hi).sum()),
        "window_rows": int(len(window)), "window_frauds": int(window[TARGET].sum()),
        "window_rate": float(window[TARGET].mean()),
        "drain_before": float(df.loc[df.step.lt(lo) & df[TARGET].eq(1), "drainsOrigin"].mean()),
        "drain_window": float(window.loc[window[TARGET].eq(1), "drainsOrigin"].mean()),
    }
    return {
        "rows": int(len(df)), "frauds": int(df[TARGET].sum()), "fraud_rate": float(df[TARGET].mean()),
        "sampling": sampling,
        "steps": [int(df.step.min()), int(df.step.max())], "duplicates": int(df.duplicated().sum()),
        "missing": int(df.isna().sum().sum()),
        "by_type": by_type.to_dict(orient="records"),
        "by_hour": by_hour.to_dict(orient="records"),
        "by_day": by_day.to_dict(orient="records"),
        "amount_hist": {"bins": bins.round(3).tolist(), **hist},
        "amount_quantiles": {("fraude" if k == 1 else "legitima"): {str(q): float(v) for q, v in row.items()}
                             for k, row in quant.iterrows()},
        "zero_rates": {c: float(df[c].eq(0).mean()) for c in
                       ["oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"]},
        "drain": drain,
    }


def main():
    t0 = time.time()
    print(f"Leyendo {DATA} ...")
    raw = pd.read_csv(DATA)
    df = add_transaction_features(raw)
    train, valid, test = temporal_split(df)
    y_tr, y_va, y_te = train[TARGET].values, valid[TARGET].values, test[TARGET].values
    # Prueba "realista": sólo los steps donde conviven ambas clases (excluye el tramo final sólo-fraude)
    in_window = test.step.le(legit_window(df)[1]).values
    splits = [{"conjunto": n, "filas": int(len(s)), "step_desde": int(s.step.min()), "step_hasta": int(s.step.max()),
               "fraudes": int(s[TARGET].sum()), "tasa": float(s[TARGET].mean())}
              for n, s in (("train", train), ("validation", valid), ("test", test))]
    print(pd.DataFrame(splits))

    results, fitted, scores_test = {}, {}, {}

    # Línea base: regla determinística sin aprendizaje
    rule_va, rule_te = valid.drainsOrigin.values.astype(float), test.drainsOrigin.values.astype(float)
    results["rule"] = {"name": MODEL_NAMES["rule"], "fit_seconds": 0.0,
                       "valid": evaluate(y_va, rule_va, 0.5),
                       "test": evaluate(y_te, rule_te, 0.5, test.amount.values),
                       "test_window": evaluate(y_te[in_window], rule_te[in_window], 0.5)}
    scores_test["rule"] = rule_te

    for key in MODEL_ORDER:
        for scenario, feats in (("A", FEATURES_PRE), ("A_sin_vaciado", FEATURES_NO_DRAIN)):
            pipe = make_pipeline(key, feats)
            ts = time.time()
            pipe.fit(train[feats], y_tr)
            fit_s = time.time() - ts
            s_va = pipe.predict_proba(valid[feats])[:, 1]
            thr = best_threshold(y_va, s_va)
            ts = time.time()
            s_te = pipe.predict_proba(test[feats])[:, 1]
            latency_ms = (time.time() - ts) / len(test) * 1000 * 1000  # ms cada 1.000 transacciones
            entry = {"name": MODEL_NAMES[key], "scenario": scenario, "fit_seconds": round(fit_s, 1),
                     "ms_per_1000": round(latency_ms, 2),
                     "valid": evaluate(y_va, s_va, thr), "test": evaluate(y_te, s_te, thr, test.amount.values),
                     "test_window": evaluate(y_te[in_window], s_te[in_window], thr)}
            rk = key if scenario == "A" else f"{key}__sin_vaciado"
            results[rk] = entry
            if scenario == "A":
                fitted[key], scores_test[key] = pipe, s_te
            print(f"{rk:22s} fit {fit_s:6.1f}s  val PR-AUC {entry['valid']['pr_auc']:.4f}  "
                  f"test PR-AUC {entry['test']['pr_auc']:.4f}  test F2 {entry['test']['f2']:.4f}")

    # Selección: (1) mayor PR-AUC en validación, (2) robustez sin las variables de vaciado, (3) simplicidad
    def sel_key(k):
        return (round(results[k]["valid"]["pr_auc"], 3),
                round(results[f"{k}__sin_vaciado"]["valid"]["pr_auc"], 3),
                -MODEL_ORDER.index(k))
    chosen = max(MODEL_ORDER, key=sel_key)
    print("Modelo elegido:", chosen)

    # Escenario B: mismo algoritmo con saldos posteriores (comparación, no se despliega)
    pipe_b = make_pipeline(chosen, FEATURES_POST).fit(train[FEATURES_POST], y_tr)
    sb_va = pipe_b.predict_proba(valid[FEATURES_POST])[:, 1]
    thr_b = best_threshold(y_va, sb_va)
    sb_te = pipe_b.predict_proba(test[FEATURES_POST])[:, 1]
    results[f"{chosen}__B"] = {"name": MODEL_NAMES[chosen], "scenario": "B",
                               "valid": evaluate(y_va, sb_va, thr_b),
                               "test": evaluate(y_te, sb_te, thr_b, test.amount.values)}

    # Sensibilidad: mismo algoritmo entrenado sólo con la ventana donde hay legítimas (sin fraudes "aislados")
    lo = legit_window(df)[0]
    tr_w = train[train.step.ge(lo)]
    pipe_w = make_pipeline(chosen, FEATURES_PRE).fit(tr_w[FEATURES_PRE], tr_w[TARGET].values)
    sw_va = pipe_w.predict_proba(valid[FEATURES_PRE])[:, 1]
    sw_te = pipe_w.predict_proba(test[FEATURES_PRE])[:, 1]
    results[f"{chosen}__solo_ventana"] = {"name": MODEL_NAMES[chosen], "scenario": "A_solo_ventana",
                                         "train_rows": int(len(tr_w)), "train_frauds": int(tr_w[TARGET].sum()),
                                         "valid": evaluate(y_va, sw_va, best_threshold(y_va, sw_va)),
                                         "test": evaluate(y_te, sw_te, best_threshold(y_va, sw_va), test.amount.values)}

    model = fitted[chosen]
    thr = results[chosen]["valid"]["threshold"]
    s_te = scores_test[chosen]
    s_va = model.predict_proba(valid[FEATURES_PRE])[:, 1]

    # Curvas en test (todos los modelos) y curva de umbral en validación (modelo elegido)
    curves = {}
    for k, sc in scores_test.items():
        p, r, _ = precision_recall_curve(y_te, sc)
        fpr, tpr, _ = roc_curve(y_te, sc)
        curves[k] = {"pr": downsample_curve(r[::-1], p[::-1]), "roc": downsample_curve(fpr, tpr)}
    grid = np.linspace(0.01, 0.99, 50)
    thr_curve = []
    for g in grid:
        pr = (s_va >= g).astype(int)
        thr_curve.append({"t": round(float(g), 3),
                          "precision": float(precision_score(y_va, pr, zero_division=0)),
                          "recall": float(recall_score(y_va, pr)),
                          "f2": float(fbeta_score(y_va, pr, beta=2, zero_division=0))})

    # Importancia por permutación: todos los fraudes de test + muestra de legítimas
    rng = np.random.RandomState(SEED)
    legit_idx = rng.choice(np.where(y_te == 0)[0], 40000, replace=False)
    idx = np.concatenate([np.where(y_te == 1)[0], legit_idx])
    pi = permutation_importance(model, test[FEATURES_PRE].iloc[idx], y_te[idx], scoring="average_precision",
                                n_repeats=5, random_state=SEED, n_jobs=-1)
    importance = sorted([{"feature": f, "importance": float(m), "std": float(s)}
                         for f, m, s in zip(FEATURES_PRE, pi.importances_mean, pi.importances_std)],
                        key=lambda d: -d["importance"])

    # Desempeño por tipo de transacción (test)
    pred_te = (s_te >= thr).astype(int)
    per_type = []
    for t, g in test.assign(pred=pred_te).groupby("type"):
        per_type.append({"type": t, "transacciones": int(len(g)), "fraudes": int(g[TARGET].sum()),
                         "alertas": int(g.pred.sum()), "detectados": int((g.pred & g[TARGET]).sum())})

    # Fraudes no detectados: perfil (para el análisis de errores)
    missed = test.loc[(y_te == 1) & (pred_te == 0)]
    missed_profile = {"n": int(len(missed)), "por_tipo": missed.type.value_counts().to_dict(),
                      "vacia_cuenta": float(missed.drainsOrigin.mean()) if len(missed) else 0.0,
                      "monto_mediano": float(missed.amount.median()) if len(missed) else 0.0,
                      "origen_saldo_cero": float(missed.origZeroBefore.mean()) if len(missed) else 0.0}

    # Ejemplos reales de test para precargar el simulador de la app
    ex_cols = ["step", "type", "amount", "oldbalanceOrg", "oldbalanceDest", "destPrefix", TARGET]
    examples = pd.concat([
        test[(y_te == 1) & (test.drainsOrigin == 1)].sample(2, random_state=1),
        test[(y_te == 1) & (test.drainsOrigin == 0)].sample(1, random_state=1),
        test[(y_te == 0) & test.type.isin(["TRANSFER", "CASH_OUT"])].sample(2, random_state=1),
        test[(y_te == 0) & test.type.eq("PAYMENT")].sample(1, random_state=1),
    ])[ex_cols]
    examples["hourOfDay"] = (examples.step - 1) % 24

    metrics = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "dataset": eda_summary(df),
        "splits": splits,
        "split_steps": {"train_max": TRAIN_MAX_STEP, "valid_max": VALID_MAX_STEP},
        "results": results,
        "chosen": chosen,
        "chosen_name": MODEL_NAMES[chosen],
        "threshold": thr,
        "features": FEATURES_PRE,
        "curves": curves,
        "threshold_curve": thr_curve,
        "importance": importance,
        "per_type": per_type,
        "missed_profile": missed_profile,
        "examples": examples.drop(columns="step").to_dict(orient="records"),
        "train_seconds": round(time.time() - t0, 1),
    }
    MODELS.mkdir(exist_ok=True)
    joblib.dump({"pipeline": model, "threshold": thr, "features": FEATURES_PRE, "model_key": chosen,
                 "model_name": MODEL_NAMES[chosen], "test_metrics": results[chosen]["test"]},
                MODELS / "fraud_model.joblib", compress=3)
    (MODELS / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Listo en {metrics['train_seconds']}s -> models/")


if __name__ == "__main__":
    main()
