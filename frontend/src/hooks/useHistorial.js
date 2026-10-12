import { useCallback, useEffect, useState } from "react";
import { evaluacionApi } from "../api/evaluacionApi";

/**
 * Fuente del estado "completado vs. pendiente":
 *   data === []  -> pendiente (aún no hay evaluaciones)
 *   data.length  -> completado (data[0] es la más reciente)
 */
export function useHistorial() {
  const [state, setState] = useState({ data: null, loading: true, error: null });

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      setState({ data: await evaluacionApi.historial(), loading: false, error: null });
    } catch (error) {
      setState({ data: null, loading: false, error });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  /** Reemplaza una evaluación (p. ej. tras marcar una tarea) sin recargar todo. */
  const replaceEvaluacion = useCallback((ev) => {
    setState((s) => ({ ...s, data: s.data?.map((x) => (x.id === ev.id ? ev : x)) ?? s.data }));
  }, []);

  return { ...state, reload: load, replaceEvaluacion };
}
