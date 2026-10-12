export const NIVEL_COLOR = { Bajo: "#2F7D4F", Medio: "#A16207", Alto: "#B3261E" };
export const NIVEL_CLASE = { Bajo: "text-riesgo-bajo", Medio: "text-riesgo-medio", Alto: "text-riesgo-alto" };

export const pct = (probabilidad) => Math.round(probabilidad * 100);

export const formatFecha = (iso, opts = { day: "numeric", month: "short", year: "numeric" }) =>
  new Date(iso).toLocaleDateString("es-PE", opts);
