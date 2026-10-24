import { NIVEL_CLASE, formatFecha, pct } from "../../utils/riesgo";
import EstadoBadge from "./EstadoBadge";

const FILA = "md:grid md:grid-cols-[minmax(0,2.2fr)_minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)] md:items-center md:gap-4";
const FECHA_HORA = { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" };

/** Cada fila es un botón: se opera con teclado y con el pulgar. En móvil se apila; desde md es una tabla. */
export default function PadronLista({ items, onSelect, seleccionadoId, etiquetaSector = (v) => v }) {
  return (
    <div className="overflow-hidden rounded-xl bg-white shadow-sm">
      <div className={`hidden border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-bold text-slate-600 ${FILA}`} aria-hidden="true">
        <span>MYPE</span><span>Fecha</span><span>Riesgo</span><span>Estado</span>
      </div>
      <ul className="divide-y divide-slate-200">
        {items.map((it) => (
          <li key={it.id}>
            <button type="button" onClick={() => onSelect(it)} aria-haspopup="dialog"
              className={`w-full px-4 py-3 text-left hover:bg-slate-50 focus-visible:outline focus-visible:outline-4 focus-visible:-outline-offset-4 focus-visible:outline-accent/40 ${FILA} ${seleccionadoId === it.id ? "bg-accent/5" : ""}`}>
              <span className="flex items-start justify-between gap-3 md:block">
                <span className="min-w-0">
                  <span className="block truncate font-bold">{it.mype_nombre}</span>
                  <span className="block truncate text-sm text-slate-600">
                    {it.mype_email}{it.sector_economico ? ` · ${etiquetaSector(it.sector_economico)}` : ""}
                  </span>
                </span>
                <span className="md:hidden"><EstadoBadge estado={it.estado_auditoria} /></span>
              </span>
              <span className="mt-1 block text-sm text-slate-600 md:mt-0">{formatFecha(it.creado_en, FECHA_HORA)}</span>
              <span className="block text-sm md:mt-0">
                <span className={`font-bold ${NIVEL_CLASE[it.nivel_riesgo]}`}>{it.nivel_riesgo}</span>{" "}
                <span className="text-slate-600">({pct(it.probabilidad)}%)</span>
              </span>
              <span className="hidden md:block"><EstadoBadge estado={it.estado_auditoria} /></span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
