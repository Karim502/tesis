import MypeLayout from "../components/MypeLayout";
import SurveyForm from "../features/evaluacion/SurveyForm";

export default function EvaluacionPage() {
  return (
    <MypeLayout volverA="/dashboard-mype">
      <h1 className="sr-only">Evaluación de riesgo fiscal</h1>
      <SurveyForm />
    </MypeLayout>
  );
}
