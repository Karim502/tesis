import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { obtenerComparativo } from "../../api/auditoriaApi";
import ErrorBanner from "../../components/ui/ErrorBanner";
import Spinner from "../../components/ui/Spinner";
import { useCarga } from "../../hooks/useCarga";
import { mensajeError } from "../../utils/errores";

const corta = (t) => String(t).split(" (")[0];
const pc = (f) => Math.round(f * 1000) / 10; // fracción -> % con 1 decimal

/** Compara la probabilidad de riesgo de la MYPE con el promedio de su sector y el general. */
export default function ComparativoSectorial({ evaluacionId }) {
  const { data, loading, error, reintentar } = useCarga((signal) => obtenerComparativo(evaluacionId, { signal }), [evaluacionId]);

  return (
    <section aria-labelledby={`comp-${evaluacionId}`} className="border-t border-slate-200 pt-5">
      <h3 id={`comp-${evaluacionId}`} className="mb-2 text-base font-bold">Comparativo sectorial</h3>
      {loading && <Spinner label="Calculando promedio del sector…" />}
      {error && <ErrorBanner message={mensajeError(error, "No pudimos calcular el comparativo.")} onRetry={reintentar} />}
      {data && <Contenido d={data} />}
    </section>
  );
}

function Contenido({ d }) {
  if (!d.sector || d.promedio_sector == null) {
    return <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">Esta evaluación no tiene sector económico registrado, por lo que no se puede comparar con un promedio sectorial.</p>;
  }
  const filas = [
    { nombre: "Esta MYPE", valor: pc(d.probabilidad), color: "#1F5F5B" },
    { nombre: `Sector: ${corta(d.sector_etiqueta)}`, valor: pc(d.promedio_sector), color: "#64748B", n: d.n_sector },
    { nombre: "Promedio general", valor: pc(d.promedio_general), color: "#CBD5E1", n: d.n_general },
  ];
  const dif = pc(Math.abs(d.diferencia_sector));
  const texto = d.diferencia_sector > 0.0005 ? `${dif} puntos porcentuales por encima` : d.diferencia_sector < -0.0005 ? `${dif} puntos porcentuales por debajo` : "igual";
  return (
    <>
      <p className="mb-2 text-sm">
        Riesgo de <b>{pc(d.probabilidad)}%</b>, {texto === "igual" ? <b>igual al</b> : <><b>{texto}</b> del</>} promedio del sector
        {" "}<b>{corta(d.sector_etiqueta)}</b> ({pc(d.promedio_sector)}%, {d.n_sector} evaluaciones).
      </p>
      {!d.muestra_suficiente && (
        <p role="note" className="mb-2 rounded-lg border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900">
          Muestra pequeña: el sector tiene {d.n_sector} evaluaciones (mínimo recomendado: {d.minimo_muestra}). Interpreta el promedio con cautela.
        </p>
      )}
      <div role="img" aria-label={filas.map((f) => `${f.nombre}: ${f.valor}%`).join(". ")} className="h-40 w-full">
        <ResponsiveContainer>
          <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 40, left: 0, bottom: 4 }}>
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis type="category" dataKey="nombre" width={120} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <Bar dataKey="valor" radius={4} isAnimationActive={false} barSize={22}>
              {filas.map((f) => <Cell key={f.nombre} fill={f.color} />)}
              <LabelList dataKey="valor" position="right" formatter={(v) => `${v}%`} style={{ fontSize: 12, fontWeight: 700 }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
