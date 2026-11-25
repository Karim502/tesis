import { useCallback, useEffect, useState } from "react";

/**
 * Carga un recurso con cancelación: al cambiar `deps` o desmontar, la petición anterior se aborta
 * y su respuesta jamás pisa a la nueva. `fn` recibe la señal de aborto.
 */
export function useCarga(fn, deps) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setState({ data: null, loading: true, error: null });
    fn(ctrl.signal)
      .then((data) => !ctrl.signal.aborted && setState({ data, loading: false, error: null }))
      .catch((error) => {
        if (error?.name === "AbortError" || ctrl.signal.aborted) return;
        setState({ data: null, loading: false, error });
      });
    return () => ctrl.abort();
  }, [...deps, intento]); // eslint-disable-line react-hooks/exhaustive-deps

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);
  return { ...state, reintentar };
}
