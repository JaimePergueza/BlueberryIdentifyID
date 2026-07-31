import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { ApiError, apiRequest } from "../lib/api";
import { formatBytes } from "../lib/format";
import type { UploadAnalysisResponse } from "../types/api";

interface SelectedImageProps {
  label: string;
  hint: string;
  file: File | null;
  onChange: (file: File | null) => void;
}

function ImageSelector({ label, hint, file, onChange }: SelectedImageProps) {
  const previewUrl = useMemo(
    () => (file && file.type !== "image/tiff" ? URL.createObjectURL(file) : null),
    [file],
  );

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  return (
    <label className={`upload-zone ${file ? "has-file" : ""}`}>
      <input
        type="file"
        accept="image/jpeg,image/png,image/tiff,.jpg,.jpeg,.png,.tif,.tiff"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        required
      />
      {previewUrl ? (
        <img src={previewUrl} alt={`Vista previa: ${label}`} />
      ) : (
        <span className="upload-icon" aria-hidden="true">＋</span>
      )}
      <strong>{file ? file.name : label}</strong>
      <small>{file ? `${file.type || "Imagen"} · ${formatBytes(file.size)}` : hint}</small>
      {file && <span className="text-link">Cambiar archivo</span>}
    </label>
  );
}

export function NewAnalysisPage() {
  const navigate = useNavigate();
  const [petriFile, setPetriFile] = useState<File | null>(null);
  const [microFile, setMicroFile] = useState<File | null>(null);
  const [sampleCode, setSampleCode] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (body: FormData) =>
      apiRequest<UploadAnalysisResponse>("/api/v1/analysis/two-image-upload", {
        method: "POST",
        body,
      }),
    onSuccess: (result) => {
      navigate(`/analyses/${result.analysis_run_id}/preliminary`, {
        state: { uploaded: true },
      });
    },
    onError: (caught) => {
      setError(caught instanceof ApiError ? caught.message : "No se pudo procesar el análisis.");
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!petriFile || !microFile) {
      setError("Selecciona las dos imágenes de la misma muestra.");
      return;
    }
    const body = new FormData();
    body.set("petri_image", petriFile);
    body.set("micro_image", microFile);
    if (sampleCode.trim()) body.set("sample_code", sampleCode.trim());
    if (notes.trim()) body.set("notes", notes.trim());
    mutation.mutate(body);
  };

  return (
    <div className="page page-narrow">
      <div className="page-header">
        <div>
          <span className="eyebrow">Recorrido principal</span>
          <h1>Nuevo análisis</h1>
          <p>Carga una fotografía de caja Petri y una imagen microscópica de la misma muestra.</p>
        </div>
      </div>

      <form className="analysis-form" onSubmit={handleSubmit}>
        <section className="card">
          <div className="section-heading">
            <div>
              <span className="step-number">1</span>
              <h2>Identificación de la muestra</h2>
            </div>
          </div>
          <div className="form-grid">
            <label className="field">
              <span>Código de muestra <small>(opcional)</small></span>
              <input
                value={sampleCode}
                onChange={(event) => setSampleCode(event.target.value)}
                placeholder="Ej. BB-2026-014"
                maxLength={100}
              />
              <small>Si se omite, el sistema generará un código automático.</small>
            </label>
            <label className="field">
              <span>Observaciones <small>(opcional)</small></span>
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Lote, procedencia o información relevante"
                rows={3}
              />
            </label>
          </div>
        </section>

        <section className="card">
          <div className="section-heading">
            <div>
              <span className="step-number">2</span>
              <h2>Imágenes de la misma muestra</h2>
            </div>
          </div>
          <div className="upload-grid">
            <ImageSelector
              label="Imagen de caja Petri"
              hint="JPEG, PNG o TIFF · máximo configurado por el servidor"
              file={petriFile}
              onChange={setPetriFile}
            />
            <ImageSelector
              label="Imagen microscópica"
              hint="Debe corresponder a la misma muestra"
              file={microFile}
              onChange={setMicroFile}
            />
          </div>
        </section>

        <div className="alert alert-info">
          <strong>Resultado preliminar</strong>
          <p>La herramienta analiza patrones visuales; no identifica género o especie y exige revisión experta.</p>
        </div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="form-actions">
          <button
            className="button button-primary button-large"
            disabled={mutation.isPending}
            type="submit"
          >
            {mutation.isPending ? "Analizando imágenes…" : "Ejecutar análisis preliminar"}
          </button>
        </div>
      </form>
    </div>
  );
}
