import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { obtenerShap } from "../../api/auditoriaApi";
import ErrorBanner from "../../components/ui/ErrorBanner";
import Spinner from "../../components/ui/Spinner";
import { useCarga } from "../../hooks/useCarga";
import { SHAP_COLOR_NEGATIVO, SHAP_COLOR_POSITIVO } from "../../utils/auditoria";
import { mensajeError } from "../../utils/errores";

const cortar = (t, n = 30) => (t.length > n ? `${t.slice(0, n - 1)}…` : t);
const fmt = (v, dec = 3) => (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(dec);

/** Convierte el JSON del backend en filas de cascada: cada barra va de la suma acumulada previa a la nueva. */
function construirFilas(d) {
  const filas = d.contribuciones.map((c) => ({
    nombre: `${c.etiqueta}: ${String(c.valor).split(" (")[0]}`, valorCorto: String(c.valor).split(" (")[0], variable: c.etiqueta, valor: String(c.valor), shap: c.shap,
  }));
  if (d.otras) {
    filas.push({ nombre: `${d.otras.cantidad} variables más`, valorCorto: "", variable: `${d.otras.cantidad} variables más`, valor: "—", shap: d.otras.shap });
  }
  // Orden visual: mayor |SHAP| arriba. La cascada se acumula desde abajo (valor base) hacia arriba, como shap.plots.waterfall.
  let acum = d.valor_base;
  for (let i = filas.length - 1; i >= 0; i--) {
    const ini = acum;
    acum += filas[i].shap;
    filas[i].rango = [Math.min(ini, acum), Math.max(ini, acum)];
  }
  return filas;
}

function mensajeShap(err) {
  if (err?.status === 503) return err.message || "El modelo de explicabilidad no está disponible.";
  if (err?.code === "FEATURES_MISSING") {
    const f = err.details?.faltantes;
    return `Faltan datos para explicar esta evaluación${f?.length ? `: ${f.join(", ")}` : ""}.`;
  }
  return mensajeError(err, "No pudimos calcular la explicación SHAP.");
}

/**
 * Explicabilidad local (SHAP) de una evaluación como cascada horizontal con Recharts.
 * Colores (pedido): verde = contribución positiva al riesgo, rojo = negativa. Se cambian en utils/auditoria.js.
 */
export default function ShapWaterfallChart({ evaluacionId }) {
  const { data, loading, error, reintentar } = useCarga((signal) => obtenerShap(evaluacionId, { signal }), [evaluacionId]);
  const titulo = `shap-${evaluacionId}`;

  return (
    <section aria-labelledby={titulo} className="border-t border-slate-200 pt-5">
      <h3 id={titulo} className="mb-1 text-base font-bold">Explicabilidad SHAP</h3>
      {loading && <Spinner label="Calculando valores SHAP…" />}
      {error && <ErrorBanner message={mensajeShap(error)} onRetry={error.status === 503 || error.code === "FEATURES_MISSING" ? undefined : reintentar} />}
      {data && <Grafico d={data} />}
    </section>
  );
}

function Grafico({ d }) {
  const filas = construirFilas(d);
  const prob = d.espacio === "probabilidad";
  const unidad = prob ? "probabilidad" : "log-odds";
  const fin = d.valor_base + filas.reduce((s, f) => s + f.shap, 0);
  const alto = Math.max(200, filas.length * 40 + 60);

  return (
    <>
      <p className="mb-2 text-xs text-slate-600">
        Cómo cada variable empuja la predicción desde el valor base ({d.valor_base.toFixed(3)}) hasta el valor de esta MYPE ({fin.toFixed(3)}),
        en unidades de {unidad}. Probabilidad base {(d.probabilidad_base * 100).toFixed(1)}% → {(d.probabilidad * 100).toFixed(1)}%.
      </p>
      <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs" aria-label="Leyenda">
        <li className="flex items-center gap-1"><span aria-hidden="true" className="h-3 w-3 rounded-sm" style={{ background: SHAP_COLOR_POSITIVO }} />Contribución positiva (sube el riesgo)</li>
        <li className="flex items-center gap-1"><span aria-hidden="true" className="h-3 w-3 rounded-sm" style={{ background: SHAP_COLOR_NEGATIVO }} />Contribución negativa (baja el riesgo)</li>
      </ul>

      <div style={{ height: alto }} className="w-full" aria-hidden="true">
        <ResponsiveContainer>
          <BarChart data={filas} layout="vertical" margin={{ top: 24, right: 16, left: 0, bottom: 8 }}>
            <XAxis type="number" domain={["auto", "auto"]} tick={{ fontSize: 11 }} tickFormatter={(v) => Number(v.toFixed(2))} />
            <YAxis type="category" dataKey="nombre" width={168} tick={<EtiquetaFila filas={filas} />} interval={0} />
            <ReferenceLine x={d.valor_base} stroke="#64748B" strokeDasharray="4 3" label={{ value: "base", position: "top", fontSize: 10, fill: "#64748B" }} />
            <ReferenceLine x={fin} stroke="#0F172A" label={{ value: "f(x)", position: "top", fontSize: 10, fill: "#0F172A" }} />
            <Tooltip cursor={{ fill: "rgba(148,163,184,0.15)" }} content={<Detalle unidad={unidad} />} />
            <Bar dataKey="rango" isAnimationActive={false} barSize={18} minPointSize={2}>
              {filas.map((f) => <Cell key={f.nombre} fill={f.shap >= 0 ? SHAP_COLOR_POSITIVO : SHAP_COLOR_NEGATIVO} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Alternativa accesible y legible para lectores de pantalla */}
      <table className="sr-only">
        <caption>Contribución SHAP por variable ({unidad})</caption>
        <thead><tr><th>Variable</th><th>Valor</th><th>Contribución SHAP</th></tr></thead>
        <tbody>{filas.map((f) => <tr key={f.nombre}><td>{f.variable}</td><td>{f.valor}</td><td>{fmt(f.shap)}</td></tr>)}</tbody>
      </table>
    </>
  );
}

/** Etiqueta del eje Y en dos líneas: variable (negrita) y su valor debajo. */
function EtiquetaFila({ x, y, payload, filas }) {
  const f = filas.find((r) => r.nombre === payload.value);
  if (!f) return null;
  return (
    <text x={x - 6} y={y} textAnchor="end" fontSize={11}>
      <tspan x={x - 6} dy={f.valorCorto ? "-0.3em" : "0.35em"} fontWeight={700} fill="#0F172A">{cortar(f.variable, 23)}</tspan>
      {f.valorCorto && <tspan x={x - 6} dy="1.3em" fill="#475569">{cortar(f.valorCorto, 26)}</tspan>}
    </text>
  );
}

function Detalle({ active, payload, unidad }) {
  if (!active || !payload?.length) return null;
  const f = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-2 text-xs shadow-md">
      <p className="font-bold">{f.variable}</p>
      <p>Valor: {f.valor}</p>
      <p>Contribución SHAP: <b>{fmt(f.shap)}</b> {unidad}</p>
      <p className="text-slate-600">{f.shap >= 0 ? "Aumenta" : "Reduce"} el riesgo</p>
    </div>
  );
}
