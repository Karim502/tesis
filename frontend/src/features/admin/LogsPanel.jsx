import { useState } from "react";
import { adminApi } from "../../api/adminApi";
import ErrorBanner from "../../components/ui/ErrorBanner";
import Spinner from "../../components/ui/Spinner";
import { useDebounce, usePagina } from "../../hooks/usePagina";
import { ACCIONES, ROL_CORTO, describirDetalle, describirRecurso, fechaHora } from "../../utils/admin";
import { mensajeError } from "../../utils/errores";
import Paginacion from "../auditoria/Paginacion";
import { BTN_SECUNDARIO, CAMPO } from "./Modal";

const VACIO = { accion: "", usuario: "", rol: "", fechaInicio: "", fechaFin: "" };

/** Eje C: bitácora de auditoría (quién inició sesión, qué evaluación revisó y cuándo) con filtros y paginación. */
export default function LogsPanel() {
  const [f, setF] = useState(VACIO);
  const usuario = useDebounce(f.usuario.trim(), 400);
  const rangoInvalido = !!(f.fechaInicio && f.fechaFin && f.fechaInicio > f.fechaFin);
  const filtros = { accion: f.accion, usuario, rol: f.rol, fecha_inicio: f.fechaInicio, fecha_fin: rangoInvalido ? "" : f.fechaFin };
  const lista = usePagina(rangoInvalido ? async () => ({ items: [], total: 0 }) : adminApi.logs, filtros);
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const hayFiltros = Object.values(f).some(Boolean);

  return (
    <section aria-labelledby="t-logs">
      <h2 id="t-logs" className="sr-only">Bitácora de auditoría</h2>
      <form onSubmit={(e) => e.preventDefault()} aria-label="Filtros de la bitácora" className="mb-4 grid gap-3 rounded-xl bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-5">
        <div>
          <label htmlFor="lg-accion" className="mb-1 block text-sm font-bold">Acción</label>
          <select id="lg-accion" value={f.accion} onChange={set("accion")} className={CAMPO}>
            <option value="">Todas</option>
            {Object.entries(ACCIONES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="lg-usuario" className="mb-1 block text-sm font-bold">Usuario (correo)</label>
          <input id="lg-usuario" type="search" value={f.usuario} onChange={set("usuario")} className={CAMPO} maxLength={100} placeholder="ej. aldo@" />
        </div>
        <div>
          <label htmlFor="lg-rol" className="mb-1 block text-sm font-bold">Rol</label>
          <select id="lg-rol" value={f.rol} onChange={set("rol")} className={CAMPO}>
            <option value="">Todos</option>
            {Object.entries(ROL_CORTO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="lg-desde" className="mb-1 block text-sm font-bold">Desde</label>
          <input id="lg-desde" type="date" value={f.fechaInicio} max={f.fechaFin || undefined} onChange={set("fechaInicio")} className={CAMPO} aria-invalid={rangoInvalido} />
        </div>
        <div>
          <label htmlFor="lg-hasta" className="mb-1 block text-sm font-bold">Hasta</label>
          <input id="lg-hasta" type="date" value={f.fechaFin} min={f.fechaInicio || undefined} onChange={set("fechaFin")} className={CAMPO} aria-invalid={rangoInvalido} />
        </div>
        <div className="flex flex-wrap gap-2 sm:col-span-2 lg:col-span-5">
          <button type="button" className={BTN_SECUNDARIO} disabled={!hayFiltros} onClick={() => setF(VACIO)}>Limpiar filtros</button>
          <button type="button" className={BTN_SECUNDARIO} onClick={lista.recargar} disabled={lista.loading}>Actualizar</button>
          {rangoInvalido && <p role="alert" className="self-center text-sm font-bold text-riesgo-alto">La fecha de inicio no puede ser posterior a la fecha fin.</p>}
        </div>
      </form>

      {lista.error && <ErrorBanner message={mensajeError(lista.error, "No pudimos cargar la bitácora.")} onRetry={lista.recargar} />}
      {!lista.error && lista.loading && lista.items.length === 0 && <Spinner label="Cargando bitácora…" />}

      {!lista.error && !(lista.loading && lista.items.length === 0) && (
        lista.items.length === 0 ? (
          <p className="rounded-xl bg-white p-6 text-center font-bold shadow-sm">{hayFiltros ? "Ningún evento coincide con los filtros." : "Aún no hay eventos registrados."}</p>
        ) : (
          <div aria-busy={lista.loading} className={lista.loading ? "opacity-60 transition-opacity" : ""}>
            <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
              <table className="w-full min-w-[820px] text-left text-sm">
                <caption className="sr-only">Eventos de auditoría, del más reciente al más antiguo</caption>
                <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-600">
                  <tr><th scope="col" className="p-3">Fecha (Lima)</th><th scope="col" className="p-3">Usuario</th><th scope="col" className="p-3">Acción</th>
                    <th scope="col" className="p-3">Recurso</th><th scope="col" className="p-3">Detalle</th><th scope="col" className="p-3">IP</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {lista.items.map((e) => (
                    <tr key={e.id}>
                      <td className="whitespace-nowrap p-3 text-slate-700">{fechaHora(e.creado_en)}</td>
                      <td className="p-3">
                        <p className="font-bold">{e.usuario_email ?? "—"}</p>
                        {e.usuario_rol && <p className="text-xs text-slate-600">{ROL_CORTO[e.usuario_rol] ?? e.usuario_rol}</p>}
                      </td>
                      <td className="p-3">{ACCIONES[e.accion] ?? e.accion}</td>
                      <td className="whitespace-nowrap p-3">{describirRecurso(e.recurso_tipo, e.recurso_id)}</td>
                      <td className="max-w-[260px] p-3 text-slate-700">{describirDetalle(e.accion, e.detalle)}</td>
                      <td className="p-3 font-mono text-xs text-slate-600">{e.ip ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-sm text-slate-600" aria-live="polite">{lista.total} evento{lista.total === 1 ? "" : "s"}</p>
            <Paginacion pagina={lista.pagina} totalPaginas={lista.totalPaginas} tamano={lista.tamano} onPagina={lista.setPagina} onTamano={lista.cambiarTamano} deshabilitado={lista.loading} />
          </div>
        )
      )}
    </section>
  );
}
