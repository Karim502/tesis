import { useId, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ROLE_HOME } from "../utils/roles";
import "./LoginPage.css";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Mensajes de interfaz según el código de error del backend.
const SERVER_MESSAGES = {
  INVALID_CREDENTIALS: "Credenciales inválidas. Revisa tu correo y contraseña.",
  INACTIVE_USER: "Usuario inactivo. Pide al administrador que reactive tu cuenta.",
  NETWORK_ERROR: "No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.",
};

function validate({ email, password }) {
  const errors = {};
  if (!email.trim()) errors.email = "Ingresa tu correo.";
  else if (!EMAIL_RE.test(email.trim())) errors.email = "Escribe un correo válido, por ejemplo nombre@empresa.pe.";
  if (!password) errors.password = "Ingresa tu contraseña.";
  return errors;
}

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const id = useId();

  const [form, setForm] = useState({ email: "", password: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    setFieldErrors((fe) => ({ ...fe, [name]: undefined }));
    setServerError("");
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const errors = validate(form);
    setFieldErrors(errors);
    if (Object.keys(errors).length) return; // no se llama al servidor con campos vacíos

    setSubmitting(true);
    setServerError("");
    try {
      const user = await login(form.email.trim(), form.password);
      navigate(ROLE_HOME[user.rol], { replace: true }); // redirección por rol
    } catch (err) {
      setServerError(
        SERVER_MESSAGES[err.code] ??
          (err.status === 429
            ? "Demasiados intentos. Espera un minuto antes de volver a probar."
            : "No pudimos iniciar sesión. Inténtalo de nuevo.")
      );
      setForm((f) => ({ ...f, password: "" })); // no se conserva la contraseña tras un fallo
    } finally {
      setSubmitting(false);
    }
  };

  const emailId = `${id}-email`;
  const passId = `${id}-password`;

  return (
    <main className="login">
      <aside className="login__aside">
        <h1>Riesgo fiscal de las MYPE, con evidencia</h1>
        <p>Cada perfil entra directo a la herramienta que necesita.</p>
        <dl className="login__roles">
          <div>
            <dt>Dueño de MYPE</dt>
            <dd>Registra los datos de tu negocio y responde el cuestionario.</dd>
          </div>
          <div>
            <dt>Auditor</dt>
            <dd>Revisa evaluaciones de riesgo, modelos predictivos y explicaciones SHAP.</dd>
          </div>
          <div>
            <dt>Administrador</dt>
            <dd>Gestiona usuarios, roles, encuestas y configuración.</dd>
          </div>
        </dl>
      </aside>

      <section className="login__panel">
        <form className="login__form" onSubmit={onSubmit} noValidate>
          <h2>Iniciar sesión</h2>

          {serverError && (
            <div className="alert" role="alert">
              {serverError}
            </div>
          )}

          <div className="field">
            <label htmlFor={emailId}>Correo electrónico</label>
            <input
              id={emailId}
              name="email"
              type="email"
              autoComplete="username"
              value={form.email}
              onChange={onChange}
              aria-invalid={!!fieldErrors.email}
              aria-describedby={fieldErrors.email ? `${emailId}-err` : undefined}
              disabled={submitting}
            />
            {fieldErrors.email && (
              <p className="field__error" id={`${emailId}-err`}>
                {fieldErrors.email}
              </p>
            )}
          </div>

          <div className="field">
            <label htmlFor={passId}>Contraseña</label>
            <div className="field__password">
              <input
                id={passId}
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={form.password}
                onChange={onChange}
                aria-invalid={!!fieldErrors.password}
                aria-describedby={fieldErrors.password ? `${passId}-err` : undefined}
                disabled={submitting}
              />
              <button type="button" className="link-btn" onClick={() => setShowPassword((s) => !s)}>
                {showPassword ? "Ocultar" : "Mostrar"}
              </button>
            </div>
            {fieldErrors.password && (
              <p className="field__error" id={`${passId}-err`}>
                {fieldErrors.password}
              </p>
            )}
          </div>

          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? "Verificando…" : "Ingresar"}
          </button>

          <div className="login__guest">
            <p className="login__divider">¿Solo quieres conocer tu nivel de riesgo?</p>
            <Link to="/invitado/evaluacion" className="btn btn--secondary">
              Realizar diagnóstico rápido (Invitado)
            </Link>
            <p className="login__hint">Sin crear cuenta. Tus respuestas se guardan de forma anónima.</p>
          </div>
        </form>
      </section>
    </main>
  );
}
