import { useState } from "react";
import { evaluacionApi } from "../../api/evaluacionApi";
import { mensajeError } from "../../utils/errores";

const PRIORIDAD = { alta: "Prioridad alta", media: "Prioridad media", baja: "Prioridad baja" };

/**
 * Lista de tareas. Con cuenta, cada marca se guarda en el servidor (sobrevive a recargas y dispositivos).
 * Con `soloLocal` (invitado) no hay a dónde guardar: el avance solo cambia en este dispositivo.
 */
export default function RecommendationsChecklist({ evaluacion, onUpdated, soloLocal = false }) {
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const recs = evaluacion.recomendaciones;
  const hechas = recs.filter((r) => r.completada).length;

  async function alternar(rec) {
    const completada = !rec.completada;
    setError(null);
    if (soloLocal) {
      onUpdated({ ...evaluacion, recomendaciones: recs.map((r) => (r.id === rec.id ? { ...r, completada } : r)) });
      return;
    }
    setGuardando(true);
    // Actualización optimista: la marca responde al instante aunque la señal sea lenta.
    onUpdated({
      ...evaluacion,
      recomendaciones: recs.map((r) => (r.id === rec.id ? { ...r, completada } : r)),
    });
    try {
      onUpdated(await evaluacionApi.marcarRecomendacion(evaluacion.id, rec.id, completada));
    } catch (e) {
      onUpdated(evaluacion); // revierte
      setError(mensajeError(e, "No pudimos guardar tu avance. Inténtalo de nuevo."));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <p className="text-sm font-bold" aria-live="polite">
          {hechas} de {recs.length} tareas completadas
        </p>
      </div>
      <div
        role="progressbar"
        aria-label="Avance de tareas"
        aria-valuemin={0}
        aria-valuemax={recs.length}
        aria-valuenow={hechas}
        className="mb-4 h-2 overflow-hidden rounded-full bg-slate-300"
      >
        <div className="h-full bg-riesgo-bajo transition-[width] motion-reduce:transition-none" style={{ width: `${(hechas / recs.length) * 100}%` }} />
      </div>

      {error && (
        <p role="alert" className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-900">
          {error}
        </p>
      )}

      <ul className="grid gap-2">
        {recs.map((rec) => (
          <li key={rec.id}>
            <label className="flex min-h-[56px] cursor-pointer items-start gap-3 rounded-lg border-2 border-slate-200 bg-white p-3 has-[:checked]:border-riesgo-bajo/50 has-[:checked]:bg-green-50">
              <input
                type="checkbox"
                checked={rec.completada}
                onChange={() => alternar(rec)}
                disabled={guardando}
                className="mt-0.5 h-6 w-6 shrink-0 accent-[#2F7D4F]"
              />
              <span className="min-w-0">
                <span className={`block font-bold ${rec.completada ? "text-slate-500 line-through" : ""}`}>{rec.titulo}</span>
                <span className="mt-0.5 block text-sm text-slate-600">{rec.detalle}</span>
                <span className={`mt-1 block text-xs font-bold ${rec.prioridad === "alta" ? "text-riesgo-alto" : "text-slate-600"}`}>
                  {PRIORIDAD[rec.prioridad]}
                </span>
              </span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}
