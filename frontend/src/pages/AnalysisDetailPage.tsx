import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { ErrorState, LoadingState } from "../components/Feedback";
import { ProtectedImage } from "../components/ProtectedImage";
import { AnalysisStatusBadge, LabelBadge, ReviewBadge } from "../components/StatusBadge";
import { apiRequest } from "../lib/api";
import { decisionName, formatBytes, formatDate, formatPercent, labelName } from "../lib/format";
import type { AnalysisDetail } from "../types/api";

function MetadataCard({
  title,
  entries,
}: {
  title: string;
  entries: Array<[string, string | number | null | undefined]>;
}) {
  return (
    <section className="card">
      <div className="section-heading"><h2>{title}</h2></div>
      <dl className="key-value-list">
        {entries.map(([label, value]) => (
          <div key={label}><dt>{label}</dt><dd>{value ?? "—"}</dd></div>
        ))}
      </dl>
    </section>
  );
}

export function AnalysisDetailPage() {
  const { analysisRunId = "" } = useParams();
  const query = useQuery({
    queryKey: ["analysis-detail", analysisRunId],
    queryFn: () => apiRequest<AnalysisDetail>(`/api/v1/analysis-runs/${analysisRunId}/detail`),
    enabled: Boolean(analysisRunId),
  });

  if (query.isLoading) return <LoadingState message="Recuperando la trazabilidad completa…" />;
  if (query.isError) return <ErrorState error={query.error} />;

  const detail = query.data!;
  const prediction = detail.prediction;
  const review = detail.human_review;

  return (
    <div className="page">
      <div className="page-header detail-header">
        <div>
          <span className="eyebrow">Muestra {detail.sample.sample_code}</span>
          <h1>Detalle y trazabilidad</h1>
          <p>Registro automático y decisión humana presentados sin sobrescribir información.</p>
        </div>
        <div className="header-badges">
          <AnalysisStatusBadge status={detail.analysis_run.status} />
          <ReviewBadge reviewed={detail.human_review_completed} />
        </div>
      </div>

      <section className="comparison-grid">
        <article className="card result-column automatic-result">
          <span className="eyebrow">Resultado automático</span>
          <h2>{labelName(prediction?.predicted_label)}</h2>
          <LabelBadge label={prediction?.predicted_label ?? null} />
          <div className="large-value">{formatPercent(prediction?.confidence_score)}</div>
          <p>{prediction?.explanation ?? "Este análisis todavía no tiene una predicción."}</p>
          {prediction && (
            <Link className="text-link" to={`/analyses/${analysisRunId}/preliminary`}>Abrir explicación preliminar</Link>
          )}
        </article>

        <article className="card result-column human-result">
          <span className="eyebrow">Resultado final humano</span>
          <h2>{labelName(detail.final_label)}</h2>
          <LabelBadge label={detail.final_label} />
          <div className="review-decision">{decisionName(review?.review_decision)}</div>
          <p>{review?.comments ?? "La muestra permanece pendiente de revisión experta."}</p>
          {review ? (
            <small>Revisado por {review.reviewer_name} · {formatDate(review.created_at)}</small>
          ) : (
            <Link className="button button-primary" to={`/analyses/${analysisRunId}/review`}>Registrar revisión</Link>
          )}
        </article>
      </section>

      <section className="card image-comparison-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Evidencia visual</span>
            <h2>Imágenes de la muestra</h2>
          </div>
        </div>
        <div className="stored-image-grid">
          <ProtectedImage
            endpoint={`/api/v1/petri-images/${detail.petri_image.id}/content`}
            alt={`Caja Petri de la muestra ${detail.sample.sample_code}`}
            caption={`Caja Petri · ${detail.petri_image.file_name}`}
          />
          <ProtectedImage
            endpoint={`/api/v1/micro-images/${detail.micro_image.id}/content`}
            alt={`Microscopía de la muestra ${detail.sample.sample_code}`}
            caption={`Microscopía · ${detail.micro_image.file_name}`}
          />
        </div>
      </section>

      <div className="detail-grid">
        <MetadataCard
          title="Muestra"
          entries={[
            ["Código", detail.sample.sample_code],
            ["Producto", detail.sample.product],
            ["Lote", detail.sample.lot_code],
            ["Origen", detail.sample.origin],
            ["Fecha de recolección", formatDate(detail.sample.collection_date)],
            ["Registro", formatDate(detail.sample.created_at)],
            ["Notas", detail.sample.notes],
          ]}
        />
        <MetadataCard
          title="Caja Petri"
          entries={[
            ["Archivo", detail.petri_image.file_name],
            ["Formato", detail.petri_image.mime_type],
            ["Tamaño", formatBytes(detail.petri_image.file_size_bytes)],
            ["Dimensiones", detail.petri_image.width && detail.petri_image.height ? `${detail.petri_image.width} × ${detail.petri_image.height}` : "—"],
            ["Medio de cultivo", detail.petri_image.culture_medium],
            ["Temperatura", detail.petri_image.incubation_temperature_c !== null ? `${detail.petri_image.incubation_temperature_c} °C` : null],
            ["Incubación", detail.petri_image.incubation_time_hours !== null ? `${detail.petri_image.incubation_time_hours} h` : null],
          ]}
        />
        <MetadataCard
          title="Microscopía"
          entries={[
            ["Archivo", detail.micro_image.file_name],
            ["Formato", detail.micro_image.mime_type],
            ["Tamaño", formatBytes(detail.micro_image.file_size_bytes)],
            ["Dimensiones", detail.micro_image.width && detail.micro_image.height ? `${detail.micro_image.width} × ${detail.micro_image.height}` : "—"],
            ["Aumento", detail.micro_image.magnification],
            ["Microscopio", detail.micro_image.microscope_type],
            ["Tinción", detail.micro_image.staining_method],
          ]}
        />
        <MetadataCard
          title="Ejecución"
          entries={[
            ["Estado", detail.analysis_run.status],
            ["Creado", formatDate(detail.analysis_run.created_at)],
            ["Iniciado", formatDate(detail.analysis_run.started_at)],
            ["Completado", formatDate(detail.analysis_run.completed_at)],
            ["Motor", `${detail.model_version.name} ${detail.model_version.version}`],
            ["Tipo", detail.model_version.model_type],
            ["Error", detail.analysis_run.error_message],
          ]}
        />
      </div>

      <div className="form-actions split-actions">
        <Link className="button button-secondary" to="/analyses">Volver al historial</Link>
        {!detail.human_review_completed && (
          <Link className="button button-primary" to={`/analyses/${analysisRunId}/review`}>Revisar análisis</Link>
        )}
      </div>
    </div>
  );
}
