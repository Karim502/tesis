import { useCallback, useEffect, useRef, useState } from "react";
import { adminApi } from "../../api/adminApi";
import ErrorBanner from "../../components/ui/ErrorBanner";
import Spinner from "../../components/ui/Spinner";
import { fechaHora } from "../../utils/admin";
import { mensajeError } from "../../utils/errores";
import { BTN_SECUNDARIO } from "./Modal";

// El estado se comunica con TEXTO + símbolo, no solo con color.
const ESTADO = {
  ok: { texto: "Operativo", simbolo: "●", clase: "text-emerald-800 bg-emerald-50 border-emerald-300" },
  advertencia: { texto: "Atención", simbolo: "▲", clase: "text-amber-900 bg-amber-50 border-amber-300" },
  error: { texto: "Caído", simbolo: "✖", clase: "text-red-900 bg-red-50 border-red-300" },
};
const REFRESCO_MS = 30_000;

/** Eje C: health check de los servicios (se vuelve a comprobar cada 30 s mientras la pestaña está abierta). */
export default function HealthPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);
  const ctrl = useRef(null);

  const comprobar = useCallback(async () => {
    ctrl.current?.abort();
    const c = (ctrl.current = new AbortController());
    setCargando(true);
    try {
      setData(await adminApi.health({ signal: c.signal }));
      setError(null);
    } catch (e) {
      if (e?.name !== "AbortError") setError(e);
    } finally {
      if (!c.signal.aborted) setCargando(false);
    }
  }, []);

  useEffect(() => {
    comprobar();
    const t = setInterval(comprobar, REFRESCO_MS);
    return () => { clearInterval(t); ctrl.current?.abort(); };
  }, [comprobar]);

  if (!data && cargando) return <Spinner label="Comprobando servicios…" />;
  const g = data && ESTADO[data.estado_general];

  return (
    <section aria-labelledby="t-health">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="t-health" className="text-lg font-bold">Estado de los servicios</h2>
          {data && <p className="text-sm text-slate-600">Última comprobación: {fechaHora(data.revisado_en)}</p>}
        </div>
        <button type="button" className={BTN_SECUNDARIO} onClick={comprobar} disabled={cargando}>{cargando ? "Comprobando…" : "Volver a comprobar"}</button>
      </div>

      {error && <ErrorBanner message={mensajeError(error, "No se pudo comprobar el estado del sistema.")} onRetry={comprobar} />}

      {g && (
        <>
          <p role="status" className={`mb-4 rounded-xl border p-4 font-bold ${g.clase}`}>
            <span aria-hidden="true">{g.simbolo} </span>Estado general: {g.texto}
          </p>
          <ul className="grid gap-3 sm:grid-cols-2">
            {data.servicios.map((s) => {
              const e = ESTADO[s.estado];
              return (
                <li key={s.nombre} className={`rounded-xl border p-4 ${e.clase}`}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-bold text-ink">{s.nombre}</p>
                    <span className="text-xs font-bold"><span aria-hidden="true">{e.simbolo} </span>{e.texto}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-800">{s.detalle}</p>
                  {s.latencia_ms != null && <p className="mt-1 text-xs text-slate-600">Respuesta en {s.latencia_ms} ms</p>}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
