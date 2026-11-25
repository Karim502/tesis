import { useEffect, useId, useRef, useState } from "react";
import { actualizarAuditoria } from "../../api/auditoriaApi";
import { ESTADOS, NOTAS_MAX } from "../../utils/auditoria";
import { mensajeError } from "../../utils/errores";
import { formatFecha } from "../../utils/riesgo";
import DatosEvaluacion from "./DatosEvaluacion";
import ComparativoSectorial from "./ComparativoSectorial";
import EstadoBadge from "./EstadoBadge";
import ShapWaterfallChart from "./ShapWaterfallChart";

const FOCUSABLES = 'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Panel lateral (pantalla completa en móvil) para revisar una MYPE y registrar su estado y notas.
 * Incluye datos de la MYPE, comparativo sectorial, explicabilidad SHAP y el formulario de gestión
 * (estado + notas internas) conectado al PATCH. `children` queda como espacio extra opcional.
 */
export default function AuditoriaDrawer({ item, preguntas, onClose, onSaved, children }) {
  const uid = useId();
  const panelRef = useRef(null);
  const cerrarRef = useRef(null);

  const [estado, setEstado] = useState(item.estado_auditoria);
  const [notas, setNotas] = useState(item.notas_auditor ?? "");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [guardado, setGuardado] = useState(false);

  // "Con cambios" = distinto de lo último guardado en el servidor.
  const dirty = estado !== item.estado_auditoria || notas.trim() !== (item.notas_auditor ?? "");

  // Accesibilidad de diálogo: foco al abrir, bloqueo del scroll de fondo y foco de vuelta al cerrar.
  useEffect(() => {
    const previo = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    cerrarRef.current?.focus();
    return () => {
      document.body.style.overflow = overflow;
      previo?.focus?.();
    };
  }, []);

  function solicitarCierre() {
    if (dirty && !window.confirm("Tienes cambios sin guardar. ¿Quieres descartarlos?")) return;
    onClose();
  }

  function onKeyDown(e) {
    if (e.key === "Escape") return solicitarCierre();
    if (e.key !== "Tab") return;
    // Mantiene el foco dentro del panel mientras está abierto.
    const f = panelRef.current.querySelectorAll(FOCUSABLES);
    const primero = f[0], ultimo = f[f.length - 1];
    if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); ultimo.focus(); }
    else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primero.focus(); }
  }

  async function guardar(e) {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    setGuardado(false);
    try {
      // PATCH parcial: solo viajan los campos que realmente cambiaron.
      const cambios = {};
      if (estado !== item.estado_auditoria) cambios.estado = estado;
      if (notas.trim() !== (item.notas_auditor ?? "")) cambios.notas = notas.trim();
      const actualizado = await actualizarAuditoria(item.id, cambios);
      onSaved(actualizado);                         // el padrón y el panel pasan a mostrar lo guardado
      setNotas(actualizado.notas_auditor ?? "");    // sincroniza (el servidor recorta espacios)
      setGuardado(true);
    } catch (err) {
      // Lo escrito se conserva: el auditor puede reintentar sin perder su nota.
      setError(mensajeError(err, "No pudimos guardar los cambios. Inténtalo de nuevo."));
    } finally {
      setGuardando(false);
    }
  }

  const tituloId = `${uid}-titulo`;
  return (
    <div className="fixed inset-0 z-40" onKeyDown={onKeyDown}>
      <div className="absolute inset-0 bg-black/40" onClick={solicitarCierre} aria-hidden="true" />
      <div ref={panelRef} role="dialog" aria-modal="true" aria-labelledby={tituloId}
        className="absolute inset-y-0 right-0 flex w-full flex-col bg-white shadow-xl md:max-w-2xl">
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div className="min-w-0">
            <h2 id={tituloId} className="truncate text-lg font-bold">{item.mype_nombre}</h2>
            <div className="mt-1"><EstadoBadge estado={item.estado_auditoria} /></div>
          </div>
          <button ref={cerrarRef} type="button" onClick={solicitarCierre}
            className="min-h-[44px] shrink-0 rounded-lg px-3 font-bold text-accent underline focus-visible:outline focus-visible:outline-4 focus-visible:outline-accent/40">
            Cerrar
          </button>
        </header>

        <div className="flex-1 space-y-6 overflow-y-auto px-4 py-4">
          <DatosEvaluacion item={item} preguntas={preguntas} />
          <ComparativoSectorial evaluacionId={item.id} />
          <ShapWaterfallChart evaluacionId={item.id} />
          {children}

          <form id={`${uid}-form`} onSubmit={guardar} className="space-y-4 border-t border-slate-200 pt-5" noValidate>
            <h3 className="text-base font-bold">Gestión de auditoría</h3>
            <div>
              <label htmlFor={`${uid}-estado`} className="mb-1 block text-sm font-bold">Estado</label>
              <select id={`${uid}-estado`} value={estado} disabled={guardando}
                onChange={(e) => { setEstado(e.target.value); setGuardado(false); }}
                className="min-h-[48px] w-full rounded-lg border-2 border-slate-300 bg-white px-3 text-base focus-visible:border-accent focus-visible:outline focus-visible:outline-4 focus-visible:outline-accent/30">
                {ESTADOS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor={`${uid}-notas`} className="mb-1 block text-sm font-bold">Notas internas de auditoría</label>
              <textarea id={`${uid}-notas`} rows={6} maxLength={NOTAS_MAX} value={notas} disabled={guardando}
                onChange={(e) => { setNotas(e.target.value); setGuardado(false); }}
                aria-describedby={`${uid}-ayuda`}
                className="w-full rounded-lg border-2 border-slate-300 bg-white p-3 text-base focus-visible:border-accent focus-visible:outline focus-visible:outline-4 focus-visible:outline-accent/30" />
              <p id={`${uid}-ayuda`} className="mt-1 flex justify-between gap-3 text-xs text-slate-600">
                <span>Solo las ven los auditores; el dueño de la MYPE no tiene acceso.</span>
                <span aria-hidden="true">{notas.length}/{NOTAS_MAX}</span>
              </p>
            </div>

            {item.auditado_en && (
              <p className="text-xs text-slate-600">
                Última modificación: {item.auditado_por_nombre ?? "un auditor"} ·{" "}
                {formatFecha(item.auditado_en, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
              </p>
            )}

            {error && <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
            <p role="status" aria-live="polite" className={guardado ? "text-sm font-bold text-riesgo-bajo" : "sr-only"}>
              {guardado ? "Cambios guardados." : ""}
            </p>
          </form>
        </div>

        <footer className="border-t border-slate-200 bg-slate-50 px-4 py-3">
          <button type="submit" form={`${uid}-form`} disabled={!dirty || guardando}
            className="flex min-h-[52px] w-full items-center justify-center gap-2 rounded-lg bg-accent font-bold text-white hover:bg-[#174B48] disabled:cursor-not-allowed disabled:opacity-50">
            {guardando && <span aria-hidden="true" className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white motion-reduce:animate-none" />}
            {guardando ? "Guardando…" : "Guardar cambios"}
          </button>
        </footer>
      </div>
    </div>
  );
}
