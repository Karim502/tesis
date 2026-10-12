import GuestLayout from "../components/GuestLayout";
import SurveyForm from "../features/evaluacion/SurveyForm";

export default function EvaluacionInvitadoPage() {
  return (
    <GuestLayout>
      <h1 className="sr-only">Diagnóstico rápido de riesgo fiscal</h1>
      <p className="mx-auto mb-4 max-w-xl rounded-lg bg-white p-3 text-sm text-slate-700 shadow-sm">
        No necesitas cuenta. Tus respuestas se guardan de forma anónima, sin nombre ni correo, para una investigación
        académica sobre el cumplimiento fiscal de las MYPE.
      </p>
      <SurveyForm modo="invitado" />
    </GuestLayout>
  );
}
