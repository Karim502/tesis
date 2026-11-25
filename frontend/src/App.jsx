import { Navigate, Route, Routes } from "react-router-dom";
import { HomeRedirect, ProtectedRoute, PublicOnlyRoute } from "./components/RouteGuards";
import LoginPage from "./pages/LoginPage";
import DashboardMype from "./pages/DashboardMype";
import EvaluacionPage from "./pages/EvaluacionPage";
import EvaluacionInvitadoPage from "./pages/EvaluacionInvitadoPage";
import ResultadoInvitadoPage from "./pages/ResultadoInvitadoPage";
import DashboardAuditor from "./pages/DashboardAuditor";
import AdminDashboard from "./pages/AdminDashboard";
import { ROLES } from "./utils/roles";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />

      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<LoginPage />} />
        {/* Modo Invitado: públicas, sin JWT. Quien ya tiene sesión es enviado a su propio panel. */}
        <Route path="/invitado/evaluacion" element={<EvaluacionInvitadoPage />} />
        <Route path="/invitado/resultado" element={<ResultadoInvitadoPage />} />
      </Route>

      <Route element={<ProtectedRoute allowedRoles={[ROLES.DUENO_MYPE]} />}>
        <Route path="/dashboard-mype" element={<DashboardMype />} />
        <Route path="/dashboard-mype/evaluacion" element={<EvaluacionPage />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.AUDITOR]} />}>
        <Route path="/dashboard-auditor" element={<DashboardAuditor />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={[ROLES.ADMIN]} />}>
        <Route path="/admin-panel" element={<AdminDashboard />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
