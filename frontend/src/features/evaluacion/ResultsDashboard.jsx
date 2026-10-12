import { useState } from "react";
import { Link } from "react-router-dom";
import { formatFecha } from "../../utils/riesgo";
import RecommendationsChecklist from "./RecommendationsChecklist";
import RiskGauge from "./RiskGauge";
import RiskHistoryChart from "./RiskHistoryChart";

function Tarjeta({ titulo, children, className = "" }) {
  return (
    <section className={`rounded-xl bg-white p-5 shadow-sm ${className}`}>
      <h2 className="mb-4 text-lg font-bold">{titulo}</h2>
      {children}
    </section>
  );
}

/**
 * Props:
 *  - evaluaciones: lista (la primera es la más reciente). El invitado pasa una sola.
 *  - invitado: true => sin PDF, sin historial y con el checklist solo en este dispositivo.
 *  - onNuevaEvaluacion: (solo invitado) reinicia el diagnóstico para la siguiente persona.
 */
export default function ResultsDashboard({ evaluaciones, usuario, onEvaluacionActualizada, invitado = false, onNuevaEvaluacion }) {
  const actual = evaluaciones[0]; // la más reciente
  const [pdf, setPdf] = useState({ cargando: false, error: null });

  async function descargarPdf() {
    setPdf({ cargando: true, error: null });
    try {
      // Carga diferida: jsPDF solo se descarga cuando el usuario lo pide (ahorra datos móviles).
      const { generarConstanciaPdf } = await import("./generarConstanciaPdf");
      await generarConstanciaPdf({ usuario, evaluacion: actual });
      setPdf({ cargando: false, error: null });
    } catch {
      setPdf({ cargando: false, error: "No pudimos generar el PDF. Inténtalo de nuevo." });
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Tarjeta titulo={`Tu riesgo fiscal al ${formatFecha(actual.creado_en)}`}>
        <RiskGauge probabilidad={actual.probabilidad} nivel={actual.nivel_riesgo} />
        <p className="mt-4 text-center text-sm text-slate-600">
          Puntaje de cumplimiento: <strong>{actual.score}/100</strong>
        </p>
      </Tarjeta>

      <Tarjeta titulo="Tu plan de acción">
        <RecommendationsChecklist evaluacion={actual} onUpdated={onEvaluacionActualizada} soloLocal={invitado} />
      </Tarjeta>

      {/* El invitado tiene una sola evaluación: el gráfico de evolución no aplica. */}
      {!invitado && (
        <Tarjeta titulo="Cómo ha cambiado tu riesgo" className="md:col-span-2">
          <RiskHistoryChart evaluaciones={evaluaciones} />
        </Tarjeta>
      )}

      {invitado ? (
        <div className="grid gap-3 md:col-span-2 md:grid-cols-2 md:items-center">
          {/* Sin botón de PDF: solo un aviso discreto con la vía para obtenerlo. */}
          <p className="text-sm text-slate-600">
            <Link to="/login" className="font-bold text-accent underline">
              Regístrate
            </Link>{" "}
            para descargar tu reporte en PDF
          </p>
          <button
            type="button"
            onClick={onNuevaEvaluacion}
            className="flex min-h-[52px] items-center justify-center rounded-lg border-2 border-accent px-4 font-bold text-accent"
          >
            Hacer otro diagnóstico
          </button>
        </div>
      ) : (
        <div className="grid gap-3 md:col-span-2 md:grid-cols-2">
          <button
            type="button"
            onClick={descargarPdf}
            disabled={pdf.cargando}
            className="flex min-h-[52px] items-center justify-center gap-2 rounded-lg bg-accent px-4 font-bold text-white hover:bg-[#174B48] disabled:cursor-progress disabled:opacity-70"
          >
            {pdf.cargando && (
              <span aria-hidden="true" className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white motion-reduce:animate-none" />
            )}
            {pdf.cargando ? "Generando PDF…" : "Descargar constancia PDF"}
          </button>
          <Link
            to="/dashboard-mype/evaluacion"
            className="flex min-h-[52px] items-center justify-center rounded-lg border-2 border-accent px-4 font-bold text-accent"
          >
            Hacer una nueva evaluación
          </Link>
          {pdf.error && (
            <p role="alert" className="text-sm font-bold text-riesgo-alto md:col-span-2">
              {pdf.error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
