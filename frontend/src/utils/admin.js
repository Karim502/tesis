// Etiquetas y formateadores del panel del administrador.

export const ACCIONES = {
  LOGIN: "Inicio de sesión",
  EVALUACION_CONSULTADA: "Revisó una evaluación",
  AUDITORIA_ACTUALIZADA: "Actualizó estado/notas",
  AUDITOR_CREADO: "Creó un auditor",
  AUDITOR_ACTUALIZADO: "Editó un auditor",
  AUDITOR_SUSPENDIDO: "Suspendió un auditor",
  AUDITOR_REACTIVADO: "Reactivó un auditor",
  AUDITOR_ELIMINADO: "Eliminó un auditor",
  MODELO_REENTRENAMIENTO: "Lanzó un reentrenamiento",
  MODELO_ACTIVADO: "Activó un modelo",
};

export const ROL_CORTO = { ADMIN: "Admin", AUDITOR: "Auditor", DUENO_MYPE: "Dueño MYPE" };

export const ESTADO_MODELO = {
  ENTRENANDO: { label: "Entrenando", clase: "bg-sky-100 text-sky-900" },
  CANDIDATO: { label: "Candidato", clase: "bg-amber-100 text-amber-900" },
  ACTIVO: { label: "Activo", clase: "bg-emerald-100 text-emerald-900" },
  ARCHIVADO: { label: "Archivado", clase: "bg-slate-200 text-slate-800" },
  FALLIDO: { label: "Fallido", clase: "bg-red-100 text-red-900" },
};

// Etapas del job, en orden: sirven para mostrar el avance mientras entrena.
export const ETAPAS = ["en cola", "validando datos", "entrenando", "evaluando", "guardando"];

// El backend entrega fechas ISO; si vienen sin zona se interpretan como UTC.
const aDate = (iso) => new Date(/([zZ]|[+-]\d\d:?\d\d)$/.test(iso) ? iso : `${iso}Z`);

export function fechaHora(iso) {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-PE", {
    dateStyle: "short", timeStyle: "short", timeZone: "America/Lima",
  }).format(aDate(iso));
}

export const porcentaje = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

/** Resumen legible del `detalle` de un evento (sin mostrar JSON crudo). */
export function describirDetalle(accion, d) {
  if (!d) return "";
  switch (accion) {
    case "AUDITORIA_ACTUALIZADA": {
      const partes = [];
      if (d.estado) partes.push(`estado ${d.estado.antes} → ${d.estado.despues}`);
      if (d.notas_modificadas) partes.push("notas editadas");
      return partes.join(" · ");
    }
    case "AUDITOR_CREADO":
    case "AUDITOR_SUSPENDIDO":
    case "AUDITOR_REACTIVADO":
    case "AUDITOR_ELIMINADO":
      return d.email ?? "";
    case "AUDITOR_ACTUALIZADO":
      return `${d.email ?? ""}${d.campos?.length ? ` (${d.campos.join(", ")})` : ""}`;
    case "MODELO_REENTRENAMIENTO":
      return `v${d.version} · ${d.origen}${d.activar_si_mejora ? " · auto-activar si mejora" : ""}`;
    case "MODELO_ACTIVADO":
      return `v${d.version}${d.desde_version ? ` (antes v${d.desde_version})` : ""}${d.automatica ? " · automática" : ""}`;
    default:
      return "";
  }
}

export function describirRecurso(tipo, id) {
  if (!tipo || id == null) return "—";
  return `${{ evaluacion: "Evaluación", usuario: "Usuario", modelo: "Modelo" }[tipo] ?? tipo} #${id}`;
}
