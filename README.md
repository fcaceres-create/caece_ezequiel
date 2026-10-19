# Predicción de fraude en transacciones

Trabajo Práctico Final · Universidad CAECE · **Autor:** Ezequiel Diaz Fernandez

Modelo que estima si una transacción es fraudulenta, con su análisis completo (CRISP-DM) y una aplicación web Flask que lo consume mediante una API.

| | |
|---|---|
| **Aplicación online** | [caece-aprendizaje-artificial-ezequiel.onrender.com](https://caece-aprendizaje-artificial-ezequiel.onrender.com) (plan gratuito: la primera carga puede demorar ~50 s) |
| **Modelo final** | Gradient Boosting (`HistGradientBoostingClassifier`) |
| **Prueba (últimos 8 días, nunca vistos)** | 2.165 de 2.168 fraudes detectados · 0 falsos positivos · PR-AUC 1,000 |
| **Variables** | 14, todas conocidas *antes* de autorizar la operación |
| **Informe** | [docs/Informe_TP_Fraude.pdf](docs/Informe_TP_Fraude.pdf) |
| **Presentación** | [docs/presentacion.html](docs/presentacion.html) (abrir en el navegador; ← → para navegar) |

## Hallazgos principales

1. **El fraude vacía la cuenta.** El 97,6 % de los fraudes extrae exactamente todo el saldo de origen, y casi ninguna operación legítima lo hace. Una regla basada sólo en eso logra 97 % de recall, y se usó como línea base.
2. **El archivo no es una muestra uniforme.** `Fraud.csv` contiene el tramo final del simulador más todos los fraudes previos: los steps 1–352 sólo tienen fraudes. La tasa real de fraude es 0,29 %, no 0,60 %. Se controló que el modelo no aproveche este artefacto.
3. **Elección por robustez.** Random Forest y Gradient Boosting empataron en PR-AUC. Se eligió Gradient Boosting porque, sin las variables de vaciado, mantiene PR-AUC 0,999, mientras que Regresión Logística y Árbol caen a 0,65 y 0,50.
4. **Resultados razonables para un simulador**, pero no extrapolables a datos reales sin monitoreo de deriva y reentrenamiento.

## Estructura

```
notebooks/   Preparación de datos: auditoría, EDA, ingeniería de variables, partición temporal
src/
  features.py  Ingeniería de variables (la comparten el entrenamiento y la app)
  train.py     Entrenamiento y comparación de 4 algoritmos + regla base, selección, umbral, métricas
models/
  fraud_model.joblib  Pipeline (preprocesamiento + modelo) + umbral
  metrics.json        Resultados, curvas y datos del análisis (alimenta dashboard, informe y slides)
app/         Aplicación Flask: API REST + dashboard + proceso + simulador
docs/        Informe PDF, presentación HTML, figuras y scripts que los generan
```

## Cómo ejecutar

```bash
pip install -r requirements.txt

# 1. Dataset: descargar Fraud.csv desde el enlace de la consigna y guardarlo en data/Fraud.csv
#    (no se versiona por su tamaño: 120 MB)

# 2. (Opcional) Reentrenar: ~2 minutos. El modelo ya entrenado está en models/
python src/train.py

# 3. Aplicación web -> http://127.0.0.1:5000
python app/app.py

# 4. (Opcional) Regenerar informe y presentación a partir de models/metrics.json
python docs/build_report.py
python docs/build_slides.py
```

La aplicación sólo necesita `models/`: no hace falta el dataset para ejecutarla.

## API

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/predict` | Probabilidad de fraude y decisión para una transacción |
| `GET` | `/api/metrics` | Métricas y datos del análisis |
| `GET` | `/api/health` | Estado y modelo cargado |

```bash
curl -X POST http://127.0.0.1:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"type":"TRANSFER","amount":181000,"oldbalanceOrg":181000,"oldbalanceDest":0,"hourOfDay":3,"destPrefix":"C"}'
```

```json
{"probabilidad": 0.9999, "umbral": 0.984, "es_fraude": true, "decision": "BLOQUEAR / REVISAR",
 "modelo": "Gradient Boosting (HistGB)", "senales": [{"nivel": "alto", "texto": "La operación vacía exactamente el saldo..."}]}
```

Campos: `type` (CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER), `amount`, `oldbalanceOrg`, `oldbalanceDest` (obligatorios), `hourOfDay` (0–23, por defecto 12) y `destPrefix` (`C` cliente / `M` comercio). Si la entrada es inválida, responde `422` con la lista de errores.

## Metodología (resumen)

- **Métrica:** PR-AUC, porque la accuracy engaña con menos del 1 % de fraude. El umbral se elige maximizando F2 en validación, porque un fraude no detectado cuesta más que una revisión.
- **Validación temporal:** entrenamiento con steps 1–405, validación con 406–548 y prueba con 549–743, que se usa una sola vez.
- **Desbalance:** `class_weight`, sin remuestreo, así no se fabrican datos ni se altera la evaluación.
- **Algoritmos:** Regresión Logística, Árbol de Decisión, Random Forest y Gradient Boosting, más una regla base. Cada uno se evalúa también sin las variables de vaciado (ablación).
- **Controles:** escenario con saldos posteriores (fuga), evaluación sólo en la ventana con ambas clases y entrenamiento sin el período de sólo fraudes.
