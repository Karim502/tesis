import { Link } from "react-router-dom";

/** Marco de las pantallas del invitado: mismo aspecto que MypeLayout, pero sin sesión. */
export default function GuestLayout({ children }) {
  return (
    <div className="min-h-screen bg-slate-100 font-sans text-ink">
      <header className="bg-panel text-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-2">
          <p className="min-w-0 truncate text-sm">
            <strong>Diagnóstico rápido</strong> · Invitado
          </p>
          <Link to="/login" className="flex min-h-[44px] shrink-0 items-center px-2 text-sm underline">
            Iniciar sesión
          </Link>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-4 py-5">{children}</div>
    </div>
  );
}
