import { useEffect, useId, useRef } from "react";

const FOCUSABLES = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Diálogo accesible: role="dialog", foco atrapado, Esc cierra, el scroll de fondo se bloquea y el foco vuelve al origen. */
export default function Modal({ titulo, onClose, children, ancho = "max-w-md", cerrable = true }) {
  const ref = useRef(null);
  const id = useId();

  useEffect(() => {
    const previo = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    (ref.current.querySelector("[data-autofocus]") ?? ref.current.querySelector(FOCUSABLES))?.focus();

    const onKey = (e) => {
      if (e.key === "Escape" && cerrable) return onClose();
      if (e.key !== "Tab") return;
      const items = [...ref.current.querySelectorAll(FOCUSABLES)];
      if (!items.length) return;
      const [primero, ultimo] = [items[0], items[items.length - 1]];
      if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); ultimo.focus(); }
      else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primero.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      previo?.focus?.();
    };
  }, [onClose, cerrable]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && cerrable && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={id}
        className={`max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl ${ancho}`}>
        <h2 id={id} className="mb-3 text-lg font-bold">{titulo}</h2>
        {children}
      </div>
    </div>
  );
}

export const BTN_PRIMARIO = "min-h-[44px] rounded-lg bg-accent px-4 font-bold text-white hover:bg-[#174B48] disabled:cursor-not-allowed disabled:opacity-50";
export const BTN_SECUNDARIO = "min-h-[44px] rounded-lg border-2 border-accent px-4 font-bold text-accent disabled:cursor-not-allowed disabled:opacity-50";
export const BTN_PELIGRO = "min-h-[44px] rounded-lg bg-riesgo-alto px-4 font-bold text-white hover:bg-[#8F1E18] disabled:cursor-not-allowed disabled:opacity-50";
export const CAMPO = "min-h-[44px] w-full rounded-lg border-2 border-slate-300 bg-white px-3 text-base focus-visible:border-accent focus-visible:outline focus-visible:outline-4 focus-visible:outline-accent/30";
