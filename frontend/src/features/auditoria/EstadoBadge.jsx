import { ESTADO_POR_VALOR } from "../../utils/auditoria";

export default function EstadoBadge({ estado }) {
  const e = ESTADO_POR_VALOR[estado] ?? { label: estado, badge: "bg-slate-100 text-slate-800" };
  return <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-bold ${e.badge}`}>{e.label}</span>;
}
