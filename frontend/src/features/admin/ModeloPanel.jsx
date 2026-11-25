import { useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ErrorBanner from "../../components/ui/ErrorBanner";
import Spinner from "../../components/ui/Spinner";
import { useModelos } from "../../hooks/useModelos";
import { ESTADO_MODELO, ETAPAS, fechaHora, porcentaje } from "../../utils/admin";
import { mensajeError } from "../../utils/errores";
import ConfirmDialog from "./ConfirmDialog";
import { BTN_PRIMARIO, BTN_SECUNDARIO } from "./Modal";

const Badge = ({ estado }) => {
  const e = ESTADO_MODELO[estado] ?? { label: estado, clase: "bg-slate-200 text-slate-800" };
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${e.clase}`}>{e.label}</span>;
};

function Metrica({ nombre, valor }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-600">{nombre}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums">{porcentaje(valor)}</p>
    </div>
  );
}

/** Eje B: métricas del modelo activo, "Forzar reentrenamiento" con estado en vivo e historial de versiones. */
export default function ModeloPanel() {
  const m = useModelos();
  const [archivo, setArchivo] = useState(null);
  const [auto, setAuto] = useState(false);
  const [aActivar, setAActivar] = useState(null);
  const inputRef = useRef(null);

  if (m.cargando) return <Spinner label="Cargando modelos…" />;
  if (m.error && !m.data) return <ErrorBanner message={mensajeError(m.error, "No pudimos cargar el estado del modelo.")} onRetry={m.recargar} />;

  const { activo, versiones } = m.data;
  const ultimo = versiones[0]; // la más reciente (el backend ordena por versión desc.)
  const enCurso = versiones.find((v) => v.estado === "ENTRENANDO");
  const idxEtapa = enCurso ? Math.max(0, ETAPAS.indexOf(enCurso.etapa)) : 0;

  const pct = (val) => (val != null ? +(val * 100).toFixed(1) : null);

  const grafico = versiones.filter((v) => v.f1_score != null).slice(0, 8).reverse()
    .map((v) => ({
      nombre: `v${v.version}`,
      F1: pct(v.f1_score),
      Accuracy: pct(v.accuracy),
      Precision: pct(v.precision),
      Recall: pct(v.recall),
      "ROC-AUC": pct(v.roc_auc),
    }));

  async function lanzar() {
    const ok = await m.reentrenar({ archivo, activarSiMejora: auto });
    if (ok) { setArchivo(null); if (inputRef.current) inputRef.current.value = ""; }
  }

  return (
    <div className="space-y-6">
      {/* 1 · Modelo actual */}
      <section aria-labelledby="t-actual">
        <h2 id="t-actual" className="mb-2 text-lg font-bold">
          Modelo en producción {activo && <span className="ml-1 text-base font-normal text-slate-600">· v{activo.version} · activo desde {fechaHora(activo.activado_en)}</span>}
        </h2>
        {activo ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <Metrica nombre="F1-Score" valor={activo.f1_score} />
            <Metrica nombre="Accuracy" valor={activo.accuracy} />
            <Metrica nombre="Precisión" valor={activo.precision} />
            <Metrica nombre="Recall" valor={activo.recall} />
            <Metrica nombre="ROC-AUC" valor={activo.roc_auc} />
          </div>
        ) : (
          <p className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            Aún no hay una versión activa registrada: la API usa el archivo base configurado. Registra tu modelo actual con
            <code className="mx-1 rounded bg-white px-1">python -m scripts.registrar_modelo_inicial</code> o entrena una versión y actívala abajo.
          </p>
        )}
        {activo && <p className="mt-2 text-xs text-slate-600">Métricas sobre el conjunto de prueba ({activo.n_filas_test ?? "—"} filas) que el modelo no vio al entrenar.</p>}
      </section>

      {/* 2 · Forzar reentrenamiento */}
      <section aria-labelledby="t-retrain" className="rounded-xl bg-white p-4 shadow-sm">
        <h2 id="t-retrain" className="mb-1 text-lg font-bold">Reentrenamiento</h2>
        <p className="mb-3 text-sm text-slate-600">
          Entrena una nueva versión de LightGBM en segundo plano; la API sigue respondiendo y el modelo en producción no cambia hasta que lo actives.
        </p>

        <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
          <div>
            <label htmlFor="lote" className="mb-1 block text-sm font-bold">Nuevo lote de datos (CSV, opcional)</label>
            <input id="lote" ref={inputRef} type="file" accept=".csv,text/csv" disabled={m.entrenando || m.lanzando}
              onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
              className="block min-h-[44px] w-full rounded-lg border-2 border-slate-300 bg-white p-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:font-bold" />
            <p className="mt-1 text-xs text-slate-600">
              {archivo ? `Se usará «${archivo.name}».` : "Sin archivo se usa el dataset por defecto del servidor."} Debe incluir la columna objetivo <code>riesgo</code> (0/1).
            </p>
          </div>
          <button type="button" onClick={lanzar} disabled={m.entrenando || m.lanzando} className={`${BTN_PRIMARIO} md:min-w-[220px]`}>
            {m.lanzando ? "Enviando…" : m.entrenando ? "Entrenando…" : "Forzar reentrenamiento"}
          </button>
        </div>

        <label className="mt-3 flex min-h-[44px] items-center gap-2 text-sm">
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} disabled={m.entrenando || m.lanzando} className="h-5 w-5 accent-[#1F5F5B]" />
          Activar automáticamente si su F1 supera al del modelo activo
        </label>

        {m.errorAccion && <div className="mt-3"><ErrorBanner message={mensajeError(m.errorAccion, "No se pudo completar la acción.")} /></div>}
        {m.avisos.length > 0 && (
          <ul role="status" className="mt-3 list-disc rounded-lg border border-amber-300 bg-amber-50 p-3 pl-7 text-sm text-amber-900">
            {m.avisos.map((a) => <li key={a}>{a}</li>)}
          </ul>
        )}

        {/* Estado en vivo del último entrenamiento */}
        {enCurso && (
          <div role="status" aria-live="polite" className="mt-4 rounded-lg border border-sky-200 bg-sky-50 p-4">
            <p className="font-bold text-sky-900">Entrenando versión {enCurso.version}… <span className="font-normal">({enCurso.etapa ?? "en cola"})</span></p>
            <div role="progressbar" aria-valuemin={0} aria-valuemax={ETAPAS.length} aria-valuenow={idxEtapa + 1} aria-label="Avance del entrenamiento"
              className="mt-2 h-2 overflow-hidden rounded-full bg-sky-200">
              <div className="h-full bg-sky-600 transition-[width] motion-reduce:transition-none" style={{ width: `${((idxEtapa + 1) / ETAPAS.length) * 100}%` }} />
            </div>
            <p className="mt-2 text-xs text-sky-900">Origen: {enCurso.origen_datos}. Puedes cerrar esta pantalla: el trabajo continúa en el servidor.</p>
          </div>
        )}
        {!enCurso && ultimo?.estado === "FALLIDO" && (
          <p role="alert" className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900">
            <b>El entrenamiento de la versión {ultimo.version} falló.</b> {ultimo.error}
          </p>
        )}
        {!enCurso && ultimo?.estado === "CANDIDATO" && (
          <p role="status" className="mt-4 rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900">
            <b>Versión {ultimo.version} lista</b> (candidata): F1 {porcentaje(ultimo.f1_score)} · Accuracy {porcentaje(ultimo.accuracy)}.
            {activo && ` El modelo activo tiene F1 ${porcentaje(activo.f1_score)}.`} {ultimo.error && <span className="text-amber-900"> {ultimo.error}</span>}
          </p>
        )}
      </section>

      {/* 3 · Historial */}
      <section aria-labelledby="t-hist">
        <h2 id="t-hist" className="mb-2 text-lg font-bold">Historial de versiones</h2>
        {grafico.length > 1 && (
          <div className="mb-3 h-52 rounded-xl bg-white p-3 shadow-sm" role="img"
            aria-label={`F1 y accuracy por versión: ${grafico.map((g) => `${g.nombre} F1 ${g.F1}%`).join(", ")}`}>
            <ResponsiveContainer>
              <BarChart data={grafico} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="nombre" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
                <Tooltip formatter={(v) => `${v}%`} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="F1" fill="#1F5F5B" isAnimationActive={false} />
                <Bar dataKey="Accuracy" fill="#94A3B8" isAnimationActive={false} />
                <Bar dataKey="Precision" fill="#0284C7" isAnimationActive={false} />
                <Bar dataKey="Recall" fill="#D97706" isAnimationActive={false} />
                <Bar dataKey="ROC-AUC" fill="#7C3AED" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        {versiones.length === 0 ? (
          <p className="rounded-xl bg-white p-6 text-center shadow-sm">Todavía no hay versiones. Lanza el primer reentrenamiento.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
            <table className="w-full min-w-[760px] text-left text-sm">
              <caption className="sr-only">Versiones del modelo</caption>
              <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-600">
                <tr><th scope="col" className="p-3">Versión</th><th scope="col" className="p-3">Estado</th><th scope="col" className="p-3">F1</th><th scope="col" className="p-3">Accuracy</th>
                  <th scope="col" className="p-3">Filas (train/test)</th><th scope="col" className="p-3">Origen</th><th scope="col" className="p-3">Creada</th><th scope="col" className="p-3 text-right">Acción</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {versiones.map((v) => (
                  <tr key={v.id}>
                    <td className="p-3 font-bold">v{v.version}<span className="block text-xs font-normal text-slate-500">{v.archivo}</span></td>
                    <td className="p-3"><Badge estado={v.estado} />{v.estado === "FALLIDO" && v.error && <p className="mt-1 max-w-[220px] text-xs text-red-800">{v.error}</p>}</td>
                    <td className="p-3 tabular-nums">{porcentaje(v.f1_score)}</td>
                    <td className="p-3 tabular-nums">{porcentaje(v.accuracy)}</td>
                    <td className="p-3 tabular-nums">{v.n_filas_train != null ? `${v.n_filas_train} / ${v.n_filas_test}` : "—"}</td>
                    <td className="max-w-[200px] p-3 text-slate-700">{v.origen_datos ?? "—"}</td>
                    <td className="p-3 text-slate-700">{fechaHora(v.creado_en)}</td>
                    <td className="p-3 text-right">
                      {(v.estado === "CANDIDATO" || v.estado === "ARCHIVADO") && (
                        <button type="button" className={BTN_SECUNDARIO} disabled={m.entrenando} onClick={() => setAActivar(v)}
                          aria-label={`${v.estado === "ARCHIVADO" ? "Volver a" : "Activar"} la versión ${v.version}`}>
                          {v.estado === "ARCHIVADO" ? "Volver a esta" : "Activar"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {aActivar && (
        <ConfirmDialog titulo={`Activar la versión ${aActivar.version}`} confirmar="Activar en producción" onConfirm={() => m.activar(aActivar.id)} onClose={() => setAActivar(null)}>
          <p>La API y la explicabilidad SHAP pasarán a usar <b>v{aActivar.version}</b> (F1 {porcentaje(aActivar.f1_score)}).
            {activo && <> La versión actual (v{activo.version}, F1 {porcentaje(activo.f1_score)}) quedará archivada y podrás volver a ella.</>}</p>
        </ConfirmDialog>
      )}
    </div>
  );
}
