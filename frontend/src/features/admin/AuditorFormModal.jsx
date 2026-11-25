import { useId, useState } from "react";
import { adminApi } from "../../api/adminApi";
import { mensajeError } from "../../utils/errores";
import Modal, { BTN_PRIMARIO, BTN_SECUNDARIO, CAMPO } from "./Modal";

/** Alta de auditor (auditor = null) o edición (nombre y/o restablecer contraseña). El correo no se cambia. */
export default function AuditorFormModal({ auditor, onClose, onSaved }) {
  const edicion = !!auditor;
  const uid = useId();
  const [f, setF] = useState({ nombre: auditor?.nombre ?? "", email: auditor?.email ?? "", password: "" });
  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));

  function validar() {
    const e = {};
    if (!f.nombre.trim()) e.nombre = "Ingresa el nombre.";
    if (!edicion && !/^\S+@\S+\.\S+$/.test(f.email.trim())) e.email = "Ingresa un correo válido.";
    if ((!edicion || f.password) && (f.password.length < 10 || !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password)))
      e.password = "Mínimo 10 caracteres, con letras y números.";
    return e;
  }

  async function enviar(ev) {
    ev.preventDefault();
    const e = validar();
    setErrores(e);
    if (Object.keys(e).length) return;
    setGuardando(true);
    setErrorGeneral(null);
    try {
      if (edicion) {
        const cambios = {};
        if (f.nombre.trim() !== auditor.nombre) cambios.nombre = f.nombre.trim();
        if (f.password) cambios.password = f.password;
        if (Object.keys(cambios).length) await adminApi.actualizarAuditor(auditor.id, cambios); // PATCH: solo lo que cambió
      } else {
        await adminApi.crearAuditor({ nombre: f.nombre.trim(), email: f.email.trim(), password: f.password });
      }
      onSaved();
    } catch (err) {
      if (err.code === "EMAIL_TAKEN") setErrores({ email: "Ya existe una cuenta con ese correo." });
      else setErrorGeneral(mensajeError(err, "No se pudo guardar el auditor."));
      setGuardando(false);
    }
  }

  const campo = (k, label, props = {}, ayuda) => (
    <div>
      <label htmlFor={`${uid}-${k}`} className="mb-1 block text-sm font-bold">{label}</label>
      <input id={`${uid}-${k}`} value={f[k]} onChange={set(k)} className={CAMPO} aria-invalid={!!errores[k]}
        aria-describedby={errores[k] ? `${uid}-${k}-e` : ayuda ? `${uid}-${k}-a` : undefined} {...props} />
      {ayuda && !errores[k] && <p id={`${uid}-${k}-a`} className="mt-1 text-xs text-slate-600">{ayuda}</p>}
      {errores[k] && <p id={`${uid}-${k}-e`} role="alert" className="mt-1 text-sm font-bold text-riesgo-alto">{errores[k]}</p>}
    </div>
  );

  return (
    <Modal titulo={edicion ? "Editar auditor" : "Nuevo auditor"} onClose={onClose} cerrable={!guardando}>
      <form onSubmit={enviar} noValidate className="space-y-3">
        {campo("nombre", "Nombre completo", { autoComplete: "off", maxLength: 120, "data-autofocus": true })}
        {campo("email", "Correo", { type: "email", disabled: edicion, autoComplete: "off", maxLength: 255 })}
        {campo("password", edicion ? "Nueva contraseña (opcional)" : "Contraseña inicial",
          { type: "password", autoComplete: "new-password", maxLength: 72 },
          edicion ? "Déjala vacía para no cambiarla." : "Entrégasela al auditor por un canal seguro.")}
        {errorGeneral && <p role="alert" className="text-sm font-bold text-riesgo-alto">{errorGeneral}</p>}
        <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
          <button type="button" className={BTN_SECUNDARIO} onClick={onClose} disabled={guardando}>Cancelar</button>
          <button type="submit" className={BTN_PRIMARIO} disabled={guardando}>{guardando ? "Guardando…" : edicion ? "Guardar cambios" : "Crear auditor"}</button>
        </div>
      </form>
    </Modal>
  );
}
