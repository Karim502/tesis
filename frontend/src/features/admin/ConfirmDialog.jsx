import { useState } from "react";
import { mensajeError } from "../../utils/errores";
import Modal, { BTN_PELIGRO, BTN_PRIMARIO, BTN_SECUNDARIO } from "./Modal";

/** Confirmación de acciones sensibles. `onConfirm` es async: si lanza, el error se muestra aquí y el diálogo sigue abierto. */
export default function ConfirmDialog({ titulo, children, confirmar = "Confirmar", peligro = false, onConfirm, onClose }) {
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState(null);

  async function ejecutar() {
    setTrabajando(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (e) {
      setError(mensajeError(e, "No se pudo completar la acción."));
      setTrabajando(false);
    }
  }

  return (
    <Modal titulo={titulo} onClose={onClose} cerrable={!trabajando}>
      <div className="text-sm text-slate-700">{children}</div>
      {error && <p role="alert" className="mt-3 text-sm font-bold text-riesgo-alto">{error}</p>}
      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button type="button" className={BTN_SECUNDARIO} onClick={onClose} disabled={trabajando}>Cancelar</button>
        <button type="button" data-autofocus className={peligro ? BTN_PELIGRO : BTN_PRIMARIO} onClick={ejecutar} disabled={trabajando}>
          {trabajando ? "Procesando…" : confirmar}
        </button>
      </div>
    </Modal>
  );
}
