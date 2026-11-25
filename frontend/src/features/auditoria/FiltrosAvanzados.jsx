import { useEffect, useId, useState } from "react";
import { ESTADOS } from "../../utils/auditoria";

const CAMPO = "min-h-[44px] w-full rounded-lg border-2 border-slate-300 bg-white px-3 text-base focus-visible:border-accent focus-visible:outline focus-visible:outline-4 focus-visible:outline-accent/30";
const DEBOUNCE_MS = 400;

/** Campo numérico con debounce: escribe en local y avisa al padre cuando el usuario hace una pausa. */
function CampoPorcentaje({ id, label, valor, onChange, invalido, describedBy }) {
  const [local, setLocal] = useState(valor);
  useEffect(() => setLocal(valor), [valor]); // sincroniza al limpiar filtros o aplicar un preset
  useEffect(() => {
    if (local === valor) return;
    const t = setTimeout(() => onChange(local), DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [local]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-bold">{label}</label>
      <div className="relative">
        <input id={id} type="number" inputMode="numeric" min={0} max={100} step={1} placeholder="0–100" value={local}
          onChange={(e) => setLocal(e.target.value)} aria-invalid={invalido} aria-describedby={describedBy}
          className={`${CAMPO} pr-9`} />
        <span aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-500">%</span>
      </div>
    </div>
  );
}

/**
 * Barra de filtros del auditor: estado, sector, rango de probabilidad de riesgo (%) y fechas.
 * `sectores` = [{valor, etiqueta}] sacado del cuestionario; si no carga, el filtro de sector se oculta.
 */
export default function FiltrosAvanzados({ filtros, onChange, onAplicar, onLimpiar, sectores, rangoInvalido, riesgoInvalido, hayFiltros }) {
  const id = useId();
  const riesgoAltoActivo = filtros.probMin === "80" && filtros.probMax === "";
  return (
    <form onSubmit={(e) => e.preventDefault()} className="rounded-xl bg-white p-4 shadow-sm" aria-label="Filtros del padrón">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor={`${id}-estado`} className="mb-1 block text-sm font-bold">Estado de auditoría</label>
          <select id={`${id}-estado`} value={filtros.estado} onChange={(e) => onChange("estado", e.target.value)} className={CAMPO}>
            <option value="">Todos</option>
            {ESTADOS.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
          </select>
        </div>
        {sectores?.length > 0 && (
          <div>
            <label htmlFor={`${id}-sector`} className="mb-1 block text-sm font-bold">Sector económico</label>
            <select id={`${id}-sector`} value={filtros.sector} onChange={(e) => onChange("sector", e.target.value)} className={CAMPO}>
              <option value="">Todos</option>
              {sectores.map((s) => <option key={s.valor} value={s.valor}>{s.etiqueta.split(" (")[0]}</option>)}
            </select>
          </div>
        )}
        <CampoPorcentaje id={`${id}-pmin`} label="Riesgo mínimo" valor={filtros.probMin} invalido={riesgoInvalido}
          describedBy={riesgoInvalido ? `${id}-riesgo` : undefined} onChange={(v) => onChange("probMin", v)} />
        <CampoPorcentaje id={`${id}-pmax`} label="Riesgo máximo" valor={filtros.probMax} invalido={riesgoInvalido}
          describedBy={riesgoInvalido ? `${id}-riesgo` : undefined} onChange={(v) => onChange("probMax", v)} />
        <div>
          <label htmlFor={`${id}-desde`} className="mb-1 block text-sm font-bold">Desde</label>
          <input id={`${id}-desde`} type="date" value={filtros.fechaInicio} max={filtros.fechaFin || undefined}
            onChange={(e) => onChange("fechaInicio", e.target.value)} className={CAMPO}
            aria-invalid={rangoInvalido} aria-describedby={rangoInvalido ? `${id}-rango` : undefined} />
        </div>
        <div>
          <label htmlFor={`${id}-hasta`} className="mb-1 block text-sm font-bold">Hasta</label>
          <input id={`${id}-hasta`} type="date" value={filtros.fechaFin} min={filtros.fechaInicio || undefined}
            onChange={(e) => onChange("fechaFin", e.target.value)} className={CAMPO}
            aria-invalid={rangoInvalido} aria-describedby={rangoInvalido ? `${id}-rango` : undefined} />
        </div>
        <div className="flex items-end sm:col-span-2 lg:col-span-2 lg:justify-end gap-2">
          <button type="button" aria-pressed={riesgoAltoActivo}
            onClick={() => onAplicar(riesgoAltoActivo ? { probMin: "" } : { probMin: "80", probMax: "" })}
            className={`min-h-[44px] flex-1 rounded-lg border-2 px-4 font-bold lg:flex-none ${riesgoAltoActivo ? "border-riesgo-alto bg-riesgo-alto text-white" : "border-riesgo-alto text-riesgo-alto"}`}>
            Riesgo alto (≥ 80%)
          </button>
          <button type="button" onClick={onLimpiar} disabled={!hayFiltros}
            className="min-h-[44px] flex-1 rounded-lg border-2 border-accent px-4 font-bold text-accent disabled:cursor-not-allowed disabled:opacity-40 lg:flex-none">
            Limpiar filtros
          </button>
        </div>
      </div>
      {riesgoInvalido && (
        <p id={`${id}-riesgo`} role="alert" className="mt-3 text-sm font-bold text-riesgo-alto">
          Indica porcentajes entre 0 y 100, con el mínimo menor o igual al máximo.
        </p>
      )}
      {rangoInvalido && (
        <p id={`${id}-rango`} role="alert" className="mt-3 text-sm font-bold text-riesgo-alto">
          La fecha de inicio no puede ser posterior a la fecha fin.
        </p>
      )}
    </form>
  );
}
