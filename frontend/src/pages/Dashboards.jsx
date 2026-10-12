import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { ROLE_LABEL } from "../utils/roles";
import "./Dashboards.css";

/**
 * Estructura común de los tres paneles. Cada uno pide su endpoint protegido: si el
 * backend responde 403 (acceso cruzado manipulado desde el cliente), se muestra el rechazo.
 */
function DashboardShell({ title, endpoint }) {
  const { user, logout } = useAuth();
  const [message, setMessage] = useState("Cargando…");

  useEffect(() => {
    apiFetch(endpoint)
      .then((d) => setMessage(d.mensaje))
      .catch((e) => setMessage(e.status === 403 ? "Acceso denegado por el servidor." : "No se pudo cargar el panel."));
  }, [endpoint]);

  return (
    <div className="shell">
      <header className="shell__bar">
        <p>
          <strong>{user.nombre}</strong> · {ROLE_LABEL[user.rol]}
        </p>
        <button className="link-btn" onClick={logout}>Cerrar sesión</button>
      </header>
      <main className="shell__main">
        <h1>{title}</h1>
        <p>{message}</p>
      </main>
    </div>
  );
}

export const DashboardAuditor = () => <DashboardShell title="Panel del auditor" endpoint="/auditor/panel" />;
export const AdminPanel = () => <DashboardShell title="Panel de administración" endpoint="/admin/panel" />;
