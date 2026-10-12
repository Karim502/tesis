import { apiFetch } from "./client";

export const evaluacionApi = {
  cuestionario: () => apiFetch("/v1/evaluacion/cuestionario"),
  crear: (respuestas) => apiFetch("/v1/evaluacion", { method: "POST", body: { respuestas } }),
  // Público: sin cookie de sesión, el servidor no emite token y guarda la evaluación como invitado.
  crearInvitado: (respuestas) => apiFetch("/v1/evaluacion/invitado", { method: "POST", body: { respuestas } }),
  historial: () => apiFetch("/v1/evaluacion/historial"),
  marcarRecomendacion: (evaluacionId, recId, completada) =>
    apiFetch(`/v1/evaluacion/${evaluacionId}/recomendaciones/${encodeURIComponent(recId)}`, {
      method: "PATCH",
      body: { completada },
    }),
};
