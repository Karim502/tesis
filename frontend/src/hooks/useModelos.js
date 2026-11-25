import { useCallback, useEffect, useRef, useState } from "react";
import { adminApi } from "../api/adminApi";

const SONDEO_MS = 2500;

/**
 * Estado del ciclo de vida del modelo + "Forzar reentrenamiento".
 *
 * Flujo: POST /admin/modelos/reentrenar responde 202 de inmediato (el entrenamiento corre en segundo plano en el servidor).
 * Mientras alguna versión esté ENTRENANDO, este hook consulta GET /admin/modelos cada 2,5 s y se detiene solo al terminar.
 * Al recargar la página retoma el sondeo, porque el estado vive en la BD y no en el navegador.
 */
export function useModelos() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [lanzando, setLanzando] = useState(false);
  const [errorAccion, setErrorAccion] = useState(null);
  const [avisos, setAvisos] = useState([]);
  const ctrl = useRef(null);

  const cargar = useCallback(async () => {
    ctrl.current?.abort();
    const c = (ctrl.current = new AbortController());
    try {
      const d = await adminApi.modelos({ signal: c.signal });
      setData(d);
      setError(null);
    } catch (e) {
      if (e?.name !== "AbortError") setError(e);
    } finally {
      if (!c.signal.aborted) setCargando(false);
    }
  }, []);

  useEffect(() => { cargar(); return () => ctrl.current?.abort(); }, [cargar]);

  // Sondeo mientras haya un entrenamiento en curso.
  const entrenando = data?.entrenando === true;
  useEffect(() => {
    if (!entrenando) return undefined;
    const t = setInterval(cargar, SONDEO_MS);
    return () => clearInterval(t);
  }, [entrenando, cargar]);

  const reentrenar = useCallback(async (opciones) => {
    setLanzando(true);
    setErrorAccion(null);
    setAvisos([]);
    try {
      await adminApi.reentrenar(opciones); // 202: ya quedó en cola
      await cargar();                      // aparece la nueva fila ENTRENANDO y arranca el sondeo
      return true;
    } catch (e) {
      setErrorAccion(e);                   // 409 ya hay uno en curso, 422 lote inválido, 413 muy grande…
      return false;
    } finally {
      setLanzando(false);
    }
  }, [cargar]);

  // Lanza el error al llamador (el diálogo de confirmación lo muestra y sigue abierto).
  const activar = useCallback(async (id) => {
    setErrorAccion(null);
    const r = await adminApi.activarModelo(id);
    setAvisos(r.advertencias);
    await cargar();
  }, [cargar]);

  return { data, error, cargando, entrenando, lanzando, errorAccion, avisos, reentrenar, activar, recargar: cargar };
}
