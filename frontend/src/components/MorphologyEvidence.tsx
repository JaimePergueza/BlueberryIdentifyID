interface MorphologyEvidenceProps {
  featureSummary: Record<string, unknown> | null;
  qualitySummary: Record<string, unknown> | null;
  decisionTrace: unknown[] | null;
}

type MetricKind = "number" | "percent" | "boolean";

interface MetricDefinition {
  key: string;
  label: string;
  kind?: MetricKind;
  digits?: number;
}

const petriMetrics: MetricDefinition[] = [
  { key: "region_count", label: "Regiones candidatas" },
  { key: "colony_coverage", label: "Cobertura candidata", kind: "percent" },
  { key: "candidate_signal_fraction", label: "Señal visual candidata", kind: "percent" },
  { key: "mean_region_area_fraction", label: "Área media por región", kind: "percent" },
  { key: "mean_circularity", label: "Circularidad media", digits: 3 },
  { key: "edge_irregularity", label: "Irregularidad del borde", digits: 3 },
  { key: "mean_texture_std", label: "Variación de textura", digits: 2 },
  { key: "mean_saturation", label: "Saturación media", kind: "percent" },
  { key: "plate_detected", label: "Placa aislada", kind: "boolean" },
  { key: "confluent_growth_detected", label: "Crecimiento confluente refinado", kind: "boolean" },
  { key: "segmentation_conflict", label: "Conflicto de segmentación", kind: "boolean" },
];

const microMetrics: MetricDefinition[] = [
  { key: "edge_density", label: "Densidad de bordes", kind: "percent" },
  { key: "filament_coverage", label: "Cobertura filamentosa", kind: "percent" },
  { key: "skeleton_density", label: "Densidad del esqueleto", kind: "percent" },
  { key: "branch_point_density", label: "Puntos de ramificación", kind: "percent" },
  { key: "elongated_component_ratio", label: "Componentes alargados", kind: "percent" },
  { key: "component_count", label: "Componentes estructurales" },
  { key: "field_coverage", label: "Campo analizado", kind: "percent" },
  { key: "field_detected", label: "Campo circular aislado", kind: "boolean" },
];

const qualityLabels: Record<string, string> = {
  petri_is_sharp: "Enfoque Petri suficiente",
  petri_overexposed: "Petri sobreexpuesta",
  petri_underexposed: "Petri subexpuesta",
  petri_plate_detected: "Límite de placa detectado",
  petri_segmentation_conflict: "Conflicto de segmentación Petri",
  petri_confluent_growth_detected: "Crecimiento confluente refinado",
  micro_is_sharp: "Enfoque microscópico suficiente",
  micro_field_detected: "Campo microscópico detectado",
  micro_appears_empty: "Campo microscópico posiblemente vacío",
  petri_extraction_ok: "Extracción Petri completada",
  micro_extraction_ok: "Extracción microscópica completada",
};

const simpleQualityKeys = Object.keys(qualityLabels);

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function formatMetric(value: unknown, definition: MetricDefinition): string {
  if (definition.kind === "boolean") return value === true ? "Sí" : value === false ? "No" : "—";
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  if (definition.kind === "percent") {
    return new Intl.NumberFormat("es-EC", { style: "percent", maximumFractionDigits: 2 }).format(value);
  }
  return new Intl.NumberFormat("es-EC", {
    maximumFractionDigits: definition.digits ?? 2,
  }).format(value);
}

