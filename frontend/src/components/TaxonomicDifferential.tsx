interface TaxonomicDifferentialProps {
  differential: unknown;
}

interface Candidate {
  id: string;
  displayName: string;
  compatibilityIndex: number | null;
  compatibilityLabel: string;
  reportedExamples: string[];
  supportingEvidence: string[];
  missingEvidence: string[];
  requiredConfirmation: string[];
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function parseCandidate(value: unknown): Candidate | null {
  const record = asRecord(value);
  const id = typeof record.id === "string" ? record.id : null;
  const displayName = typeof record.display_name === "string" ? record.display_name : null;
  if (!id || !displayName) return null;
  return {
    id,
    displayName,
    compatibilityIndex: finiteNumber(record.compatibility_index),
    compatibilityLabel: typeof record.compatibility_label === "string"
      ? record.compatibility_label
      : "sin valoración",
    reportedExamples: stringList(record.reported_blueberry_examples),
    supportingEvidence: stringList(record.supporting_evidence),
    missingEvidence: stringList(record.missing_or_contradictory_evidence),
    requiredConfirmation: stringList(record.required_confirmation),
  };
}

function statusLabel(status: unknown): string {
  if (status === "available") return "Diferencial disponible";
  if (status === "insufficient") return "Evidencia insuficiente";
  if (status === "unavailable") return "Diferencial no disponible";
  return "Estado no disponible";
}

function HypothesisList({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (items.length === 0) return null;
  return (
    <div className={`taxonomy-evidence taxonomy-evidence-${tone}`}>
      <strong>{title}</strong>
      <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>
    </div>
  );
}

export function TaxonomicDifferential({ differential }: TaxonomicDifferentialProps) {
  const record = asRecord(differential);
  if (Object.keys(record).length === 0) return null;

  const status = record.status;
  const summary = typeof record.summary === "string" ? record.summary : "";
  const scope = typeof record.scope === "string" ? record.scope : "";
  const semantics = typeof record.score_semantics === "string" ? record.score_semantics : "";
  const engine = asRecord(record.engine);
  const broad = asRecord(record.broad_interpretation);
  const macro = stringList(asRecord(record.morphological_description).macroscopy);
  const micro = stringList(asRecord(record.morphological_description).microscopy);
  const confirmation = stringList(record.confirmation_required);
  const limitations = stringList(record.limitations);
  const candidates = Array.isArray(record.candidates)
    ? record.candidates.map(parseCandidate).filter((candidate): candidate is Candidate => candidate !== null)
    : [];
  const broadIndex = finiteNumber(broad.compatibility_index);

  return (
    <section className="taxonomy-differential" aria-label="Hipótesis taxonómica orientativa">
      <article className="card taxonomy-summary-card">
        <div className="section-heading taxonomy-heading">
          <div>
            <span className="eyebrow">Interpretación microbiológica orientativa</span>
            <h2>Diferencial morfológico para arándanos</h2>
            <p>{summary}</p>
          </div>
          <span className={`taxonomy-status taxonomy-status-${String(status)}`}>{statusLabel(status)}</span>
        </div>

        {Object.keys(broad).length > 0 && (
          <div className="taxonomy-broad-result">
            <div>
              <span>Interpretación general</span>
              <strong>{typeof broad.label === "string" ? broad.label : "—"}</strong>
            </div>
            <div>
              <span>Compatibilidad visual amplia</span>
              <strong>{broadIndex === null ? "—" : `${Math.round(broadIndex * 100)}%`}</strong>
            </div>
          </div>
        )}

        <small className="taxonomy-disclaimer">
          {semantics} {scope ? `Alcance: ${scope}.` : ""}
        </small>
      </article>

      {(macro.length > 0 || micro.length > 0) && (
        <div className="taxonomy-description-grid">
          <article className="card">
            <span className="eyebrow">Descripción automática</span>
            <h3>Macroscopia</h3>
            <ul className="scope-list">{macro.map((item) => <li key={item}>{item}</li>)}</ul>
          </article>
          <article className="card">
            <span className="eyebrow">Descripción automática</span>
            <h3>Microscopía</h3>
            <ul className="scope-list">{micro.map((item) => <li key={item}>{item}</li>)}</ul>
          </article>
        </div>
      )}

      {candidates.length > 0 && (
        <div className="taxonomy-candidate-grid">
          {candidates.map((candidate) => (
            <article className="card taxonomy-candidate" key={candidate.id}>
              <div className="taxonomy-candidate-heading">
                <div>
                  <span className="eyebrow">Hipótesis diferencial</span>
                  <h3>{candidate.displayName}</h3>
                  <p>{candidate.compatibilityLabel}</p>
                </div>
                <strong className="taxonomy-index">
                  {candidate.compatibilityIndex === null ? "—" : `${Math.round(candidate.compatibilityIndex * 100)}%`}
                </strong>
              </div>
              <progress max={1} value={candidate.compatibilityIndex ?? 0} />
              <small>Índice heurístico; no es una probabilidad ni confirma un género.</small>
              {candidate.reportedExamples.length > 0 && (
                <div className="taxonomy-evidence taxonomy-evidence-examples">
                  <strong>Ejemplos reportados en arándanos</strong>
                  <p>{candidate.reportedExamples.join(" · ")}</p>
                </div>
              )}
              <HypothesisList title="Rasgos que apoyan" items={candidate.supportingEvidence} tone="support" />
              <HypothesisList title="Rasgos ausentes o no demostrados" items={candidate.missingEvidence} tone="missing" />
              <HypothesisList title="Cómo confirmarlo" items={candidate.requiredConfirmation} tone="confirm" />
            </article>
          ))}
        </div>
      )}

      {(confirmation.length > 0 || limitations.length > 0) && (
        <article className="card taxonomy-scope-card">
          <div className="taxonomy-description-grid">
            <div>
              <h3>Confirmación requerida</h3>
              <ul className="scope-list">{confirmation.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <h3>Límites del resultado</h3>
              <ul className="scope-list">{limitations.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
          <small>
            Motor: {typeof engine.name === "string" ? engine.name : "—"} {typeof engine.version === "string" ? engine.version : ""}
          </small>
        </article>
      )}
    </section>
  );
}
