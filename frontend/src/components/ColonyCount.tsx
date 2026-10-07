interface ColonyCountProps {
  assessment: unknown;
}

const reasons: Record<string, string> = {
  extraction_failed: "No se pudo procesar la placa.",
  plate_not_detected: "No se aisló el límite de la placa.",
  invalid_candidate_count: "El número de regiones no está disponible.",
  insufficient_focus: "El enfoque es insuficiente para contar.",
  unsuitable_exposure: "La exposición no permite interpretar las regiones.",
  invalid_coverage: "La cobertura detectada no es interpretable.",
  segmentation_uncertain: "La segmentación presenta conflictos.",
  connected_growth: "Hay crecimiento conectado o confluente.",
  high_coverage: "El crecimiento ocupa una superficie demasiado amplia.",
  too_many_candidates: "La densidad de regiones requiere conteo manual.",
};

export function ColonyCount({ assessment }: ColonyCountProps) {
  if (!assessment || typeof assessment !== "object" || Array.isArray(assessment)) return null;
  const value = assessment as Record<string, unknown>;
  const count = typeof value.estimated_count === "number" && Number.isInteger(value.estimated_count)
    && value.estimated_count >= 0 ? value.estimated_count : null;
  const available = value.status === "preliminary" && count !== null;
  const reasonCodes = Array.isArray(value.reason_codes)
    ? value.reason_codes.filter((item): item is string => typeof item === "string") : [];
  const warnings = Array.isArray(value.warnings)
    ? value.warnings.filter((item): item is string => typeof item === "string") : [];

  return (
    <article className="card" aria-label="Conteo preliminar de colonias">
      <span className="eyebrow">Caja Petri</span>
      <h2>{available ? "Conteo visual preliminar" : "Conteo automático no disponible"}</h2>
      {available ? (
        <p className="large-value">{count} <small>regiones candidatas</small></p>
      ) : (
        <p>Revisa la placa o repite la captura antes de registrar un número.</p>
      )}
      {reasonCodes.length > 0 && <ul>{reasonCodes.map((code) => (
        <li key={code}>{reasons[code] ?? "La captura requiere revisión."}</li>
      ))}</ul>}
      {warnings.length > 0 && <ul>{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}
      <p>El especialista puede confirmar o corregir el conteo. Este valor no representa UFC/mL.</p>
    </article>
  );
}
