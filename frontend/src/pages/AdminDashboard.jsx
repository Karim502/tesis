import { useRef } from "react";
import { useSearchParams } from "react-router-dom";
import AuditoresPanel from "../features/admin/AuditoresPanel";
import HealthPanel from "../features/admin/HealthPanel";
import LogsPanel from "../features/admin/LogsPanel";
import ModeloPanel from "../features/admin/ModeloPanel";
import { useAuth } from "../context/AuthContext";
import { ROLE_LABEL } from "../utils/roles";

const TABS = [
  { id: "auditores", label: "Auditores", Panel: AuditoresPanel },
  { id: "modelo", label: "Modelo (MLOps)", Panel: ModeloPanel },
  { id: "logs", label: "Bitácora", Panel: LogsPanel },
  { id: "salud", label: "Estado del sistema", Panel: HealthPanel },
];

/**
 * Panel del Administrador. La pestaña activa vive en la URL (?tab=modelo): sobrevive a recargas y se puede compartir.
 * Esta pantalla solo existe para ADMIN (ProtectedRoute), pero la seguridad real está en cada endpoint /api/admin/*.
 */
export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const [params, setParams] = useSearchParams();
  const activa = TABS.find((t) => t.id === params.get("tab")) ?? TABS[0];
  const refs = useRef({});

  const ir = (id) => setParams({ tab: id }, { replace: true });
  // Navegación por teclado del patrón WAI-ARIA tabs: ← → Inicio Fin.
  const onKeyDown = (e) => {
    const i = TABS.findIndex((t) => t.id === activa.id);
    const salto = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: TABS.length - 1 }[e.key];
    if (salto === undefined) return;
    e.preventDefault();
    const destino = TABS[(salto + TABS.length) % TABS.length];
    ir(destino.id);
    refs.current[destino.id]?.focus();
  };

  return (
    <div className="min-h-screen bg-slate-100 font-sans text-ink">
      <header className="bg-panel text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-2">
          <p className="min-w-0 truncate text-sm"><strong>{user.nombre}</strong> · {ROLE_LABEL[user.rol]}</p>
          <button type="button" onClick={logout} className="min-h-[44px] shrink-0 px-2 text-sm underline">Cerrar sesión</button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-5">
        <h1 className="mb-4 text-2xl font-bold">Panel de administración</h1>

        <div role="tablist" aria-label="Secciones de administración" onKeyDown={onKeyDown}
          className="mb-5 flex gap-1 overflow-x-auto border-b-2 border-slate-300">
          {TABS.map((t) => {
            const sel = t.id === activa.id;
            return (
              <button key={t.id} ref={(el) => (refs.current[t.id] = el)} role="tab" id={`tab-${t.id}`} type="button"
                aria-selected={sel} aria-controls={`panel-${t.id}`} tabIndex={sel ? 0 : -1} onClick={() => ir(t.id)}
                className={`-mb-0.5 min-h-[44px] shrink-0 whitespace-nowrap border-b-4 px-4 font-bold ${sel ? "border-accent text-accent" : "border-transparent text-slate-600 hover:text-ink"}`}>
                {t.label}
              </button>
            );
          })}
        </div>

        <div role="tabpanel" id={`panel-${activa.id}`} aria-labelledby={`tab-${activa.id}`} tabIndex={0}>
          <activa.Panel />
        </div>
      </main>
    </div>
  );
}
