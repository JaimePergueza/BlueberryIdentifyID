import type { AnalysisStatus, PredictedLabel, ReviewDecision } from "../types/api";

const LABELS: Record<PredictedLabel, string> = {
  no_evident_growth: "Sin crecimiento evidente",
  suspicious_growth: "Crecimiento sospechoso",
  probable_fungal_growth: "Probable crecimiento fúngico",
  probable_bacterial_growth: "Probable crecimiento bacteriano",
  inconclusive: "No concluyente",
};

const STATUS: Record<AnalysisStatus, string> = {
  pending: "Pendiente",
  processing: "Procesando",
  completed: "Completado",
  needs_review: "Requiere revisión",
  failed: "Fallido",
};

const DECISIONS: Record<ReviewDecision, string> = {
  confirmed: "Confirmado",
  corrected: "Corregido",
  marked_inconclusive: "Marcado como no concluyente",
  rejected_invalid_sample: "Muestra rechazada",
};

export function labelName(value: PredictedLabel | null | undefined): string {
  return value ? LABELS[value] : "Sin resultado";
}

export function statusName(value: AnalysisStatus): string {
  return STATUS[value];
}

export function decisionName(value: ReviewDecision | null | undefined): string {
  return value ? DECISIONS[value] : "Pendiente de revisión";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("es-EC", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("es-EC", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}
