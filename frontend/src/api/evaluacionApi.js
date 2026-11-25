import { apiFetch } from "./client";

export const evaluacionApi = {
  cuestionario: () => apiFetch("/evaluacion/cuestionario"),
  crear: (respuestas) => apiFetch("/evaluacion", { method: "POST", body: { respuestas } }),
  // Público: sin cookie de sesión, el servidor no emite token y guarda la evaluación como invitado.
  crearInvitado: (respuestas) => apiFetch("/evaluacion/invitado", { method: "POST", body: { respuestas } }),
  historial: () => apiFetch("/evaluacion/historial"),
  marcarRecomendacion: (evaluacionId, recId, completada) =>
    apiFetch(`/evaluacion/${evaluacionId}/recomendaciones/${encodeURIComponent(recId)}`, {
      method: "PATCH",
      body: { completada },
    }),
};
