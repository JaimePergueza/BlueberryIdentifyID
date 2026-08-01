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
        aria-required="true"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
      {previewUrl ? <img src={previewUrl} alt={`Vista previa: ${label}`} /> : <span className="upload-icon" aria-hidden="true">＋</span>}
      <strong>{file ? file.name : label}</strong>
      <small>{file ? `${file.type || "Imagen"} · ${formatBytes(file.size)}` : hint}</small>
      {file && <span className="text-link">Cambiar archivo</span>}
    </label>
  );
}

function setOptional(body: FormData, key: string, value: string) {
  const clean = value.trim();
  if (clean) body.set(key, clean);
}

export function NewAnalysisPage() {
  const navigate = useNavigate();
  const [petriFile, setPetriFile] = useState<File | null>(null);
  const [microFile, setMicroFile] = useState<File | null>(null);
  const [sampleCode, setSampleCode] = useState("");
  const [lotCode, setLotCode] = useState("");
  const [origin, setOrigin] = useState("");
  const [collectionDate, setCollectionDate] = useState("");
  const [notes, setNotes] = useState("");
  const [cultureMedium, setCultureMedium] = useState("");
  const [incubationTemperature, setIncubationTemperature] = useState("");
  const [incubationTime, setIncubationTime] = useState("");
  const [magnification, setMagnification] = useState("");
  const [microscopeType, setMicroscopeType] = useState("");
  const [stainingMethod, setStainingMethod] = useState("");
  const [preparationMethod, setPreparationMethod] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (body: FormData) => apiRequest<UploadAnalysisResponse>("/api/v1/analysis/two-image-upload", { method: "POST", body }),
    onSuccess: (result) => navigate(`/analyses/${result.analysis_run_id}/preliminary`, { state: { uploaded: true } }),
    onError: (caught) => setError(caught instanceof ApiError ? caught.message : "No se pudo procesar el análisis."),
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
    setOptional(body, "sample_code", sampleCode);
    setOptional(body, "lot_code", lotCode);
    setOptional(body, "origin", origin);
    setOptional(body, "collection_date", collectionDate);
    setOptional(body, "notes", notes);
    setOptional(body, "culture_medium", cultureMedium);
    setOptional(body, "incubation_temperature_c", incubationTemperature);
    setOptional(body, "incubation_time_hours", incubationTime);
    setOptional(body, "magnification", magnification);
    setOptional(body, "microscope_type", microscopeType);
    setOptional(body, "staining_method", stainingMethod);
    setOptional(body, "preparation_method", preparationMethod);
    mutation.mutate(body);
  };

  return (
    <div className="page page-narrow">
      <div className="page-header">
        <div>
          <span className="eyebrow">Recorrido principal</span>
          <h1>Nuevo análisis</h1>
          <p>Registra la muestra, las condiciones de cultivo y una imagen Petri y microscópica del mismo aislamiento.</p>
        </div>
      </div>

      <form className="analysis-form" onSubmit={handleSubmit} noValidate>
        <section className="card">
          <div className="section-heading"><div><span className="step-number">1</span><h2>Identificación de la muestra</h2></div></div>
          <div className="form-grid">
            <label className="field">
              <span>Código de muestra <small>(opcional)</small></span>
              <input value={sampleCode} onChange={(event) => setSampleCode(event.target.value)} placeholder="Ej. BB-2026-014" maxLength={100} />
              <small>Si se omite, el sistema generará un código automático.</small>
            </label>
            <label className="field">
              <span>Lote <small>(recomendado)</small></span>
              <input value={lotCode} onChange={(event) => setLotCode(event.target.value)} placeholder="Ej. LOTE-CARCHI-07" maxLength={100} />
            </label>
            <label className="field">
              <span>Origen o procedencia <small>(recomendado)</small></span>
              <input value={origin} onChange={(event) => setOrigin(event.target.value)} placeholder="Finca, cantón, invernadero o proveedor" maxLength={255} />
            </label>
            <label className="field">
              <span>Fecha de recolección <small>(recomendado)</small></span>
              <input type="date" value={collectionDate} onChange={(event) => setCollectionDate(event.target.value)} />
            </label>
            <label className="field field-span-2">
              <span>Observaciones <small>(opcional)</small></span>
              <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Síntomas, condición del fruto, método de muestreo u otra información relevante" rows={3} />
            </label>
          </div>
        </section>

        <section className="card">
          <div className="section-heading"><div><span className="step-number">2</span><h2>Condiciones de cultivo</h2></div></div>
          <div className="form-grid">
            <label className="field">
              <span>Medio de cultivo <small>(recomendado)</small></span>
              <input value={cultureMedium} onChange={(event) => setCultureMedium(event.target.value)} placeholder="Ej. PDA, MEA, CYA, TSA" maxLength={100} />
            </label>
            <label className="field">
              <span>Temperatura de incubación (°C) <small>(recomendado)</small></span>
              <input type="number" min="0" max="60" step="0.1" value={incubationTemperature} onChange={(event) => setIncubationTemperature(event.target.value)} placeholder="Ej. 25" />
            </label>
            <label className="field">
              <span>Tiempo de incubación (horas) <small>(recomendado)</small></span>
              <input type="number" min="0" step="0.5" value={incubationTime} onChange={(event) => setIncubationTime(event.target.value)} placeholder="Ej. 168 para 7 días" />
            </label>
          </div>
          <div className="alert alert-info">
            <strong>Por qué se solicita</strong>
            <p>El color, textura, diámetro y esporulación de una colonia cambian con el medio, la temperatura y el tiempo.</p>
          </div>
        </section>

        <section className="card">
          <div className="section-heading"><div><span className="step-number">3</span><h2>Condiciones de microscopía</h2></div></div>
          <div className="form-grid">
            <label className="field">
              <span>Aumento total <small>(recomendado)</small></span>
              <input value={magnification} onChange={(event) => setMagnification(event.target.value)} placeholder="Ej. 400× o objetivo 40×" maxLength={50} />
            </label>
            <label className="field">
              <span>Tipo de microscopio <small>(recomendado)</small></span>
              <input value={microscopeType} onChange={(event) => setMicroscopeType(event.target.value)} placeholder="Ej. óptico de campo claro" maxLength={100} />
            </label>
            <label className="field">
              <span>Tinción o medio de montaje <small>(recomendado)</small></span>
              <input value={stainingMethod} onChange={(event) => setStainingMethod(event.target.value)} placeholder="Ej. azul de lactofenol, Gram, agua" maxLength={100} />
            </label>
            <label className="field">
              <span>Método de preparación <small>(opcional)</small></span>
              <input value={preparationMethod} onChange={(event) => setPreparationMethod(event.target.value)} placeholder="Ej. cinta adhesiva, microcultivo, frotis" maxLength={150} />
            </label>
          </div>
        </section>

        <section className="card">
          <div className="section-heading"><div><span className="step-number">4</span><h2>Imágenes de la misma muestra</h2></div></div>
          <div className="upload-grid">
            <ImageSelector label="Imagen de caja Petri" hint="JPEG, PNG o TIFF · caja completa y centrada" file={petriFile} onChange={setPetriFile} />
            <ImageSelector label="Imagen microscópica" hint="Mismo aislamiento · campo enfocado y representativo" file={microFile} onChange={setMicroFile} />
          </div>
        </section>

        <div className="alert alert-info">
          <strong>Resultado preliminar y diferencial</strong>
          <p>La herramienta calcula puntuaciones heurísticas y compara perfiles morfológicos asociados con arándanos. No confirma género o especie y exige revisión experta.</p>
        </div>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="form-actions">
          <button className="button button-primary button-large" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? "Analizando imágenes…" : "Ejecutar análisis preliminar"}
          </button>
        </div>
      </form>
    </div>
  );
}
