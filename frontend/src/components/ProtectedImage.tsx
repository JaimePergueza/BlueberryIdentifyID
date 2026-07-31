import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiBlob } from "../lib/api";
import "../styles/stored-images.css";

interface ProtectedImageProps {
  endpoint: string;
  alt: string;
  caption: string;
  overlay?: unknown;
}

interface Point {
  x: number;
  y: number;
}

interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface OverlayRegion {
  id: string | number;
  role: string;
  bbox: Box | null;
  polygon: Point[];
}

interface ParsedOverlay {
  kind: "petri" | "micro" | "unknown";
  imageWidth: number | null;
  imageHeight: number | null;
  outline: Record<string, unknown> | null;
  regions: OverlayRegion[];
  branchPoints: Point[];
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function parsePoint(value: unknown): Point | null {
  const record = asRecord(value);
  const x = finiteNumber(record.x);
  const y = finiteNumber(record.y);
  return x === null || y === null ? null : { x, y };
}

function parseBox(value: unknown): Box | null {
  const record = asRecord(value);
  const x = finiteNumber(record.x);
  const y = finiteNumber(record.y);
  const width = finiteNumber(record.width);
  const height = finiteNumber(record.height);
  return x === null || y === null || width === null || height === null
    ? null
    : { x, y, width, height };
}

function parseOverlay(value: unknown): ParsedOverlay | null {
  const record = asRecord(value);
  if (record.coordinate_space !== "normalized") return null;

  const regions = Array.isArray(record.regions)
    ? record.regions.map((entry, index) => {
        const region = asRecord(entry);
        const polygon = Array.isArray(region.polygon)
          ? region.polygon.map(parsePoint).filter((point): point is Point => point !== null)
          : [];
        return {
          id: typeof region.id === "string" || typeof region.id === "number" ? region.id : index,
          role: typeof region.role === "string" ? region.role : "structure_component",
          bbox: parseBox(region.bbox),
          polygon,
        };
      })
    : [];

  const branchPoints = Array.isArray(record.branch_points)
    ? record.branch_points.map(parsePoint).filter((point): point is Point => point !== null)
    : [];

  const kind = record.kind === "petri" || record.kind === "micro" ? record.kind : "unknown";
  return {
    kind,
    imageWidth: finiteNumber(record.image_width),
    imageHeight: finiteNumber(record.image_height),
    outline: Object.keys(asRecord(record.outline)).length > 0 ? asRecord(record.outline) : null,
    regions,
    branchPoints,
  };
}

function pointsAttribute(points: Point[]): string {
  return points.map((point) => `${point.x},${point.y}`).join(" ");
}

function SegmentationOverlay({ overlay }: { overlay: ParsedOverlay }) {
  const outlineType = overlay.outline?.type;
  const outlinePoints = Array.isArray(overlay.outline?.points)
    ? overlay.outline.points.map(parsePoint).filter((point): point is Point => point !== null)
    : [];

  return (
    <svg
      className={`segmentation-overlay segmentation-overlay-${overlay.kind}`}
      viewBox="0 0 1 1"
      preserveAspectRatio="none"
      role="img"
      aria-label="Regiones detectadas por el motor"
    >
      {outlineType === "ellipse" && (
        <ellipse
          className="segmentation-outline"
          cx={finiteNumber(overlay.outline?.cx) ?? 0.5}
          cy={finiteNumber(overlay.outline?.cy) ?? 0.5}
          rx={finiteNumber(overlay.outline?.rx) ?? 0.45}
          ry={finiteNumber(overlay.outline?.ry) ?? 0.45}
        />
      )}
      {outlineType === "polygon" && outlinePoints.length >= 3 && (
        <polygon className="segmentation-outline" points={pointsAttribute(outlinePoints)} />
      )}

      {overlay.regions.map((region) => {
        const className = region.role === "candidate_colony"
          ? "segmentation-region segmentation-colony"
          : region.role === "filament_component"
            ? "segmentation-region segmentation-filament"
            : "segmentation-region segmentation-structure";
        if (region.polygon.length >= 3) {
          return <polygon key={region.id} className={className} points={pointsAttribute(region.polygon)} />;
        }
        if (region.bbox) {
          return (
            <rect
              key={region.id}
              className={className}
              x={region.bbox.x}
              y={region.bbox.y}
              width={region.bbox.width}
              height={region.bbox.height}
            />
          );
        }
        return null;
      })}

      {overlay.branchPoints.map((point, index) => (
        <circle
          className="segmentation-branch-point"
          key={`${point.x}-${point.y}-${index}`}
          cx={point.x}
          cy={point.y}
          r={0.0055}
        />
      ))}
    </svg>
  );
}

export function ProtectedImage({ endpoint, alt, caption, overlay }: ProtectedImageProps) {
  const query = useQuery({
    queryKey: ["protected-image", endpoint],
    queryFn: () => apiBlob(endpoint),
    staleTime: 5 * 60_000,
  });
  const source = useMemo(
    () => (query.data ? URL.createObjectURL(query.data) : null),
    [query.data],
  );
  const parsedOverlay = useMemo(() => parseOverlay(overlay), [overlay]);
  const [showOverlay, setShowOverlay] = useState(true);

  useEffect(
    () => () => {
      if (source) URL.revokeObjectURL(source);
    },
    [source],
  );

  const aspectRatio = parsedOverlay?.imageWidth && parsedOverlay.imageHeight
    ? `${parsedOverlay.imageWidth} / ${parsedOverlay.imageHeight}`
    : "4 / 3";
  const overlayItemCount = (parsedOverlay?.regions.length ?? 0) + (parsedOverlay?.branchPoints.length ?? 0);

  return (
    <figure className="protected-image">
      <div className="protected-image-frame">
        {query.isLoading && <span className="spinner" aria-label={`Cargando ${caption}`} />}
        {query.isError && <span className="image-unavailable">Imagen no disponible</span>}
        {source && (
          <div className="protected-image-canvas" style={{ aspectRatio }}>
            <img src={source} alt={alt} />
            {showOverlay && parsedOverlay && <SegmentationOverlay overlay={parsedOverlay} />}
          </div>
        )}
      </div>
      <div className="protected-image-caption-row">
        <figcaption>{caption}</figcaption>
        {parsedOverlay && (
          <button
            className="overlay-toggle"
            type="button"
            aria-pressed={showOverlay}
            onClick={() => setShowOverlay((current) => !current)}
          >
            {showOverlay ? "Ocultar detección" : "Mostrar detección"}
          </button>
        )}
      </div>
      {parsedOverlay && (
        <small className="overlay-summary">
          {overlayItemCount} elemento(s) visualizados. Las marcas representan detecciones automáticas, no confirmaciones microbiológicas.
        </small>
      )}
    </figure>
  );
}
