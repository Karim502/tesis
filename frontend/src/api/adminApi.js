import { apiFetch } from "./client";

/** Construye ?a=1&b=2 omitiendo vacíos. */
const qs = (obj) => {
  const q = new URLSearchParams();
  Object.entries(obj).forEach(([k, v]) => v !== "" && v != null && q.set(k, String(v)));
  const s = q.toString();
  return s ? `?${s}` : "";
};

export const adminApi = {
  // ── Eje A · Auditores
  listarAuditores: (f, { signal } = {}) => apiFetch(`/admin/auditores${qs(f)}`, { signal }),
  crearAuditor: (data) => apiFetch("/admin/auditores", { method: "POST", body: data }),
  actualizarAuditor: (id, data) => apiFetch(`/admin/auditores/${id}`, { method: "PATCH", body: data }),
  eliminarAuditor: (id) => apiFetch(`/admin/auditores/${id}`, { method: "DELETE" }),

  // ── Eje B · MLOps
  modelos: ({ signal } = {}) => apiFetch("/admin/modelos", { signal }),
  /** `archivo` (File) es opcional: sin él se usa el dataset por defecto del servidor. Responde 202 al instante. */
  reentrenar: ({ archivo, activarSiMejora }) => {
    const fd = new FormData();
    if (archivo) fd.append("lote", archivo);
    fd.append("activar_si_mejora", activarSiMejora ? "true" : "false");
    return apiFetch("/admin/modelos/reentrenar", { method: "POST", body: fd });
  },
  activarModelo: (id) => apiFetch(`/admin/modelos/${id}/activar`, { method: "POST" }),

  // ── Eje C · Monitoreo
  logs: (f, { signal } = {}) => apiFetch(`/admin/logs${qs(f)}`, { signal }),
  health: ({ signal } = {}) => apiFetch("/admin/health", { signal }),
};
