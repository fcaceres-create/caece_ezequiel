# -*- coding: utf-8 -*-
"""Genera docs/presentacion.html: presentación autocontenida (figuras embebidas, funciona sin internet).

Uso:  python docs/build_slides.py      Navegación: ← → / espacio / clic · F = pantalla completa · imprimir = PDF
"""
import base64
import json
from pathlib import Path

import figures

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "presentacion.html"
M = json.loads((ROOT / "models" / "metrics.json").read_text(encoding="utf-8"))
REPO = "https://github.com/fcaceres-create/caece_ezequiel"


def num(x, d=0):
    return f"{x:,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def pct(x, d=2):
    return num(x * 100, d) + " %"


def img(name):
    path = DOCS / "figures" / name if (DOCS / "figures" / name).exists() else DOCS / "img" / name
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def build():
    figures.build_all()
    d, smp, R = M["dataset"], M["dataset"]["sampling"], M["results"]
    ch, chn = M["chosen"], M["chosen_name"]
    T, TW, rule = R[ch]["test"], R[ch]["test_window"], R["rule"]["test"]
    c = T["confusion"]

    rows = ""
    for k in ["rule", "logreg", "tree", "forest", "hgb"]:
        x = R[k]
        abl = R.get(k + "__sin_vaciado")
        cls = ' class="sel"' if k == ch else ""
        rows += (f"<tr{cls}><td>{x['name'].replace(' (vacía la cuenta)', '')}</td><td>{num(x['test']['pr_auc'], 4)}</td>"
                 f"<td>{pct(x['test']['recall'])}</td><td>{pct(x['test']['precision'])}</td><td>{x['test']['confusion']['fn']}</td>"
                 f"<td>{x['test']['confusion']['fp']}</td><td>{num(abl['test']['pr_auc'], 4) if abl else '—'}</td></tr>")

    slides = [
        # 1 Portada
        f"""<section class="cover">
          <div class="eyebrow">Universidad CAECE · Trabajo Práctico Final</div>
          <h1>Predicción de fraude<br>en transacciones</h1>
          <p class="lead">Del análisis de datos a un modelo desplegado como aplicación web</p>
          <div class="kpis">
            <div><b>{num(d['rows'])}</b><span>transacciones</span></div>
            <div><b>{num(c['tp'])}/{num(c['tp'] + c['fn'])}</b><span>fraudes detectados en prueba</span></div>
            <div><b>{c['fp']}</b><span>falsos positivos</span></div>
          </div>
        </section>""",
        # 2 Problema
        """<section>
          <div class="eyebrow">1 · Comprensión del negocio</div>
          <h2>No todos los errores cuestan lo mismo</h2>
          <div class="cols2">
            <div class="card bad"><h3>Falso negativo</h3><p>Fraude que pasa sin detectar.<br><b>Pérdida directa del monto.</b></p></div>
            <div class="card warn"><h3>Falso positivo</h3><p>Operación legítima retenida.<br><b>Costo de revisión y fricción.</b></p></div>
          </div>
          <ul class="big">
            <li><b>Accuracy no sirve:</b> “nunca fraude” acierta más del 99 %.</li>
            <li>Métrica de comparación: <b>PR-AUC</b> (centrada en la clase minoritaria).</li>
            <li>Umbral: máximo <b>F2</b> (el recall pesa el doble que la precisión).</li>
            <li>Sólo información <b>disponible antes de autorizar</b>.</li>
          </ul>
        </section>""",
        # 3 Datos
        f"""<section>
          <div class="eyebrow">2 · Comprensión de los datos</div>
          <h2>El fraude vive en sólo dos tipos de operación</h2>
          <img class="fig" src="{img('tipo.png')}" alt="Volumen y tasa de fraude por tipo">
          <p class="note">{num(d['rows'])} transacciones · {num(d['frauds'])} fraudes · sin faltantes ni duplicados · montos de fraude ~{num(d['amount_quantiles']['fraude']['0.5'] / d['amount_quantiles']['legitima']['0.5'])}× mayores (mediana)</p>
        </section>""",
        # 4 Vaciado
        f"""<section>
          <div class="eyebrow">2 · Hallazgo clave</div>
          <h2>El fraude vacía la cuenta de origen</h2>
          <div class="hero-nums">
            <div><b class="o">{pct(d['drain']['fraude_que_vacia'], 1)}</b><span>de los fraudes extrae <i>exactamente</i> todo el saldo</span></div>
            <div><b class="b">{pct(d['drain']['p_fraude_si_vacia'])}</b><span>de las operaciones que vacían la cuenta son fraude</span></div>
          </div>
          <p class="lead">Se convirtió en la variable <code>drainsOrigin</code> y en una <b>regla base</b> que todo modelo debe superar:
          por sí sola logra {pct(rule['recall'], 1)} de recall.</p>
          <p class="note">Coherente con el negocio (quien toma una cuenta la vacía), pero mucho más nítido que en la realidad: es un rasgo del simulador PaySim.</p>
        </section>""",
        # 5 Muestreo
        f"""<section>
          <div class="eyebrow">2 · Hallazgo de calidad</div>
          <h2>El archivo no es una muestra uniforme</h2>
          <img class="fig short" src="{img('particion.png')}" alt="Legítimas y fraudes por día">
          <div class="cols2 tight">
            <p>Tramo final del simulador <b>+ todos los fraudes previos</b>: los steps 1–{smp['legit_steps'][0] - 1} sólo tienen fraudes. Tasa real: <b>{pct(smp['window_rate'])}</b>, no {pct(d['fraud_rate'])}.</p>
            <p><b>Control:</b> sin <code>step</code>/<code>day</code> como variables · fraudes representativos ({pct(smp['drain_before'], 1)} vs {pct(smp['drain_window'], 1)} vacían) · evaluación también en la ventana con ambas clases.</p>
          </div>
        </section>""",
        # 6 Preparación
        f"""<section>
          <div class="eyebrow">3 · Preparación de los datos</div>
          <h2>{len(M['features'])} variables, todas conocidas antes de autorizar</h2>
          <div class="cols2">
            <div class="card"><h3>Se crean</h3><ul>
              <li><b>Tiempo:</b> hora del día, franja nocturna</li>
              <li><b>Monto:</b> log(1 + monto)</li>
              <li><b>Saldos:</b> ceros previos, ratios monto/saldo</li>
              <li><b>Vaciado:</b> drainsOrigin, monto − saldo</li>
              <li><b>Categóricas:</b> tipo, prefijo destino (One-Hot)</li>
              <li><b>Escalado:</b> RobustScaler (colas extremas)</li></ul></div>
            <div class="card"><h3>Se excluyen</h3><ul>
              <li><code>isFlaggedFraud</code> — consigna</li>
              <li><code>nameOrig</code>/<code>nameDest</code> — ~100 % únicos: memorización</li>
              <li><code>step</code>/<code>day</code> — futuro no visto + artefacto</li>
              <li>Saldos posteriores — no se conocen al autorizar</li>
              <li>Montos extremos <b>no</b> se eliminan: son señal</li></ul></div>
          </div>
        </section>""",
        # 7 Validación
        f"""<section>
          <div class="eyebrow">4 · Validación</div>
          <h2>Entrenar con el pasado, evaluar con el futuro</h2>
          <div class="timeline">
            <div style="flex:405;background:var(--blue)">Entrenamiento · steps 1–405</div>
            <div style="flex:143;background:var(--aqua)">Validación · 406–548</div>
            <div style="flex:195;background:var(--orange)">Prueba · 549–743</div>
          </div>
          <ul class="big">
            <li>Partición <b>temporal</b>: la aleatoria mezclaría pasado y futuro y sería optimista.</li>
            <li>Validación → elegir modelo y umbral. Prueba → <b>una sola vez</b>, al final.</li>
            <li>Desbalance con <b>class_weight</b>: no fabrica datos sintéticos ni altera la evaluación.</li>
          </ul>
        </section>""",
        # 8 Algoritmos
        """<section>
          <div class="eyebrow">5 · Modelado</div>
          <h2>Cuatro familias de algoritmos y una regla base</h2>
          <table class="t">
            <tr><th>Algoritmo</th><th>Por qué</th></tr>
            <tr><td>Regla base</td><td>Referencia sin aprendizaje: si no se la supera, el modelo no se justifica</td></tr>
            <tr><td>Regresión Logística</td><td>Lineal e interpretable</td></tr>
            <tr><td>Árbol de Decisión</td><td>Reglas no lineales explicables al negocio</td></tr>
            <tr><td>Random Forest</td><td>Bagging: menor varianza, robusto a outliers</td></tr>
            <tr><td>Gradient Boosting (HistGB)</td><td>Boosting: corrige errores secuencialmente, eficiente en tablas grandes</td></tr>
          </table>
          <p class="note">Además, cada modelo se reentrenó <b>sin las variables de vaciado</b> para medir su robustez.</p>
        </section>""",
        # 9 Comparación
        f"""<section>
          <div class="eyebrow">6 · Evaluación</div>
          <h2>Empate en desempeño, desempate por robustez</h2>
          <table class="t num">
            <tr><th>Modelo</th><th>PR-AUC</th><th>Recall</th><th>Precisión</th><th>FN</th><th>FP</th><th>PR-AUC sin vaciado</th></tr>
            {rows}
          </table>
          <p class="note">Prueba, umbral fijado en validación. Sin la señal de vaciado, la Regresión Logística y el Árbol colapsan; {chn} la reaprende sola desde monto y saldo.</p>
        </section>""",
        # 10 Robustez gráfico
        f"""<section>
          <div class="eyebrow">6 · Robustez</div>
          <h2>¿Qué pasa si quitamos la señal dominante?</h2>
          <img class="fig" src="{img('modelos.png')}" alt="PR-AUC con y sin variables de vaciado">
          <p class="note">Criterio: (1) PR-AUC en validación → (2) robustez → (3) simplicidad. Elegido: <b>{chn}</b> · entrena en {num(R[ch]['fit_seconds'], 1)} s.</p>
        </section>""",
        # 11 Modelo final
        f"""<section>
          <div class="eyebrow">6 · Modelo final</div>
          <h2>{chn}</h2>
          <div class="cols2 center">
            <img class="fig" src="{img('confusion.png')}" alt="Matriz de confusión">
            <div class="stack">
              <div class="stat"><b>{pct(T['recall'])}</b><span>recall · {c['fn']} fraudes perdidos</span></div>
              <div class="stat"><b>{pct(T['precision'])}</b><span>precisión · {c['fp']} legítimas bloqueadas</span></div>
              <div class="stat"><b>{pct(T['fraud_amount_detected'] / T['fraud_amount_total'])}</b><span>del monto defraudado evitado</span></div>
              <div class="stat"><b>{num(M['threshold'], 3)}</b><span>umbral (máximo F2 en validación)</span></div>
            </div>
          </div>
        </section>""",
        # 12 Razonabilidad
        f"""<section>
          <div class="eyebrow">7 · Razonabilidad</div>
          <h2>Un resultado perfecto exige sospechar</h2>
          <table class="t">
            <tr><th>Control</th><th>Resultado</th></tr>
            <tr><td>Regla base (sólo vaciado)</td><td>{pct(rule['recall'], 1)} recall: el modelo recupera {rule['confusion']['fn'] - c['fn']} fraudes más</td></tr>
            <tr><td>Prueba sólo donde conviven ambas clases</td><td>{TW['confusion']['tp']}/{TW['confusion']['tp'] + TW['confusion']['fn']} detectados, {TW['confusion']['fp']} FP</td></tr>
            <tr><td>Entrenar sin el período sólo-fraude</td><td>PR-AUC {num(R[ch + '__solo_ventana']['test']['pr_auc'], 4)}</td></tr>
            <tr><td>Con saldos posteriores (fuga)</td><td>No mejora: {R[ch + '__B']['test']['confusion']['fn']} FN</td></tr>
          </table>
          <p class="lead">Es razonable <b>para este simulador</b>. En datos reales el patrón es menos nítido: hay que monitorear la deriva y reentrenar.</p>
        </section>""",
        # 13 App
        f"""<section>
          <div class="eyebrow">8 · Aplicación</div>
          <h2>El modelo, consumible como API y web</h2>
          <img class="fig arch" src="{img('arquitectura.png')}" alt="Arquitectura">
          <div class="cols2 shots">
            <img src="{img('app_resultados.png')}" alt="Dashboard de resultados">
            <img src="{img('app_simulador.png')}" alt="Simulador">
          </div>
          <p class="note"><code>POST /api/predict</code> · dashboard de resultados · explicación del proceso · simulador con ejemplos reales</p>
        </section>""",
        # 14 Conclusiones
        f"""<section>
          <div class="eyebrow">9 · Conclusiones</div>
          <h2>Qué nos llevamos</h2>
          <ul class="big">
            <li>Modelo que detecta el <b>{pct(T['recall'])}</b> de los fraudes futuros sin bloquear legítimas, con datos previos a la autorización.</li>
            <li>Elección justificada por <b>desempeño, robustez y simplicidad</b>; umbral alineado al costo del negocio.</li>
            <li>El análisis crítico detectó el <b>patrón de vaciado</b> y el <b>muestreo no uniforme</b>, y ambos se controlaron.</li>
            <li>Próximos pasos: umbral por costo real, variables de comportamiento por cliente, monitoreo de deriva, explicaciones SHAP.</li>
          </ul>
        </section>""",
        # 15 Cierre
        f"""<section class="cover end">
          <h1>¿Preguntas?</h1>
          <p class="lead">Código, modelo, aplicación e informe</p>
          <p class="repo">{REPO}</p>
        </section>""",
    ]

    html = TEMPLATE.replace("{{SLIDES}}", "\n".join(slides)).replace("{{N}}", str(len(slides)))
    OUT.write_text(html, encoding="utf-8")
    print("Slides:", OUT, f"{OUT.stat().st_size / 1024:.0f} KB", len(slides), "diapositivas")


TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Predicción de Fraude</title>
<style>
:root{--ink:#0b0b0b;--ink2:#52514e;--muted:#7b7a75;--line:#e2e1dc;--bg:#f6f6f4;--paper:#fcfcfb;--soft:#f0efec;
  --blue:#2a78d6;--orange:#eb6834;--aqua:#1baf7a;--bad:#c62828;--bad-bg:#fdecea;--warn:#9a6700;--warn-bg:#fff4d6}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:#1b1b1a;font-family:Inter,"Segoe UI",system-ui,sans-serif;color:var(--ink);overflow:hidden}
#deck{position:absolute;left:50%;top:50%;width:1280px;height:720px;transform-origin:center center}
section{position:absolute;inset:0;background:var(--paper);padding:56px 72px 60px;display:none;flex-direction:column;border-radius:6px}
section.active{display:flex}
.eyebrow{font-size:13px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--orange);margin-bottom:10px}
h1{font-size:64px;line-height:1.05;margin:0 0 18px;letter-spacing:-.02em}
h2{font-size:38px;line-height:1.12;margin:0 0 26px;letter-spacing:-.015em}
h3{font-size:20px;margin:0 0 10px}
p,li{font-size:19px;line-height:1.5;color:var(--ink2)}
b{color:var(--ink)}
code{font-family:Consolas,monospace;font-size:.88em;background:var(--soft);padding:1px 6px;border-radius:5px;color:var(--ink)}
.lead{font-size:23px;line-height:1.45;color:var(--ink2);max-width:1050px}
.note{font-size:16px;color:var(--muted);margin-top:auto}
ul.big{padding-left:22px;margin:4px 0}ul.big li{font-size:21px;margin-bottom:12px}
.card ul{padding-left:20px;margin:0}.card li{font-size:17.5px;margin-bottom:6px}
.cover{justify-content:center;background:linear-gradient(135deg,#fcfcfb 55%,#fdeee6)}
.cover h1{font-size:76px}
.kpis{display:flex;gap:56px;margin-top:46px;border-top:3px solid var(--orange);padding-top:20px}
.kpis div{display:flex;flex-direction:column}.kpis b{font-size:42px;letter-spacing:-.02em}.kpis span{font-size:15px;color:var(--muted)}
.end{align-items:flex-start}.repo{font-family:Consolas,monospace;font-size:22px;color:var(--blue)}
.cols2{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-bottom:22px}
.cols2.tight{gap:36px;margin-top:10px}.cols2.tight p{font-size:17px;margin:0}
.cols2.center{align-items:center}
.card{background:var(--soft);border-radius:14px;padding:22px 26px}
.card p{margin:0;font-size:19px}
.card.bad{background:var(--bad-bg)}.card.bad h3{color:var(--bad)}
.card.warn{background:var(--warn-bg)}.card.warn h3{color:var(--warn)}
.fig{max-width:100%;max-height:430px;object-fit:contain;align-self:center}
.fig.short{max-height:330px}.fig.arch{max-height:170px;margin-bottom:12px}
.hero-nums{display:flex;gap:70px;margin:12px 0 30px}
.hero-nums div{display:flex;flex-direction:column;max-width:440px}
.hero-nums b{font-size:96px;letter-spacing:-.04em;line-height:1}.hero-nums b.o{color:var(--orange)}.hero-nums b.b{color:var(--blue)}
.hero-nums span{font-size:20px;color:var(--ink2);margin-top:8px}
.timeline{display:flex;gap:3px;height:58px;border-radius:12px;overflow:hidden;margin:6px 0 30px}
.timeline div{display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:16px}
table.t{border-collapse:collapse;width:100%;font-size:17px;margin-bottom:16px}
table.t th{text-align:left;font-size:12.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);border-bottom:2px solid var(--ink2);padding:8px 12px}
table.t td{padding:10px 12px;border-bottom:1px solid var(--line);color:var(--ink2)}
table.t td:first-child{color:var(--ink);font-weight:600}
table.num td:not(:first-child),table.num th:not(:first-child){text-align:right;font-variant-numeric:tabular-nums}
table.t tr.sel td{background:#e8f1fc;color:var(--ink);font-weight:700}
.stack{display:grid;gap:14px}
.stat{border-left:4px solid var(--blue);padding:4px 0 4px 18px}
.stat b{font-size:40px;display:block;letter-spacing:-.02em;line-height:1.1}.stat span{font-size:16px;color:var(--muted)}
.shots{gap:20px;margin:0}.shots img{width:100%;height:200px;object-fit:cover;object-position:top;border:1px solid var(--line);border-radius:10px}
#bar{position:fixed;left:0;bottom:0;height:4px;background:var(--orange);transition:width .25s}
#count{position:fixed;right:18px;bottom:12px;color:#9a9992;font:13px Inter,system-ui,sans-serif}
#hint{position:fixed;left:18px;bottom:12px;color:#6d6c66;font:12px Inter,system-ui,sans-serif}
@media print{
  @page{size:1280px 720px;margin:0}
  html,body{overflow:visible;background:#fff}
  #deck{position:static;transform:none!important;width:auto;height:auto}
  section{display:flex!important;position:relative;width:1280px;height:720px;page-break-after:always;border-radius:0}
  #bar,#count,#hint{display:none}
}
</style>
</head>
<body>
<div id="deck">
{{SLIDES}}
</div>
<div id="bar"></div><div id="count"></div><div id="hint">← → para navegar · F pantalla completa</div>
<script>
const S=[...document.querySelectorAll("#deck section")];let i=0;
function fit(){const k=Math.min(innerWidth/1280,innerHeight/720)*0.96;document.getElementById("deck").style.transform=`translate(-50%,-50%) scale(${k})`;}
function show(n){i=Math.max(0,Math.min(S.length-1,n));S.forEach((s,j)=>s.classList.toggle("active",j===i));
  document.getElementById("bar").style.width=((i+1)/S.length*100)+"%";document.getElementById("count").textContent=(i+1)+" / "+S.length;
  try{history.replaceState(null,"","#"+(i+1))}catch(e){}}
addEventListener("keydown",e=>{
  if(["ArrowRight","PageDown"," ","Enter"].includes(e.key)){e.preventDefault();show(i+1)}
  else if(["ArrowLeft","PageUp","Backspace"].includes(e.key)){e.preventDefault();show(i-1)}
  else if(e.key==="Home")show(0);else if(e.key==="End")show(S.length-1);
  else if(e.key.toLowerCase()==="f"){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}});
addEventListener("click",e=>{if(e.target.closest("a"))return;show(e.clientX>innerWidth/3?i+1:i-1)});
let tx=null;addEventListener("touchstart",e=>tx=e.touches[0].clientX);addEventListener("touchend",e=>{if(tx===null)return;const dx=e.changedTouches[0].clientX-tx;if(Math.abs(dx)>40)show(dx<0?i+1:i-1);tx=null});
addEventListener("resize",fit);fit();show((parseInt(location.hash.slice(1))||1)-1);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    build()
