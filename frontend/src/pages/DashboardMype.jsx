import { Link } from "react-router-dom";
import ErrorBanner from "../components/ui/ErrorBanner";
import MypeLayout from "../components/MypeLayout";
import Spinner from "../components/ui/Spinner";
import ResultsDashboard from "../features/evaluacion/ResultsDashboard";
import { useAuth } from "../context/AuthContext";
import { useHistorial } from "../hooks/useHistorial";
import { mensajeError } from "../utils/errores";
import { formatFecha } from "../utils/riesgo";

function Pendiente() {
  return (
    <section className="rounded-xl bg-white p-6 text-center shadow-sm">
      <h2 className="text-xl font-bold">Aún no hiciste tu evaluación</h2>
      <p className="mx-auto mt-2 max-w-md text-slate-600">
        Responde unas preguntas cortas sobre tu negocio y conoce tu nivel de riesgo fiscal, con un plan de pasos para mejorarlo.
        Si te interrumpes, retomas donde te quedaste.
      </p>
      <Link
        to="/dashboard-mype/evaluacion"
        className="mt-5 inline-flex min-h-[52px] items-center justify-center rounded-lg bg-accent px-6 font-bold text-white hover:bg-[#174B48]"
      >
        Empezar evaluación
      </Link>
    </section>
  );
}

export default function DashboardMype() {
  const { user } = useAuth();
  const { data, loading, error, reload, replaceEvaluacion } = useHistorial();
  const completado = !!data?.length;

  return (
    <MypeLayout>
      <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1">
        <h1 className="text-2xl font-bold">Mi negocio</h1>
        {data && (
          <span
            className={`rounded-full px-3 py-1 text-xs font-bold ${
              completado ? "bg-green-100 text-green-900" : "bg-amber-100 text-amber-900"
            }`}
          >
            {completado ? `Evaluación completada el ${formatFecha(data[0].creado_en)}` : "Evaluación pendiente"}
          </span>
        )}
      </div>

      {loading && <Spinner label="Cargando tu panel…" />}
      {error && <ErrorBanner message={mensajeError(error, "No pudimos cargar tu información.")} onRetry={reload} />}
      {data && !completado && <Pendiente />}
      {completado && <ResultsDashboard evaluaciones={data} usuario={user} onEvaluacionActualizada={replaceEvaluacion} />}
    </MypeLayout>
  );
}
