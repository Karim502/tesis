import { useState } from "react";
import { adminApi } from "../../api/adminApi";
import ErrorBanner from "../../components/ui/ErrorBanner";
import Spinner from "../../components/ui/Spinner";
import { useDebounce, usePagina } from "../../hooks/usePagina";
import { fechaHora } from "../../utils/admin";
import { mensajeError } from "../../utils/errores";
import Paginacion from "../auditoria/Paginacion";
import AuditorFormModal from "./AuditorFormModal";
import ConfirmDialog from "./ConfirmDialog";
import { BTN_PRIMARIO, CAMPO } from "./Modal";

const ACC = "min-h-[44px] rounded-lg px-3 text-sm font-bold underline decoration-2 underline-offset-2 hover:bg-slate-100";

/** Eje A: CRUD de cuentas de Auditor (listar, crear, editar, suspender/reactivar y eliminar). */
export default function AuditoresPanel() {
  const [q, setQ] = useState("");
  const [estado, setEstado] = useState("");
  const qFinal = useDebounce(q.trim(), 400);
  const lista = usePagina(adminApi.listarAuditores, { q: qFinal, estado });

  const [formulario, setFormulario] = useState(null);   // null | {} (alta) | auditor (edición)
  const [confirmar, setConfirmar] = useState(null);     // { tipo: "suspender"|"reactivar"|"eliminar", auditor }
  const [aviso, setAviso] = useState(null);

  async function ejecutar() {
    const { tipo, auditor } = confirmar;
    if (tipo === "eliminar") await adminApi.eliminarAuditor(auditor.id);
    else await adminApi.actualizarAuditor(auditor.id, { activo: tipo === "reactivar" });
    setAviso(`${{ eliminar: "Se eliminó", suspender: "Se suspendió", reactivar: "Se reactivó" }[tipo]} la cuenta de ${auditor.nombre}.`);
    lista.recargar();
  }

  const hayFiltros = q || estado;
  return (
    <section aria-labelledby="t-auditores">
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="min-w-[200px] flex-1">
          <label htmlFor="aud-q" className="mb-1 block text-sm font-bold">Buscar</label>
          <input id="aud-q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nombre o correo" className={CAMPO} maxLength={100} />
        </div>
        <div>
          <label htmlFor="aud-estado" className="mb-1 block text-sm font-bold">Estado</label>
          <select id="aud-estado" value={estado} onChange={(e) => setEstado(e.target.value)} className={CAMPO}>
            <option value="">Todos</option><option value="activo">Activos</option><option value="suspendido">Suspendidos</option>
          </select>
        </div>
        <button type="button" className={BTN_PRIMARIO} onClick={() => setFormulario({})}>+ Nuevo auditor</button>
      </div>

      <h2 id="t-auditores" className="sr-only">Cuentas de auditores</h2>
      <p role="status" className="mb-2 min-h-[1.25rem] text-sm font-bold text-emerald-800">{aviso}</p>

      {lista.error && <ErrorBanner message={mensajeError(lista.error, "No pudimos cargar los auditores.")} onRetry={lista.recargar} />}
      {!lista.error && lista.loading && lista.items.length === 0 && <Spinner label="Cargando auditores…" />}

      {!lista.error && !(lista.loading && lista.items.length === 0) && (
        lista.items.length === 0 ? (
          <div className="rounded-xl bg-white p-6 text-center shadow-sm">
            <p className="font-bold">{hayFiltros ? "Ningún auditor coincide con la búsqueda." : "Aún no hay auditores. Crea el primero."}</p>
          </div>
        ) : (
          <div aria-busy={lista.loading} className={lista.loading ? "opacity-60 transition-opacity" : ""}>
            <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
              <table className="w-full min-w-[720px] text-left text-sm">
                <caption className="sr-only">Auditores registrados</caption>
                <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-600">
                  <tr><th scope="col" className="p-3">Auditor</th><th scope="col" className="p-3">Estado</th><th scope="col" className="p-3">Último acceso</th>
                    <th scope="col" className="p-3 text-right">Revisiones</th><th scope="col" className="p-3 text-right">Acciones</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {lista.items.map((a) => (
                    <tr key={a.id}>
                      <td className="p-3"><p className="font-bold">{a.nombre}</p><p className="text-slate-600">{a.email}</p></td>
                      <td className="p-3">
                        <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${a.activo ? "bg-emerald-100 text-emerald-900" : "bg-red-100 text-red-900"}`}>
                          {a.activo ? "Activo" : "Suspendido"}
                        </span>
                      </td>
                      <td className="p-3 text-slate-700">{fechaHora(a.ultimo_login)}</td>
                      <td className="p-3 text-right tabular-nums">{a.revisiones}</td>
                      <td className="p-3">
                        <div className="flex flex-wrap justify-end gap-1">
                          <button type="button" className={`${ACC} text-accent`} onClick={() => setFormulario(a)} aria-label={`Editar a ${a.nombre}`}>Editar</button>
                          <button type="button" className={`${ACC} text-amber-800`} onClick={() => setConfirmar({ tipo: a.activo ? "suspender" : "reactivar", auditor: a })}
                            aria-label={`${a.activo ? "Suspender" : "Reactivar"} a ${a.nombre}`}>{a.activo ? "Suspender" : "Reactivar"}</button>
                          <button type="button" className={`${ACC} text-riesgo-alto`} onClick={() => setConfirmar({ tipo: "eliminar", auditor: a })} aria-label={`Eliminar a ${a.nombre}`}>Eliminar</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-sm text-slate-600" aria-live="polite">{lista.total} auditor{lista.total === 1 ? "" : "es"}</p>
            <Paginacion pagina={lista.pagina} totalPaginas={lista.totalPaginas} tamano={lista.tamano} onPagina={lista.setPagina} onTamano={lista.cambiarTamano} deshabilitado={lista.loading} />
          </div>
        )
      )}

      {formulario && (
        <AuditorFormModal auditor={formulario.id ? formulario : null} onClose={() => setFormulario(null)}
          onSaved={() => { setAviso(formulario.id ? "Auditor actualizado." : "Auditor creado."); setFormulario(null); lista.recargar(); }} />
      )}

      {confirmar && (
        <ConfirmDialog
          titulo={{ suspender: "Suspender acceso", reactivar: "Reactivar acceso", eliminar: "Eliminar cuenta" }[confirmar.tipo]}
          confirmar={{ suspender: "Suspender", reactivar: "Reactivar", eliminar: "Eliminar definitivamente" }[confirmar.tipo]}
          peligro={confirmar.tipo !== "reactivar"} onConfirm={ejecutar} onClose={() => setConfirmar(null)}>
          {confirmar.tipo === "suspender" && <p><b>{confirmar.auditor.nombre}</b> perderá el acceso de inmediato, incluso con la sesión abierta. Puedes reactivarlo cuando quieras.</p>}
          {confirmar.tipo === "reactivar" && <p><b>{confirmar.auditor.nombre}</b> podrá volver a iniciar sesión.</p>}
          {confirmar.tipo === "eliminar" && (
            <p>Se eliminará la cuenta de <b>{confirmar.auditor.nombre}</b> ({confirmar.auditor.email}). Sus revisiones y su historial en la bitácora se conservan, pero la acción <b>no se puede deshacer</b>. Si solo quieres bloquear el acceso, usa «Suspender».</p>
          )}
        </ConfirmDialog>
      )}
    </section>
  );
}
