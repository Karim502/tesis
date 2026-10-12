import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { NIVEL_CLASE, NIVEL_COLOR, pct } from "../../utils/riesgo";

const ZONAS = [
  { name: "Bajo", v: 35, fill: NIVEL_COLOR.Bajo },
  { name: "Medio", v: 30, fill: NIVEL_COLOR.Medio },
  { name: "Alto", v: 35, fill: NIVEL_COLOR.Alto },
];

/**
 * ResponsiveContainer inyecta width/height a este hijo (Recharts 2.x), de modo que el radio
 * se calcula en píxeles y el semicírculo siempre cabe en pantallas pequeñas.
 */
function Semicirculo({ width, height, valor }) {
  const r = Math.min(width / 2, height) - 8;
  const cx = width / 2;
  const cy = height - 4;
  const v = Math.min(Math.max(valor, 0), 98.5); // evita que la aguja se salga del arco
  const aguja = [{ v }, { v: 1.5 }, { v: 100 - v - 1.5 }]; // 2ª capa: solo el segmento central es visible

  const comun = { startAngle: 180, endAngle: 0, cx, cy, dataKey: "v", stroke: "none", isAnimationActive: false };
  return (
    <PieChart width={width} height={height}>
      <Pie data={ZONAS} innerRadius={r * 0.7} outerRadius={r} {...comun}>
        {ZONAS.map((z) => (
          <Cell key={z.name} fill={z.fill} />
        ))}
      </Pie>
      <Pie data={aguja} innerRadius={r * 0.6} outerRadius={r * 1.04} {...comun}>
        <Cell fill="transparent" />
        <Cell fill="#14232B" />
        <Cell fill="transparent" />
      </Pie>
    </PieChart>
  );
}

export default function RiskGauge({ probabilidad, nivel }) {
  const valor = pct(probabilidad);
  return (
    <div>
      <div
        role="img"
        aria-label={`Medidor de riesgo fiscal: ${valor} por ciento, nivel ${nivel}`}
        className="relative mx-auto w-full max-w-sm"
      >
        <ResponsiveContainer width="100%" aspect={2}>
          <Semicirculo valor={valor} />
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 text-center">
          <p className="text-4xl font-bold leading-none">{valor}%</p>
          <p className={`mt-1 text-lg font-bold ${NIVEL_CLASE[nivel]}`}>Riesgo {nivel.toLowerCase()}</p>
        </div>
      </div>
      <ul className="mt-4 flex justify-center gap-4 text-xs text-slate-700">
        {ZONAS.map((z) => (
          <li key={z.name} className="flex items-center gap-1.5">
            <span aria-hidden="true" className="h-3 w-3 rounded-sm" style={{ background: z.fill }} />
            {z.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
