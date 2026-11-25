import { NIVEL_CLASE, formatFecha, pct } from "../../utils/riesgo";

/** Convierte el valor guardado (p. ej. "nrus") en lo que ve la persona ("Nuevo RUS") usando el catálogo. */
function valorLegible(pregunta, valor) {
  if (!pregunta) return String(valor);
  if (pregunta.tipo === "opcion") return pregunta.opciones.find((o) => o.valor === valor)?.etiqueta ?? String(valor);
  if (pregunta.tipo === "numero") return `${pregunta.prefijo ? `${pregunta.prefijo} ` : ""}${Number(valor).toLocaleString("es-PE")}`;
  return String(valor);
}

export default function DatosEvaluacion({ item, preguntas }) {
  const porId = Object.fromEntries((preguntas ?? []).map((p) => [p.id, p]));
  return (
    <section aria-labelledby="datos-titulo">
      <h3 id="datos-titulo" className="mb-2 text-base font-bold">Datos de la MYPE</h3>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-slate-600">Titular</dt><dd className="font-bold">{item.mype_nombre}</dd>
        <dt className="text-slate-600">Correo</dt><dd className="break-all">{item.mype_email}</dd>
        <dt className="text-slate-600">Evaluada el</dt>
        <dd>{formatFecha(item.creado_en, { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })}</dd>
        <dt className="text-slate-600">Riesgo</dt>
        <dd><span className={`font-bold ${NIVEL_CLASE[item.nivel_riesgo]}`}>{item.nivel_riesgo}</span> · {pct(item.probabilidad)}% de incumplimiento</dd>
        <dt className="text-slate-600">Cumplimiento</dt><dd>{item.score}/100</dd>
      </dl>

      <h3 className="mb-2 mt-5 text-base font-bold">Respuestas del cuestionario</h3>
      <dl className="grid gap-3 text-sm">
        {Object.entries(item.respuestas).map(([id, valor]) => (
          <div key={id}>
            <dt className="text-slate-600">{porId[id]?.texto ?? id}</dt>
            <dd className="font-bold">{valorLegible(porId[id], valor)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
