import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import GuestLayout from "../components/GuestLayout";
import ResultsDashboard from "../features/evaluacion/ResultsDashboard";
import { borrarResultadoInvitado, guardarResultadoInvitado, leerResultadoInvitado } from "../utils/resultadoInvitado";

export default function ResultadoInvitadoPage() {
  const location = useLocation();
  const navigate = useNavigate();
  // Prioridad: lo guardado en esta pestaña (incluye las tareas ya marcadas). `location.state` queda como
  // respaldo por si sessionStorage no está disponible: el navegador lo conserva al recargar con su valor
  // ORIGINAL, así que darle prioridad haría perder el avance del checklist.
  const [resultado, setResultado] = useState(() => leerResultadoInvitado() ?? location.state?.resultado ?? null);

  if (!resultado) return <Navigate to="/invitado/evaluacion" replace />;

  // El checklist del invitado solo cambia en este dispositivo (no hay cuenta donde guardarlo).
  const actualizar = (ev) => {
    setResultado(ev);
    guardarResultadoInvitado(ev);
  };
  const nueva = () => {
    borrarResultadoInvitado(); // la siguiente persona empieza de cero
    navigate("/invitado/evaluacion", { replace: true });
  };

  return (
    <GuestLayout>
      <h1 className="mb-4 text-2xl font-bold">Tu resultado</h1>
      <ResultsDashboard
        invitado
        evaluaciones={[resultado]}
        usuario={null}
        onEvaluacionActualizada={actualizar}
        onNuevaEvaluacion={nueva}
      />
    </GuestLayout>
  );
}
