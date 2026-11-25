/** Traduce un ApiError a un mensaje claro para el usuario. */
export function mensajeError(err, porDefecto = "Ocurrió un problema. Inténtalo de nuevo.") {
  if (err?.code === "NETWORK_ERROR") return "Sin conexión. Revisa tu internet e inténtalo de nuevo.";
  if (err?.status === 401) return "Tu sesión expiró. Vuelve a iniciar sesión.";
  if (err?.status === 403) return "No tienes permiso para ver esta sección.";
  if (err?.status === 404) return "No encontramos este registro. Puede que ya no exista.";
  if (err?.code === "INVALID_RANGE") return "La fecha de inicio no puede ser posterior a la fecha fin.";
  if (err?.code === "INVALID_RISK_RANGE") return "La probabilidad mínima no puede ser mayor que la máxima.";
  if (err?.status === 422) return "Algún dato no es válido. Revísalo e inténtalo de nuevo.";
  if (err?.code === "INVALID_ANSWERS") return "Hay respuestas que no son válidas. Revísalas e inténtalo de nuevo.";
  return porDefecto;
}
