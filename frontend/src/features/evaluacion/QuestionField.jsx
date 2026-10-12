export default function QuestionField({ pregunta, valor = "", onChange, error, inputId }) {
  return (
    <div className="flex flex-col gap-4">
      {/* Muestra el bloque (Ej: BLOQUE I: Perfil y Capacidad Operativa) */}
      {pregunta.bloque && (
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
          {pregunta.bloque}
        </span>
      )}
      
      {/* Texto de la pregunta */}
      <label htmlFor={inputId} className="text-lg font-medium leading-snug text-slate-900">
        {pregunta.texto}
      </label>

      {/* Dibuja un Desplegable o una Caja de Texto según el tipo */}
      {pregunta.tipo === "select" ? (
        <select
          id={inputId}
          value={valor}
          onChange={(e) => onChange(e.target.value)}
          className={`min-h-[52px] w-full rounded-lg border-2 bg-slate-50 p-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-accent ${
            error ? "border-red-500 focus:border-red-500 focus:ring-red-500" : "border-slate-300 focus:border-accent"
          }`}
        >
          <option value="" disabled>
            -- Seleccione una opción --
          </option>
          {pregunta.opciones?.map((opcion, index) => (
            <option key={index} value={opcion}>
              {opcion}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={inputId}
          type={pregunta.tipo === "number" ? "number" : "text"}
          value={valor}
          onChange={(e) => onChange(e.target.value)}
          className={`min-h-[52px] w-full rounded-lg border-2 bg-slate-50 p-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-accent ${
            error ? "border-red-500 focus:border-red-500 focus:ring-red-500" : "border-slate-300 focus:border-accent"
          }`}
          placeholder="Escribe tu respuesta..."
        />
      )}

      {/* Mensaje de error si intenta avanzar sin responder */}
      {error && (
        <p className="text-sm font-semibold text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}