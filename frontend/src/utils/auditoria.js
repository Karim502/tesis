// Códigos que usa la API (enum EstadoAuditoria del backend) y su etiqueta/estilo en pantalla.
export const ESTADOS = [
  { value: "PENDIENTE", label: "Pendiente", badge: "bg-amber-100 text-amber-900" },
  { value: "EN_REVISION", label: "En investigación", badge: "bg-sky-100 text-sky-900" },
  { value: "CERRADO", label: "Cerrado", badge: "bg-green-100 text-green-900" },
];

export const ESTADO_POR_VALOR = Object.fromEntries(ESTADOS.map((e) => [e.value, e]));

export const NOTAS_MAX = 2000; // mismo tope que el backend (schemas/auditoria.py)

// Tamaños de página del padrón.
export const TAMANOS_PAGINA = [10, 20, 50];

// Convención de color de la gráfica SHAP. El pedido original fue: verde = contribución POSITIVA al riesgo,
// rojo = NEGATIVA. Es lo contrario de la convención habitual (rojo = sube el riesgo). Para invertirla basta
// intercambiar estos dos valores.
export const SHAP_COLOR_POSITIVO = "#2F7D4F"; // verde: empuja la probabilidad de riesgo hacia ARRIBA
export const SHAP_COLOR_NEGATIVO = "#B3261E"; // rojo: empuja la probabilidad de riesgo hacia ABAJO
