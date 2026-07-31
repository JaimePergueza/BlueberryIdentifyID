import { ApiError } from "../lib/api";

export function LoadingState({ message = "Cargando información…" }: { message?: string }) {
  return (
    <div className="state-panel" role="status">
      <span className="spinner" aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}

export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="state-panel empty-state">
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}

export function ErrorState({ error, title = "No fue posible cargar la información" }: { error: unknown; title?: string }) {
  const message = error instanceof ApiError ? error.message : "Ocurrió un error inesperado.";
  const requestId = error instanceof ApiError ? error.requestId : undefined;
  return (
    <div className="alert alert-error" role="alert">
      <strong>{title}</strong>
      <p>{message}</p>
      {requestId && <small>Referencia: {requestId}</small>}
    </div>
  );
}
