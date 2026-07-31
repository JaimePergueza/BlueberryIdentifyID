import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import { AnalysisStatusBadge, LabelBadge, ReviewBadge } from "../components/StatusBadge";
import { apiRequest } from "../lib/api";
import { formatDate, formatPercent, labelName } from "../lib/format";
import type { AnalysisHistoryPage, PredictedLabel } from "../types/api";

const labels: PredictedLabel[] = [
  "no_evident_growth",
  "suspicious_growth",
  "probable_fungal_growth",
  "probable_bacterial_growth",
  "inconclusive",
];

interface Filters {
  sampleCode: string;
  status: string;
  reviewStatus: string;
  preliminaryLabel: string;
  finalLabel: string;
  createdFrom: string;
  createdTo: string;
}

const initialFilters: Filters = {
  sampleCode: "",
  status: "",
  reviewStatus: "",
  preliminaryLabel: "",
  finalLabel: "",
  createdFrom: "",
  createdTo: "",
};

function queryString(page: number, filters: Filters): string {
  const params = new URLSearchParams({ page: String(page), page_size: "20" });
  if (filters.sampleCode.trim()) params.set("sample_code", filters.sampleCode.trim());
  if (filters.status) params.set("status", filters.status);
  if (filters.reviewStatus) params.set("review_status", filters.reviewStatus);
  if (filters.preliminaryLabel) params.set("preliminary_label", filters.preliminaryLabel);
  if (filters.finalLabel) params.set("final_label", filters.finalLabel);
  if (filters.createdFrom) params.set("created_from", `${filters.createdFrom}T00:00:00Z`);
  if (filters.createdTo) params.set("created_to", `${filters.createdTo}T23:59:59Z`);
  return params.toString();
}

export function HistoryPage() {
  const [draft, setDraft] = useState(initialFilters);
  const [filters, setFilters] = useState(initialFilters);
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["analysis-history", page, filters],
    queryFn: () => apiRequest<AnalysisHistoryPage>(`/api/v1/analysis-runs?${queryString(page, filters)}`),
  });

  const applyFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPage(1);
    setFilters(draft);
  };
  const clearFilters = () => {
    setDraft(initialFilters);
    setFilters(initialFilters);
    setPage(1);
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Trazabilidad</span>
          <h1>Historial de análisis</h1>
          <p>Busca muestras y compara el resultado automático con la decisión experta.</p>
        </div>
        <Link className="button button-primary" to="/analyses/new">Nuevo análisis</Link>
      </div>

      <form className="card filter-panel" onSubmit={applyFilters}>
        <div className="filter-grid">
          <label className="field">
            <span>Código de muestra</span>
            <input value={draft.sampleCode} onChange={(event) => setDraft({ ...draft, sampleCode: event.target.value })} placeholder="Buscar parcialmente" />
          </label>
          <label className="field">
            <span>Estado</span>
            <select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}>
              <option value="">Todos</option>
              <option value="pending">Pendiente</option>
              <option value="processing">Procesando</option>
              <option value="completed">Completado</option>
              <option value="needs_review">Requiere revisión</option>
              <option value="failed">Fallido</option>
            </select>
          </label>
          <label className="field">
            <span>Revisión</span>
            <select value={draft.reviewStatus} onChange={(event) => setDraft({ ...draft, reviewStatus: event.target.value })}>
              <option value="">Todas</option>
              <option value="pending">Pendiente</option>
              <option value="reviewed">Revisada</option>
            </select>
          </label>
          <label className="field">
            <span>Resultado preliminar</span>
            <select value={draft.preliminaryLabel} onChange={(event) => setDraft({ ...draft, preliminaryLabel: event.target.value })}>
              <option value="">Todos</option>
              {labels.map((label) => <option value={label} key={label}>{labelName(label)}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Resultado final</span>
            <select value={draft.finalLabel} onChange={(event) => setDraft({ ...draft, finalLabel: event.target.value })}>
              <option value="">Todos</option>
              {labels.map((label) => <option value={label} key={label}>{labelName(label)}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Desde</span>
            <input type="date" value={draft.createdFrom} onChange={(event) => setDraft({ ...draft, createdFrom: event.target.value })} />
          </label>
          <label className="field">
            <span>Hasta</span>
            <input type="date" value={draft.createdTo} onChange={(event) => setDraft({ ...draft, createdTo: event.target.value })} />
          </label>
        </div>
        <div className="filter-actions">
          <button className="button button-ghost" type="button" onClick={clearFilters}>Limpiar</button>
          <button className="button button-secondary" type="submit">Aplicar filtros</button>
        </div>
      </form>

      {query.isLoading && <LoadingState message="Consultando el historial…" />}
      {query.isError && <ErrorState error={query.error} />}
      {query.data && query.data.items.length === 0 && (
        <EmptyState title="No se encontraron análisis" message="Prueba con otros filtros o registra una nueva muestra." />
      )}
      {query.data && query.data.items.length > 0 && (
        <section className="card history-card">
          <div className="section-heading">
            <div><h2>{query.data.total} resultados</h2><p>Página {query.data.page} de {query.data.total_pages}</p></div>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Muestra</th><th>Estado</th><th>Preliminar</th><th>Confianza</th><th>Final</th><th>Revisión</th><th>Fecha</th><th /></tr></thead>
              <tbody>
                {query.data.items.map((item) => (
                  <tr key={item.analysis_run_id}>
                    <td><strong>{item.sample_code}</strong><small className="table-subtext">{item.model_name} {item.model_version}</small></td>
                    <td><AnalysisStatusBadge status={item.analysis_status} /></td>
                    <td><LabelBadge label={item.preliminary_label} /></td>
                    <td>{formatPercent(item.confidence_score)}</td>
                    <td><LabelBadge label={item.final_label} /></td>
                    <td><ReviewBadge reviewed={item.review_status === "reviewed"} /></td>
                    <td>{formatDate(item.created_at)}</td>
                    <td><Link className="text-link" to={`/analyses/${item.analysis_run_id}`}>Detalle</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button className="button button-ghost" type="button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Anterior</button>
            <span>Página {page}</span>
            <button className="button button-ghost" type="button" disabled={page >= query.data.total_pages} onClick={() => setPage((value) => value + 1)}>Siguiente</button>
          </div>
        </section>
      )}
    </div>
  );
}
