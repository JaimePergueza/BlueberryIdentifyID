import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { LabelBadge, ReviewBadge } from "../components/StatusBadge";
import { apiRequest } from "../lib/api";
import { formatDate } from "../lib/format";
import type { AnalysisHistoryPage } from "../types/api";

export function DashboardPage() {
  const query = useQuery({
    queryKey: ["analysis-history", "dashboard"],
    queryFn: () => apiRequest<AnalysisHistoryPage>("/api/v1/analysis-runs?page=1&page_size=100"),
  });

  if (query.isLoading) return <LoadingState message="Preparando el resumen operativo…" />;
  if (query.isError) return <ErrorState error={query.error} />;

  const data = query.data!;
  const pending = data.items.filter((item) => item.review_status === "pending").length;
  const reviewed = data.items.filter((item) => item.review_status === "reviewed").length;
  const inconclusive = data.items.filter(
    (item) => item.final_label === "inconclusive" || item.preliminary_label === "inconclusive",
  ).length;

  return (
    <div className="page">
      <div className="page-header dashboard-header">
        <div>
          <span className="eyebrow">Panel operativo</span>
          <h1>Resumen de análisis</h1>
          <p>Estado actual de las muestras registradas y pendientes de validación humana.</p>
        </div>
        <Link className="button button-primary" to="/analyses/new">
          Nuevo análisis
        </Link>
      </div>

      <section className="metric-grid" aria-label="Indicadores del sistema">
        <article className="metric-card">
          <span>Total registrado</span>
          <strong>{data.total}</strong>
          <small>análisis disponibles</small>
        </article>
        <article className="metric-card metric-warning">
          <span>Pendientes</span>
          <strong>{pending}</strong>
          <small>requieren revisión</small>
        </article>
        <article className="metric-card metric-success">
          <span>Revisados</span>
          <strong>{reviewed}</strong>
          <small>con decisión experta</small>
        </article>
        <article className="metric-card">
          <span>No concluyentes</span>
          <strong>{inconclusive}</strong>
          <small>automáticos o finales</small>
        </article>
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Actividad reciente</span>
            <h2>Últimos análisis</h2>
          </div>
          <Link className="text-link" to="/analyses">Ver historial completo</Link>
        </div>

        {data.items.length === 0 ? (
          <EmptyState
            title="Todavía no hay análisis"
            message="Registra la primera muestra para comenzar el recorrido de evaluación."
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Muestra</th>
                  <th>Resultado preliminar</th>
                  <th>Revisión</th>
                  <th>Fecha</th>
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {data.items.slice(0, 6).map((item) => (
                  <tr key={item.analysis_run_id}>
                    <td><strong>{item.sample_code}</strong></td>
                    <td><LabelBadge label={item.preliminary_label} /></td>
                    <td><ReviewBadge reviewed={item.review_status === "reviewed"} /></td>
                    <td>{formatDate(item.created_at)}</td>
                    <td><Link className="text-link" to={`/analyses/${item.analysis_run_id}`}>Abrir</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
