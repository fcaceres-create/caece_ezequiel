# -*- coding: utf-8 -*-
"""Ingeniería de variables para predicción de fraude.

Replica las decisiones de la etapa de preparación (notebooks/Preparacion_Datos_Fraude.ipynb)
para que el entrenamiento y la aplicación web calculen exactamente las mismas variables.
"""
import numpy as np
import pandas as pd

TRANSACTION_TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]

# Partición temporal definida en la preparación de datos (1 step = 1 hora)
TRAIN_MAX_STEP = 405
VALID_MAX_STEP = 548

CATEGORICAL = ["type", "destPrefix"]

# Escenario A (modelo desplegado): sólo información conocida ANTES de autorizar la operación.
NUMERIC_PRE = [
    "amount", "logAmount", "hourOfDay", "isNight",
    "oldbalanceOrg", "oldbalanceDest", "origZeroBefore", "destZeroBefore",
    "amountToOrigBalance", "amountToDestBalance", "amountMinusOrigBalance", "drainsOrigin",
]
# Escenario B (comparación): agrega saldos posteriores y errores contables del registro.
NUMERIC_POST = NUMERIC_PRE + [
    "newbalanceOrig", "newbalanceDest", "origBalanceDelta", "destBalanceDelta",
    "origBalanceError", "destBalanceError", "origZeroAfter", "destZeroAfter",
]
FEATURES_PRE = NUMERIC_PRE + CATEGORICAL
FEATURES_POST = NUMERIC_POST + CATEGORICAL
# Ablación: escenario A sin las dos variables de "vaciado de cuenta"
FEATURES_NO_DRAIN = [c for c in FEATURES_PRE if c not in ("drainsOrigin", "amountMinusOrigBalance")]
TARGET = "isFraud"


def add_transaction_features(data: pd.DataFrame) -> pd.DataFrame:
    """Agrega variables derivadas calculables al momento de procesar la transacción."""
    out = data.copy()
    out = out.drop(columns=["Unnamed: 0", "isFlaggedFraud"], errors="ignore")
    out["hourOfDay"] = (out["step"] - 1) % 24
    out["day"] = (out["step"] - 1) // 24 + 1
    out["isNight"] = out["hourOfDay"].between(0, 5).astype("int8")
    out["logAmount"] = np.log1p(out["amount"])
    out["origBalanceDelta"] = out["newbalanceOrig"] - out["oldbalanceOrg"]
    out["destBalanceDelta"] = out["newbalanceDest"] - out["oldbalanceDest"]
    is_cash_in = out["type"].eq("CASH_IN")
    expected_orig = np.where(is_cash_in, out.oldbalanceOrg + out.amount, out.oldbalanceOrg - out.amount)
    expected_dest = np.where(is_cash_in, out.oldbalanceDest - out.amount, out.oldbalanceDest + out.amount)
    out["origBalanceError"] = out.newbalanceOrig - expected_orig
    out["destBalanceError"] = out.newbalanceDest - expected_dest
    out["origZeroBefore"] = out.oldbalanceOrg.eq(0).astype("int8")
    out["origZeroAfter"] = out.newbalanceOrig.eq(0).astype("int8")
    out["destZeroBefore"] = out.oldbalanceDest.eq(0).astype("int8")
    out["destZeroAfter"] = out.newbalanceDest.eq(0).astype("int8")
    out["destPrefix"] = out.nameDest.astype(str).str[0]
    out["amountToOrigBalance"] = out.amount / (out.oldbalanceOrg.abs() + 1)
    out["amountToDestBalance"] = out.amount / (out.oldbalanceDest.abs() + 1)
    # Patrón de vaciado: la operación se lleva exactamente todo el saldo disponible del origen
    out["amountMinusOrigBalance"] = out.amount - out.oldbalanceOrg
    out["drainsOrigin"] = (np.isclose(out.amount, out.oldbalanceOrg, atol=0.01) & out.oldbalanceOrg.gt(0)).astype("int8")
    return out


def temporal_split(prepared: pd.DataFrame):
    train = prepared.loc[prepared.step.le(TRAIN_MAX_STEP)]
    valid = prepared.loc[prepared.step.between(TRAIN_MAX_STEP + 1, VALID_MAX_STEP)]
    test = prepared.loc[prepared.step.gt(VALID_MAX_STEP)]
    return train, valid, test
