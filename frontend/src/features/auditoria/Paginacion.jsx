import { TAMANOS_PAGINA } from "../../utils/auditoria";

const BTN = "min-h-[44px] min-w-[44px] rounded-lg border-2 border-accent px-3 font-bold text-accent disabled:cursor-not-allowed disabled:opacity-40";

/** Paginación numerada: Anterior / "Página X de Y" / Siguiente + tamaño de página. */
export default function Paginacion({ pagina, totalPaginas, tamano, onPagina, onTamano, deshabilitado }) {
  return (
    <nav aria-label="Paginación del padrón" className="mt-4 flex flex-wrap items-center justify-between gap-3">
      <label className="flex items-center gap-2 text-sm">
        <span className="font-bold">Por página</span>
        <select value={tamano} onChange={(e) => onTamano(Number(e.target.value))}
          className="min-h-[44px] rounded-lg border-2 border-slate-300 bg-white px-2">
          {TAMANOS_PAGINA.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </label>
      <div className="flex items-center gap-2">
        <button type="button" className={BTN} disabled={deshabilitado || pagina <= 1} onClick={() => onPagina(pagina - 1)}>
          <span aria-hidden="true">←</span> Anterior
        </button>
        <span className="px-1 text-sm" aria-live="polite">Página <b>{pagina}</b> de <b>{totalPaginas}</b></span>
        <button type="button" className={BTN} disabled={deshabilitado || pagina >= totalPaginas} onClick={() => onPagina(pagina + 1)}>
          Siguiente <span aria-hidden="true">→</span>
        </button>
      </div>
    </nav>
  );
}
