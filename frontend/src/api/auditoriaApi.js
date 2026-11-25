import { apiFetch } from "./client";

/**
 * GET /api/evaluaciones — padrón con filtros opcionales (los vacíos no se envían).
 * Fechas en formato YYYY-MM-DD (calendario de Perú); `fechaFin` es inclusiva.
 * `probMin`/`probMax` son porcentajes 0–100 (inclusivos). Paginación por `limit`/`offset`.
 */
export function listarPadron(
  { estado, sector, probMin, probMax, fechaInicio, fechaFin, limit = 20, offset = 0 } = {},
  { signal } = {},
) {
  const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (estado) q.set("estado_auditoria", estado);
  if (sector) q.set("sector_economico", sector);
  if (probMin !== "" && probMin != null) q.set("probabilidad_min", String(probMin));
  if (probMax !== "" && probMax != null) q.set("probabilidad_max", String(probMax));
  if (fechaInicio) q.set("fecha_inicio", fechaInicio);
  if (fechaFin) q.set("fecha_fin", fechaFin);
  return apiFetch(`/evaluaciones?${q}`, { signal });
}

/**
 * PATCH /api/evaluaciones/{id}/auditoria — actualización parcial: solo se envían los campos que cambiaron.
 * `cambios` puede traer `estado` y/o `notas` (cadena vacía = borrar la nota).
 * Devuelve la evaluación ya actualizada; lanza ApiError con status 401/403/404/422 o NETWORK_ERROR.
 */
export function actualizarAuditoria(id, { estado, notas }) {
  const body = {};
  if (estado !== undefined) body.estado_auditoria = estado;
  if (notas !== undefined) body.notas_auditor = notas || null;
  return apiFetch(`/evaluaciones/${id}/auditoria`, { method: "PATCH", body });
}

/** GET /api/evaluaciones/{id}/comparativo-sectorial — probabilidades en fracción 0–1. */
export const obtenerComparativo = (id, { signal } = {}) =>
  apiFetch(`/evaluaciones/${id}/comparativo-sectorial`, { signal });

/** GET /api/evaluaciones/{id}/shap — contribuciones SHAP locales en JSON. */
export const obtenerShap = (id, { maxDisplay = 12, signal } = {}) =>
  apiFetch(`/evaluaciones/${id}/shap?max_display=${maxDisplay}`, { signal });
