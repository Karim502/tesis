export default function ErrorBanner({ message, onRetry }) {
  return (
    <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-900">
      <p>{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 min-h-[44px] rounded-md border-2 border-red-800 px-4 font-bold hover:bg-red-100 focus-visible:outline focus-visible:outline-4 focus-visible:outline-red-300"
        >
          Reintentar
        </button>
      )}
    </div>
  );
}
