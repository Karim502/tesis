import { useCallback, useEffect, useRef, useState } from "react";
import { listarPadron } from "../api/auditoriaApi";

const VACIOS = { estado: "", sector: "", probMin: "", probMax: "", fechaInicio: "", fechaFin: "" };

const num = (v) => (v === "" || v == null ? null : Number(v));

/**
 * Estado del padrón del auditor: filtros, paginación numerada (offset/limit) y actualización en sitio.
 * Cada consulta cancela la anterior (AbortController) y `reqId` descarta cualquier respuesta tardía,
 * de modo que nunca se muestra el resultado de un filtro o de una página anterior.
 */
export function usePadron() {
  const [filtros, setFiltros] = useState(VACIOS);
  const [pagina, setPagina] = useState(1); // base 1
  const [tamano, setTamano] = useState(20);
  const [state, setState] = useState({ items: [], total: 0, loading: true, error: null });
  const reqId = useRef(0);
  const abortRef = useRef(null);

  const min = num(filtros.probMin);
  const max = num(filtros.probMax);
  const fueraDeRango = (v) => v != null && (Number.isNaN(v) || v < 0 || v > 100);
  const rangoInvalido = !!(filtros.fechaInicio && filtros.fechaFin && filtros.fechaInicio > filtros.fechaFin);
  const riesgoInvalido = fueraDeRango(min) || fueraDeRango(max) || (min != null && max != null && min > max);
  const hayFiltros = Object.values(filtros).some((v) => v !== "");

  const cargar = useCallback(async () => {
    const id = ++reqId.current;
    abortRef.current?.abort();
    if (rangoInvalido || riesgoInvalido) {
      // No se consulta con un rango imposible; el formulario ya muestra el aviso.
      setState((s) => ({ ...s, loading: false, error: null }));
      return;
    }
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await listarPadron(
        { ...filtros, limit: tamano, offset: (pagina - 1) * tamano },
        { signal: ctrl.signal },
      );
      if (id !== reqId.current) return;
      const paginas = Math.max(1, Math.ceil(data.total / tamano));
      if (pagina > paginas) { setPagina(paginas); return; } // la página dejó de existir (p. ej. tras filtrar)
      setState({ items: data.items, total: data.total, loading: false, error: null });
    } catch (error) {
      if (error?.name === "AbortError" || id !== reqId.current) return;
      setState({ items: [], total: 0, loading: false, error });
    }
  }, [filtros, pagina, tamano, rangoInvalido, riesgoInvalido]);

  useEffect(() => {
    cargar();
  }, [cargar]);
  useEffect(() => () => abortRef.current?.abort(), []);

  /** Reemplaza un registro tras guardarlo, sin volver a consultar toda la lista. */
  const replaceItem = useCallback((actualizado) => {
    setState((s) => ({ ...s, items: s.items.map((i) => (i.id === actualizado.id ? actualizado : i)) }));
  }, []);

  // Cambiar un filtro vuelve a la página 1.
  const setFiltro = useCallback((campo, valor) => {
    setFiltros((f) => ({ ...f, [campo]: valor }));
    setPagina(1);
  }, []);
  const aplicar = useCallback((parcial) => {
    setFiltros((f) => ({ ...f, ...parcial }));
    setPagina(1);
  }, []);
  const limpiar = useCallback(() => { setFiltros(VACIOS); setPagina(1); }, []);
  const cambiarTamano = useCallback((n) => { setTamano(n); setPagina(1); }, []);

  const totalPaginas = Math.max(1, Math.ceil(state.total / tamano));

  return {
    filtros, setFiltro, aplicar, limpiar, rangoInvalido, riesgoInvalido, hayFiltros,
    items: state.items, total: state.total, loading: state.loading, error: state.error,
    pagina, setPagina, tamano, cambiarTamano, totalPaginas,
    reload: cargar, replaceItem,
  };
}
