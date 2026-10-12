// El invitado no tiene cuenta ni historial: su resultado vive solo en esta pestaña (sessionStorage),
// para que recargar la página no lo pierda. Se borra al cerrar la pestaña o con "Nueva evaluación".
const KEY = "cu01:resultado-invitado";

export function guardarResultadoInvitado(resultado) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(resultado));
  } catch {
    /* sin almacenamiento: el resultado igual se muestra desde el estado de React */
  }
}

export function leerResultadoInvitado() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) ?? "null");
  } catch {
    return null;
  }
}

export function borrarResultadoInvitado() {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* nada que borrar */
  }
}
