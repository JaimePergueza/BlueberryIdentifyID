import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <div className="page page-narrow">
      <div className="state-panel not-found">
        <span className="eyebrow">Error 404</span>
        <h1>Página no encontrada</h1>
        <p>La dirección no pertenece al recorrido operativo de BlueberryMicroID.</p>
        <Link className="button button-primary" to="/">Volver al resumen</Link>
      </div>
    </div>
  );
}