function MetricCard({
  eyebrow,
  title,
  metrics,
  values,
}: {
  eyebrow: string;
  title: string;
  metrics: MetricDefinition[];
  values: Record<string, unknown>;
}) {
  return (
    <article className="card morphology-card">
      <span className="eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      <dl className="morphology-metric-list">
        {metrics.map((metric) => (
          <div key={metric.key}>
            <dt>{metric.label}</dt>
            <dd>{formatMetric(values[metric.key], metric)}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function qualityStatusName(status: unknown): string {
  if (status === "accepted") return "Captura aceptada";
  if (status === "warning") return "Captura aceptada con advertencias";
  if (status === "rejected") return "Captura rechazada para interpretación";
  return "Estado de calidad no disponible";
}

function isPositiveQualityFlag(key: string, value: boolean): boolean {
  const negativeWhenTrue = [
    "overexposed",
    "underexposed",
    "empty",
    "conflict",
    "confluent",
  ].some((token) => key.includes(token));
  return negativeWhenTrue ? value === false : value === true;
}

export function MorphologyEvidence({ featureSummary, qualitySummary, decisionTrace }: MorphologyEvidenceProps) {
  if (!featureSummary && !qualitySummary) return null;

  const petri = asRecord(featureSummary?.petri);
  const micro = asRecord(featureSummary?.micro);
  const quality = asRecord(qualitySummary);
  const status = quality.overall_status;
  const blockingReasons = stringList(quality.blocking_reasons);
  const warningReasons = stringList(quality.warning_reasons);
  const qualityScore = typeof quality.quality_score === "number" ? quality.quality_score : null;
  const fusion = (decisionTrace ?? [])
    .map(asRecord)
    .find((step) => step.step === "evidence_fusion") ?? {};

  const scores = [
    ["Evidencia macroscópica", fusion.macro_growth_score],
    ["Evidencia filamentosa", fusion.filamentous_score],
    ["Evidencia celular", fusion.cellular_score],
  ] as const;

  return (
    <section className="morphology-evidence" aria-label="Evidencia morfológica automática">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Análisis explicable</span>
          <h2>Evidencia morfológica</h2>
          <p>Mediciones visuales empleadas por el motor. No equivalen a una identificación taxonómica.</p>
        </div>
      </div>

      <div className="morphology-grid">
        <MetricCard eyebrow="Macroscopia" title="Caja Petri" metrics={petriMetrics} values={petri} />
        <MetricCard eyebrow="Microscopía" title="Estructuras visibles" metrics={microMetrics} values={micro} />
      </div>

      {Object.keys(fusion).length > 0 && (
        <article className="card morphology-score-card">
          <div className="section-heading"><h2>Fusión de evidencia</h2></div>
          <div className="evidence-score-grid">
            {scores.map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{typeof value === "number" ? `${Math.round(value * 100)}%` : "—"}</strong>
                <progress max={1} value={typeof value === "number" ? value : 0} />
              </div>
            ))}
          </div>
        </article>
      )}

      {Object.keys(quality).length > 0 && (
        <article className="card morphology-quality-card">
          <div className="section-heading quality-heading">
            <div>
              <span className="eyebrow">Puerta de calidad</span>
              <h2>{qualityStatusName(status)}</h2>
              {qualityScore !== null && <p>Puntuación técnica de captura: {Math.round(qualityScore * 100)}%</p>}
            </div>
            <span className={`quality-status quality-status-${String(status)}`}>{String(status ?? "unknown")}</span>
          </div>

          {blockingReasons.length > 0 && (
            <div className="quality-reason-block quality-reason-blocking">
              <strong>Condiciones bloqueantes</strong>
              <ul>{blockingReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
            </div>
          )}
          {warningReasons.length > 0 && (
            <div className="quality-reason-block quality-reason-warning">
              <strong>Advertencias</strong>
              <ul>{warningReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
            </div>
          )}

          <div className="quality-chip-grid">
            {simpleQualityKeys.map((key) => {
              const value = quality[key];
              if (typeof value !== "boolean") return null;
              const positive = isPositiveQualityFlag(key, value);
              return (
                <span className={`quality-chip ${positive ? "quality-chip-good" : "quality-chip-warning"}`} key={key}>
                  {qualityLabels[key]}: {value ? "Sí" : "No"}
                </span>
              );
            })}
          </div>
        </article>
      )}
    </section>
  );
}