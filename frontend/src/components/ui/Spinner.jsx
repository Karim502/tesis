export default function Spinner({ label = "Cargando…" }) {
  return (
    <div role="status" className="flex items-center justify-center gap-3 py-16 text-slate-600">
      <span
        aria-hidden="true"
        className="h-6 w-6 animate-spin rounded-full border-4 border-slate-300 border-t-accent motion-reduce:animate-none"
      />
      <span>{label}</span>
    </div>
  );
}
