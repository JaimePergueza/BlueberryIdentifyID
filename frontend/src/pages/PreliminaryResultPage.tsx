import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { ErrorState, LoadingState } from "../components/Feedback";
import { LabelBadge, ReviewBadge } from "../components/StatusBadge";
import { apiRequest } from "../lib/api";
import { formatDate, formatPercent, labelName } from "../lib/format";
import type { PreliminaryResult } from "../types/api";

export function PreliminaryResultPage() {
  const { analysisRunId = "" } = useParams();
  const query = useQuery({
    queryKey: ["preliminary-result", analysisRunId],
    queryFn: () => apiRequest<PreliminaryResult>(`/api/v1/analysis-runs/${analysisRunId}/preliminary-result`),
    enabled: Boolean(analysisRunId),
  });

  if (query.isLoading) return <LoadingState message="Recuperando el resultado preliminar…" />;
  if (query.isError) return <ErrorState error={query.error} />;

  const result = query.data!;
  const probabilities = Object.entries(result.class_probabilities ?? {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="page page-narrow">
      <div className="page-header">
        <div>
          <span className="eyebrow">Resultado automático</span>
          <h1>Clasificación preliminar</h1>
          <p>La predicción permanece inmutable aunque posteriormente exista una corrección humana.</p>
        </div>
        <ReviewBadge reviewed={result.human_review_completed} />
      </div>

      <section className="result-hero card">
        <div>
          <span className="eyebrow">Categoría visual preliminar</span>
          <div className="result-label"><LabelBadge label={result.predicted_label} /></div>
          <h2>{labelName(result.predicted_label)}</h2>
          <p>{result.explanation ?? "El motor no proporcionó una explicación adicional."}</p>
        </div>
        <div className="confidence-ring" aria-label={`Confianza ${formatPercent(result.confidence_score)}`}>
          <strong>{formatPercent(result.confidence_score)}</strong>
          <span>confianza técnica</span>
        </div>
      </section>

      <div className="two-column">
        <section className="card">
          <div className="section-heading"><h2>Distribución de categorías</h2></div>
          <div className="probability-list">
            {probabilities.map(([label, probability]) => (
              <div className="probability-row" key={label}>
                <div><span>{labelName(label as PreliminaryResult["predicted_label"])}</span><strong>{formatPercent(probability)}</strong></div>
                <progress max={1} value={probability} />
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="section-heading"><h2>Control de calidad</h2></div>
          {result.quality_summary && Object.keys(result.quality_summary).length > 0 ? (
            <dl className="key-value-list">
              {Object.entries(result.quality_summary).map(([key, value]) => (
                <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{String(value)}</dd></div>
              ))}
            </dl>
          ) : <p className="muted">No existen indicadores adicionales.</p>}
        </section>
      </div>

      {result.warnings && result.warnings.length > 0 && (
        <div className="alert alert-warning">
          <strong>Advertencias automáticas</strong>
          <ul>{result.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </div>
      )}

      <div className="alert alert-info">
        <strong>Revisión humana obligatoria</strong>
        <p>{result.disclaimer}</p>
        {result.reviewed_at && <small>Última revisión: {formatDate(result.reviewed_at)}</small>}
      </div>

      <div className="form-actions split-actions">
        <Link className="button button-secondary" to={`/analyses/${analysisRunId}`}>Ver trazabilidad</Link>
        {result.human_review_completed ? (
          <Link className="button button-primary" to={`/analyses/${analysisRunId}`}>Ver resultado final</Link>
        ) : (
          <Link className="button button-primary" to={`/analyses/${analysisRunId}/review`}>Registrar revisión experta</Link>
        )}
      </div>
    </div>
  );
}
