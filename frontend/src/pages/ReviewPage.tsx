import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";
import { ErrorState, LoadingState } from "../components/Feedback";
import { LabelBadge } from "../components/StatusBadge";
import { ApiError, apiRequest } from "../lib/api";
import { labelName } from "../lib/format";
import { useAuth } from "../lib/auth";
import type { HumanReview, PredictedLabel, PreliminaryResult, ReviewDecision } from "../types/api";

const labels: PredictedLabel[] = [
  "no_evident_growth",
  "suspicious_growth",
  "probable_fungal_growth",
  "probable_bacterial_growth",
  "inconclusive",
];

export function ReviewPage() {
  const { analysisRunId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [decision, setDecision] = useState<ReviewDecision>("confirmed");
  const [correctedLabel, setCorrectedLabel] = useState<PredictedLabel>("inconclusive");
  const [comments, setComments] = useState("");
  const [error, setError] = useState<string | null>(null);

  const resultQuery = useQuery({
    queryKey: ["preliminary-result", analysisRunId],
    queryFn: () => apiRequest<PreliminaryResult>(`/api/v1/analysis-runs/${analysisRunId}/preliminary-result`),
    enabled: Boolean(analysisRunId),
  });

  const mutation = useMutation({
    mutationFn: () =>
      apiRequest<HumanReview>(`/api/v1/analysis-runs/${analysisRunId}/reviews`, {
        method: "POST",
        body: JSON.stringify({
          reviewer_name: user?.username ?? "especialista",
          review_decision: decision,
          corrected_label: decision === "corrected" ? correctedLabel : null,
          comments: comments.trim() || null,
          is_final: true,
        }),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["preliminary-result", analysisRunId] }),
        queryClient.invalidateQueries({ queryKey: ["analysis-detail", analysisRunId] }),
        queryClient.invalidateQueries({ queryKey: ["analysis-history"] }),
      ]);
      navigate(`/analyses/${analysisRunId}`);
    },
    onError: (caught) => {
      setError(caught instanceof ApiError ? caught.message : "No se pudo registrar la revisión.");
    },
  });

  if (resultQuery.isLoading) return <LoadingState message="Preparando la revisión…" />;
  if (resultQuery.isError) return <ErrorState error={resultQuery.error} />;

  const result = resultQuery.data!;
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    mutation.mutate();
  };

  return (
    <div className="page page-narrow">
      <div className="page-header">
        <div>
          <span className="eyebrow">Validación experta</span>
          <h1>Revisión humana</h1>
          <p>La decisión se agrega al historial y nunca sobrescribe la predicción automática.</p>
        </div>
      </div>

      <section className="card compact-result">
        <div>
          <span className="eyebrow">Resultado preliminar</span>
          <h2>{labelName(result.predicted_label)}</h2>
          <p>{result.explanation}</p>
        </div>
        <LabelBadge label={result.predicted_label} />
      </section>

      <form className="card review-form" onSubmit={handleSubmit}>
        <div className="section-heading"><h2>Decisión del especialista</h2></div>
        <fieldset className="decision-grid">
          <legend className="sr-only">Selecciona una decisión</legend>
          {([
            ["confirmed", "Confirmar", "El resultado automático coincide con la evaluación."],
            ["corrected", "Corregir", "Asignar otra categoría visual preliminar."],
            ["marked_inconclusive", "No concluyente", "No existe evidencia suficiente."],
            ["rejected_invalid_sample", "Rechazar muestra", "La muestra o las imágenes no son válidas."],
          ] as const).map(([value, title, description]) => (
            <label className={`decision-option ${decision === value ? "selected" : ""}`} key={value}>
              <input
                type="radio"
                name="decision"
                value={value}
                checked={decision === value}
                onChange={() => setDecision(value)}
              />
              <strong>{title}</strong>
              <small>{description}</small>
            </label>
          ))}
        </fieldset>

        {decision === "corrected" && (
          <label className="field">
            <span>Categoría corregida</span>
            <select value={correctedLabel} onChange={(event) => setCorrectedLabel(event.target.value as PredictedLabel)}>
              {labels.map((label) => <option value={label} key={label}>{labelName(label)}</option>)}
            </select>
          </label>
        )}

        <label className="field">
          <span>Comentarios técnicos <small>(opcional)</small></span>
          <textarea
            rows={5}
            value={comments}
            onChange={(event) => setComments(event.target.value)}
            placeholder="Registra la observación que sustenta la decisión."
          />
        </label>

        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="form-actions split-actions">
          <Link className="button button-secondary" to={`/analyses/${analysisRunId}/preliminary`}>Cancelar</Link>
          <button className="button button-primary" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? "Guardando revisión…" : "Guardar decisión final"}
          </button>
        </div>
      </form>
    </div>
  );
}
