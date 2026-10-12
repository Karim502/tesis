import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { evaluacionApi } from "../../api/evaluacionApi";
import { useAuth } from "../../context/AuthContext";
import ErrorBanner from "../../components/ui/ErrorBanner";
import Spinner from "../../components/ui/Spinner";
import { mensajeError } from "../../utils/errores";
import { guardarResultadoInvitado } from "../../utils/resultadoInvitado";
import QuestionField from "./QuestionField";
import { normalizarRespuestas, validarRespuesta } from "./validaciones";

/**
 * Cuestionario por pasos: una pregunta por pantalla.
 * El catálogo viene del backend, así que el wizard escala a 15-16 preguntas sin cambiar este código.
 */
export default function SurveyForm({ modo = "usuario" }) {
  const invitado = modo === "invitado";
  const { user } = useAuth(); // en modo invitado user es null
  const navigate = useNavigate();
  const uid = useId();
  const tituloRef = useRef(null);
  const borradorKey = `cu01:borrador:${user?.id ?? "invitado"}`;

  const [preguntas, setPreguntas] = useState(null);
  const [errorCarga, setErrorCarga] = useState(null);
  const [paso, setPaso] = useState(0);
  const [respuestas, setRespuestas] = useState({});
  const [errorPaso, setErrorPaso] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [errorEnvio, setErrorEnvio] = useState(null);

  const cargar = useCallback(async () => {
    setErrorCarga(null);
    setPreguntas(null);
    try {
      const { preguntas: lista } = await evaluacionApi.cuestionario();
      setPreguntas(lista);
      // Restaura el borrador (por si el usuario perdió señal o cerró la pestaña a medias).
      if (invitado) return; // invitado: nunca se reutilizan respuestas de otra persona
      try {
        const borrador = JSON.parse(sessionStorage.getItem(borradorKey) ?? "null");
        if (borrador && borrador.paso < lista.length) {
          setRespuestas(borrador.respuestas ?? {});
          setPaso(borrador.paso);
        }
      } catch {
        /* borrador ilegible: se ignora */
      }
    } catch (e) {
      setErrorCarga(mensajeError(e, "No pudimos cargar el cuestionario."));
    }
  }, [borradorKey, invitado]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  // Guarda el borrador (sessionStorage: se borra al cerrar la pestaña).
  useEffect(() => {
    if (!preguntas || invitado) return;
    try {
      sessionStorage.setItem(borradorKey, JSON.stringify({ paso, respuestas }));
    } catch {
      /* almacenamiento no disponible: el formulario sigue funcionando */
    }
  }, [preguntas, paso, respuestas, borradorKey, invitado]);

  // Al cambiar de pregunta, el foco va al título para lectores de pantalla.
  useEffect(() => {
    tituloRef.current?.focus();
  }, [paso]);

  if (errorCarga) return <ErrorBanner message={errorCarga} onRetry={cargar} />;
  if (!preguntas) return <Spinner label="Preparando tu cuestionario…" />;

  const pregunta = preguntas[paso];
  const esUltima = paso === preguntas.length - 1;
  const avance = Math.round((paso / preguntas.length) * 100);

  const cambiar = (valor) => {
    setRespuestas((r) => ({ ...r, [pregunta.id]: valor }));
    setErrorPaso(null);
    setErrorEnvio(null);
  };

  const enviar = async () => {
    setEnviando(true);
    setErrorEnvio(null);
    try {
      const payload = normalizarRespuestas(preguntas, respuestas);
      if (invitado) {
        const resultado = await evaluacionApi.crearInvitado(payload);
        guardarResultadoInvitado(resultado);
        navigate("/invitado/resultado", { replace: true, state: { resultado } });
        return;
      }
      await evaluacionApi.crear(payload);
      try {
        sessionStorage.removeItem(borradorKey);
      } catch {
        /* nada que limpiar */
      }
      navigate("/dashboard-mype", { replace: true });
    } catch (e) {
      setErrorEnvio(mensajeError(e, "No pudimos guardar tu evaluación."));
    } finally {
      setEnviando(false);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    const err = validarRespuesta(pregunta, respuestas[pregunta.id]);
    if (err) return setErrorPaso(err);
    if (esUltima) enviar();
    else setPaso((p) => p + 1);
  };

  return (
    <form onSubmit={onSubmit} noValidate className="mx-auto flex min-h-[70vh] max-w-xl flex-col">
      <div className="mb-6">
        <p ref={tituloRef} tabIndex={-1} className="text-sm font-bold text-slate-700 outline-none">
          Pregunta {paso + 1} de {preguntas.length}
        </p>
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={avance}
          aria-label="Avance del cuestionario"
          className="mt-2 h-2 overflow-hidden rounded-full bg-slate-300"
        >
          <div className="h-full bg-accent transition-[width] motion-reduce:transition-none" style={{ width: `${avance}%` }} />
        </div>
      </div>

      <div className="flex-1 rounded-xl bg-white p-5 shadow-sm">
        <QuestionField
          key={pregunta.id}
          pregunta={pregunta}
          valor={respuestas[pregunta.id]}
          onChange={cambiar}
          error={errorPaso}
          inputId={`${uid}-${pregunta.id}`}
        />
      </div>

      {errorEnvio && (
        <div className="mt-4">
          <ErrorBanner message={errorEnvio} />
        </div>
      )}

      {/* Barra de acciones fija abajo: alcanzable con el pulgar */}
      <div className="sticky bottom-0 -mx-4 mt-4 flex gap-3 border-t border-slate-300 bg-slate-100 px-4 py-3">
        <button
          type="button"
          onClick={() => {
            setErrorPaso(null);
            setPaso((p) => p - 1);
          }}
          disabled={paso === 0 || enviando}
          className="min-h-[52px] flex-1 rounded-lg border-2 border-accent font-bold text-accent disabled:cursor-not-allowed disabled:opacity-40"
        >
          Atrás
        </button>
        <button
          type="submit"
          disabled={enviando}
          className="flex min-h-[52px] flex-[2] items-center justify-center gap-2 rounded-lg bg-accent font-bold text-white hover:bg-[#174B48] disabled:cursor-progress disabled:opacity-70"
        >
          {enviando && (
            <span aria-hidden="true" className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white motion-reduce:animate-none" />
          )}
          {enviando ? "Calculando tu riesgo…" : esUltima ? "Ver mi resultado" : "Siguiente"}
        </button>
      </div>
    </form>
  );
}
