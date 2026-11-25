import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Lista paginada genérica (offset/limit) con filtros. Cada consulta cancela la anterior y descarta respuestas tardías;
 * mientras recarga conserva los datos previos (sin parpadeo) y, si la página deja de existir, vuelve a la última.
 *   fetcher(params, {signal}) -> {items, total}
 */
export function usePagina(fetcher, filtros, tamanoInicial = 20) {
  const [pagina, setPagina] = useState(1);
  const [tamano, setTamano] = useState(tamanoInicial);
  const [state, setState] = useState({ items: [], total: 0, loading: true, error: null });
  const reqId = useRef(0);
  const abortRef = useRef(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const clave = JSON.stringify(filtros);

  // Cambiar un filtro vuelve a la página 1.
  useEffect(() => setPagina(1), [clave]);

  const cargar = useCallback(async () => {
    const id = ++reqId.current;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetcherRef.current({ ...JSON.parse(clave), limit: tamano, offset: (pagina - 1) * tamano }, { signal: ctrl.signal });
      if (id !== reqId.current) return;
      const paginas = Math.max(1, Math.ceil(data.total / tamano));
      if (pagina > paginas) return setPagina(paginas);
      setState({ items: data.items, total: data.total, loading: false, error: null });
    } catch (error) {
      if (error?.name === "AbortError" || id !== reqId.current) return;
      setState({ items: [], total: 0, loading: false, error });
    }
  }, [clave, pagina, tamano]);

  useEffect(() => { cargar(); }, [cargar]);
  useEffect(() => () => abortRef.current?.abort(), []);

  // `recargar` es ESTABLE y siempre ejecuta la versión más reciente de `cargar`. Si un componente guardara una copia vieja
  // (p. ej. dentro de un callback de un diálogo), recargaría con filtros antiguos y pisaría la búsqueda actual.
  const cargarRef = useRef(cargar);
  cargarRef.current = cargar;
  const recargar = useCallback(() => cargarRef.current(), []);

  return {
    ...state, pagina, setPagina, tamano,
    cambiarTamano: (n) => { setTamano(n); setPagina(1); },
    totalPaginas: Math.max(1, Math.ceil(state.total / tamano)),
    recargar,
  };
}

/** Valor con retraso: evita una petición por cada tecla en los campos de texto. */
export function useDebounce(valor, ms = 400) {
  const [v, setV] = useState(valor);
  useEffect(() => {
    const t = setTimeout(() => setV(valor), ms);
    return () => clearTimeout(t);
  }, [valor, ms]);
  return v;
}
