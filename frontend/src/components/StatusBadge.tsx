import { labelName, statusName } from "../lib/format";
import type { AnalysisStatus, PredictedLabel } from "../types/api";

export function AnalysisStatusBadge({ status }: { status: AnalysisStatus }) {
  return <span className={`badge badge-${status}`}>{statusName(status)}</span>;
}

export function LabelBadge({ label }: { label: PredictedLabel | null }) {
  return <span className={`badge badge-label badge-${label ?? "empty"}`}>{labelName(label)}</span>;
}

export function ReviewBadge({ reviewed }: { reviewed: boolean }) {
  return (
    <span className={`badge ${reviewed ? "badge-reviewed" : "badge-pending-review"}`}>
      {reviewed ? "Revisado" : "Pendiente de revisión"}
    </span>
  );
}
