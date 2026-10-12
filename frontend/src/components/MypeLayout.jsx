import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ROLE_LABEL } from "../utils/roles";

/** Marco común de las pantallas del Dueño de MYPE (mobile-first). */
export default function MypeLayout({ children, volverA }) {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen bg-slate-100 font-sans text-ink">
      <header className="bg-panel text-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-2">
          <p className="min-w-0 truncate text-sm">
            <strong>{user.nombre}</strong> · {ROLE_LABEL[user.rol]}
          </p>
          <button type="button" onClick={logout} className="min-h-[44px] shrink-0 px-2 text-sm underline">
            Cerrar sesión
          </button>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-4 py-5">
        {volverA && (
          <Link to={volverA} className="mb-3 inline-flex min-h-[44px] items-center text-sm font-bold text-accent underline">
            Volver a mi panel
          </Link>
        )}
        {children}
      </div>
    </div>
  );
}
