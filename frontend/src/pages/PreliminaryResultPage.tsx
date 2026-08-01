import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { ErrorState, LoadingState } from "../components/Feedback";
import { MorphologyEvidence } from "../components/MorphologyEvidence";
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
  const categoryScores = Object.entries(result.class_probabilities ?? {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="page page-narrow">
      <div className="page-header">
        <div>
          <span className="eyebrow">Resultado automático</span>
          <h1>Clasificación morfológica preliminar</h1>
          <p>La predicción y sus mediciones permanecen inmutables aunque exista una corrección humana posterior.</p>
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
        <div className="confidence-ring" aria-label={`Puntuación técnica ${formatPercent(result.confidence_score)}`}>
          <strong>{formatPercent(result.confidence_score)}</strong>
          <span>puntuación heurística limitada</span>
        </div>
      </section>

      <MorphologyEvidence
        featureSummary={result.feature_summary}
        qualitySummary={result.quality_summary}
        decisionTrace={result.decision_trace}
      />

      <div className="two-column">
        <section className="card">
          <div className="section-heading"><h2>Puntuaciones heurísticas por categoría</h2></div>
          <p>No son probabilidades calibradas ni frecuencias biológicas.</p>
          <div className="probability-list">
            {categoryScores.map(([label, score]) => (
              <div className="probability-row" key={label}>
                <div><span>{labelName(label as PreliminaryResult["predicted_label"])}</span><strong>{formatPercent(score)}</strong></div>
                <progress max={1} value={score} />
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="section-heading"><h2>Alcance del resultado</h2></div>
          <ul className="scope-list">
            <li>Compara evidencia macroscópica y microscópica de la misma muestra.</li>
            <li>Describe crecimiento y patrones morfológicos amplios.</li>
            <li>Puede abstenerse como no concluyente ante señales contradictorias.</li>
            <li>Las hipótesis de género son orientativas y deben confirmarse en laboratorio.</li>
          </ul>
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
