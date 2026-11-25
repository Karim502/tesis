import { useEffect, useMemo, useRef, useState } from "react";
import { evaluacionApi } from "../../api/evaluacionApi";
import ErrorBanner from "../../components/ui/ErrorBanner";
import Spinner from "../../components/ui/Spinner";
import { usePadron } from "../../hooks/usePadron";
import { mensajeError } from "../../utils/errores";
import AuditoriaDrawer from "./AuditoriaDrawer";
import FiltrosAvanzados from "./FiltrosAvanzados";
import Paginacion from "./Paginacion";
import PadronLista from "./PadronLista";

/** Panel del auditor: filtros avanzados + lista paginada + drawer de auditoría (comparativo, SHAP, estado y notas). */
export default function PadronAuditor() {
  const padron = usePadron();
  const [seleccionado, setSeleccionado] = useState(null);
  const [preguntas, setPreguntas] = useState(null);

  // El catálogo de preguntas da el texto real de las respuestas y las opciones del filtro de sector.
  // Si falla, el panel sigue funcionando (sin filtro de sector y con identificadores crudos).
  useEffect(() => {
    evaluacionApi.cuestionario().then((r) => setPreguntas(r.preguntas)).catch(() => setPreguntas(null));
  }, []);

  const sectores = useMemo(
    () => preguntas?.find((p) => p.id === "sector_economico")?.opciones ?? [],
    [preguntas],
  );
  const etiquetaSector = (v) => sectores.find((s) => s.valor === v)?.etiqueta?.split(" (")[0] ?? v;

  const { items, total, loading, error, filtros } = padron;
  const invalido = padron.rangoInvalido || padron.riesgoInvalido;

  // Con un filtro activo, guardar puede sacar al registro del filtro (p. ej. "Pendiente" -> "Cerrado").
  // La fila se actualiza al instante y la lista se vuelve a consultar AL CERRAR el panel, para que nada
  // desaparezca mientras el auditor trabaja y, al terminar, lista y contador sean los reales.
  const refrescarAlCerrar = useRef(false);

  function alGuardar(actualizado) {
    padron.replaceItem(actualizado);
    setSeleccionado(actualizado);
    if (filtros.estado && actualizado.estado_auditoria !== filtros.estado) refrescarAlCerrar.current = true;
  }

  function cerrarPanel() {
    setSeleccionado(null);
    if (refrescarAlCerrar.current) {
      refrescarAlCerrar.current = false;
      padron.reload();
    }
  }

  const desde = total === 0 ? 0 : (padron.pagina - 1) * padron.tamano + 1;
  const hasta = (padron.pagina - 1) * padron.tamano + items.length;

  return (
    <>
      <h1 className="mb-1 text-2xl font-bold">Padrón de evaluaciones</h1>
      <p className="mb-4 text-sm text-slate-600" aria-live="polite">
        {!loading && !error && !invalido && `Mostrando ${desde}–${hasta} de ${total}`}
      </p>

      <FiltrosAvanzados filtros={filtros} onChange={padron.setFiltro} onAplicar={padron.aplicar} onLimpiar={padron.limpiar}
        sectores={sectores} rangoInvalido={padron.rangoInvalido} riesgoInvalido={padron.riesgoInvalido} hayFiltros={padron.hayFiltros} />

      <div className="mt-4">
        {error && <ErrorBanner message={mensajeError(error, "No pudimos cargar el padrón.")} onRetry={padron.reload} />}
        {!error && !invalido && loading && items.length === 0 && <Spinner label="Cargando evaluaciones…" />}

        {!error && !invalido && !(loading && items.length === 0) && (
          items.length === 0 ? (
            <div className="rounded-xl bg-white p-6 text-center shadow-sm">
              <p className="font-bold">{padron.hayFiltros ? "Ninguna evaluación coincide con los filtros." : "Aún no hay evaluaciones de MYPE."}</p>
              {padron.hayFiltros && (
                <button type="button" onClick={padron.limpiar} className="mt-3 min-h-[44px] rounded-lg border-2 border-accent px-4 font-bold text-accent">
                  Limpiar filtros
                </button>
              )}
            </div>
          ) : (
            <div aria-busy={loading} className={loading ? "opacity-50 transition-opacity" : ""}>
              <PadronLista items={items} onSelect={setSeleccionado} seleccionadoId={seleccionado?.id} etiquetaSector={etiquetaSector} />
              <Paginacion pagina={padron.pagina} totalPaginas={padron.totalPaginas} tamano={padron.tamano}
                onPagina={padron.setPagina} onTamano={padron.cambiarTamano} deshabilitado={loading} />
            </div>
          )
        )}
      </div>

      {seleccionado && (
        <AuditoriaDrawer key={seleccionado.id} item={seleccionado} preguntas={preguntas}
          onClose={cerrarPanel} onSaved={alGuardar} />
      )}
    </>
  );
}
