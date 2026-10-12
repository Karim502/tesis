import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ROLE_HOME } from "../utils/roles";

function Splash() {
  return <p className="splash" role="status">Verificando sesión…</p>;
}

/**
 * Guard de rutas privadas.
 * - Sin sesión          -> /login
 * - Rol no permitido    -> se devuelve a SU propio panel (acceso cruzado bloqueado)
 *
 * IMPORTANTE: este guard es solo experiencia de usuario. La seguridad real está en el
 * backend (require_roles), porque el código del navegador siempre puede ser manipulado.
 */
export function ProtectedRoute({ allowedRoles }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Splash />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!allowedRoles.includes(user.rol)) return <Navigate to={ROLE_HOME[user.rol]} replace />;
  return <Outlet />;
}

/** /login solo para visitantes: si ya hay sesión, va directo a su panel. */
export function PublicOnlyRoute() {
  const { user, loading } = useAuth();
  if (loading) return <Splash />;
  if (user) return <Navigate to={ROLE_HOME[user.rol]} replace />;
  return <Outlet />;
}

/** "/" decide el destino según sesión y rol. */
export function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <Splash />;
  return <Navigate to={user ? ROLE_HOME[user.rol] : "/login"} replace />;
}
