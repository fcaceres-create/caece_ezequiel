// Utilidades compartidas para los gráficos (Chart.js). Los colores salen de las variables CSS
// para que el modo claro/oscuro se respete al redibujar.
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const fmtInt = (n) => Math.round(n).toLocaleString("es-AR");
const fmtPct = (x, d = 2) => (x * 100).toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d }) + " %";
const fmtMoney = (n) => {
  const a = Math.abs(n);
  if (a >= 1e9) return "$ " + (n / 1e9).toLocaleString("es-AR", { maximumFractionDigits: 2 }) + " mil M";
  if (a >= 1e6) return "$ " + (n / 1e6).toLocaleString("es-AR", { maximumFractionDigits: 1 }) + " M";
  return "$ " + fmtInt(n);
};

const _charts = [];
const _builders = [];

function baseOptions(extra = {}) {
  const grid = css("--grid"), muted = css("--muted"), text = css("--text");
  return Object.assign({
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: css("--surface"), titleColor: text, bodyColor: css("--text-2"),
        borderColor: css("--border"), borderWidth: 1, padding: 10, boxPadding: 4, usePointStyle: true,
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: muted, font: { size: 11 } }, border: { color: grid } },
      y: { grid: { color: grid }, ticks: { color: muted, font: { size: 11 } }, border: { display: false } },
    },
  }, extra);
}

// Registra un constructor de gráfico; se re-ejecuta al cambiar el tema.
function chart(id, build) {
  const el = document.getElementById(id);
  if (!el) return;
  const make = () => {
    const cfg = build();
    _charts[id] && _charts[id].destroy();
    _charts[id] = new Chart(el, cfg);
  };
  _builders.push(make);
  make();
}
window.redrawCharts = () => _builders.forEach((b) => b());
