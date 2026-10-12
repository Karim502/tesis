export const validarRespuesta = (pregunta, valor) => {
  if (valor === undefined || valor === null || valor === "") {
    return "Por favor, selecciona una respuesta antes de continuar.";
  }
  return null;
};

export const normalizarRespuestas = (preguntas, respuestas) => {
  // Quitamos las llaves {} para evitar el doble encapsulamiento
  return respuestas; 
};