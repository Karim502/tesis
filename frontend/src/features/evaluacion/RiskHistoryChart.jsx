import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatFecha, pct } from "../../utils/riesgo";

const MAX_PUNTOS = 12; // en pantallas pequeñas más puntos serían ilegibles

export default function RiskHistoryChart({ evaluaciones }) {
  // El historial llega de más reciente a más antigua; el gráfico necesita orden cronológico.
  const datos = [...evaluaciones]
    .reverse()
    .slice(-MAX_PUNTOS)
    .map((e, i) => ({
      idx: i + 1,
      riesgo: pct(e.probabilidad),
      corta: formatFecha(e.creado_en, { day: "numeric", month: "short" }),
      larga: formatFecha(e.creado_en),
      nivel: e.nivel_riesgo,
    }));

  if (datos.length < 2) {
    return (
      <p className="rounded-lg bg-slate-100 p-4 text-sm text-slate-700">
        Con tu próxima evaluación verás aquí cómo cambia tu riesgo en el tiempo.
      </p>
    );
  }

  return (
    <div role="img" aria-label={`Evolución de tu riesgo en ${datos.length} evaluaciones`} className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={datos} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#d5dde0" />
          <XAxis
            dataKey="idx"
            type="number"
            domain={[1, datos.length]}
            ticks={datos.map((d) => d.idx)}
            interval="preserveStartEnd"
            tickFormatter={(i) => datos[i - 1]?.corta}
            tick={{ fontSize: 11 }}
          />
          <YAxis domain={[0, 100]} ticks={[0, 35, 65, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} width={44} />
          <ReferenceLine y={35} stroke="#2F7D4F" strokeDasharray="4 4" />
          <ReferenceLine y={65} stroke="#B3261E" strokeDasharray="4 4" />
          <Tooltip
            labelFormatter={(i) => datos[i - 1]?.larga}
            formatter={(valor, _n, { payload }) => [`${valor}% (${payload.nivel})`, "Riesgo"]}
          />
          <Line type="monotone" dataKey="riesgo" stroke="#1F5F5B" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
