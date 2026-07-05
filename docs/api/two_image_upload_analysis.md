# Two-Image Upload Preliminary Analysis API (Fase 40.1)

## Overview

Fase 40.1 converts the stateless Fase 40 endpoint into a **fully persistent flow**. Uploading a Petri dish image and a microscopy image now creates real database entities (Sample, PetriImage, MicroImage, AnalysisRun, Prediction) and returns their actual identifiers.

**Key invariant:** `requires_human_review` is always `true` for results from this endpoint. All preliminary uploads require expert review regardless of the visual label.

Both endpoints use the simulated (mock) inference engine. Results carry no diagnostic or taxonomic validity.

---

## Endpoints

### POST /api/v1/analysis/two-image-upload

Upload a Petri dish photograph and a microscopy photograph. Both images are validated and stored; Sample, PetriImage, MicroImage, AnalysisRun and Prediction are created in the database. Real DB identifiers are returned.

**Content-Type**: `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `petri_image` | file | yes | Petri dish photograph (JPEG/PNG/TIFF). Never a fruit photo. |
| `micro_image` | file | yes | Microscopy photograph from the same sample. |
| `sample_code` | string | no | Optional lab sample code. Auto-generated (`AUTO-XXXXXXXX`) if omitted. |
| `notes` | string | no | Optional free-text notes for the sample. |

**Response 201**:

```json
{
  "analysis_run_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "sample_id": "1c2d3e4f-5678-9abc-def0-123456789abc",
  "petri_image_id": "aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb",
  "micro_image_id": "11112222-3333-4444-5555-666677778888",
  "predicted_label": "probable_fungal_growth",
  "confidence_score": 0.65,
  "class_probabilities": {
    "no_evident_growth": 0.0875,
    "suspicious_growth": 0.0875,
    "probable_fungal_growth": 0.65,
    "probable_bacterial_growth": 0.0875,
    "inconclusive": 0.0875
  },
  "requires_human_review": true,
  "disclaimer": "SIMULATED RESULT (mock inference engine — Fase 40 preliminary endpoint): ..."
}
```

Internal storage paths are **never** included in the response.

**Error responses**:
- `400 invalid_image` — corrupted, disallowed MIME/extension, or format mismatch
- `413 image_too_large` — file exceeds upload size limit

---

### GET /api/v1/analysis-runs/{analysis_run_id}/preliminary-result

Retrieve the `Prediction` produced by a previously processed `AnalysisRun`, formatted as a preliminary result.

**Response 200**:

```json
{
  "analysis_run_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "predicted_label": "no_evident_growth",
  "confidence_score": 0.60,
  "class_probabilities": { ... },
  "requires_human_review": false,
  "technical_observation": "...",
  "disclaimer": "This result was produced by a simulated (mock) inference engine ..."
}
```

**Error responses**:
- `404 analysis_run_not_found` — no such AnalysisRun
- `404 prediction_not_found` — AnalysisRun exists but has no Prediction yet

---

## Persistence flow

1. Validate both images (MIME, extension, Pillow-decodable, size limit)
2. Store petri image → upload storage (`uploads/petri/`)
3. Store micro image → upload storage (`uploads/micro/`)
   - If micro storage fails, petri file is deleted (no orphan files)
4. Create and persist `Sample` (auto-code if not provided)
5. Create and persist `PetriImage` linked to Sample
6. Create and persist `MicroImage` linked to Sample
7. Get or create `ModelVersion` for the preliminary engine
8. Create `AnalysisRun` (pending → processing → needs_review)
9. Run `PreliminaryTwoImageAnalysisEngine` (mock, no pixel inspection)
10. Create `Prediction` with `requires_human_review=True`
11. Persist `AnalysisRun` + `Prediction` atomically via `UnitOfWork`
12. Return real DB identifiers

The resulting `AnalysisRun` has status `needs_review` to signal that human expert review is required.

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `BLUEBERRY_MICROID_UPLOAD_STORAGE_DIR` | `<repo>/storage/uploads` | Directory for uploaded images. Must be **outside the repository** in production. |

Uploaded images are stored under `<upload_storage_dir>/petri/` and `<upload_storage_dir>/micro/` with UUID-based file names.

---

## Preliminary label classes

| Label | Meaning |
|---|---|
| `no_evident_growth` | No evident microbial growth detected visually |
| `suspicious_growth` | Possible but ambiguous growth pattern |
| `probable_fungal_growth` | Visual pattern consistent with fungal growth |
| `probable_bacterial_growth` | Visual pattern consistent with bacterial growth |
| `inconclusive` | Cannot be classified reliably |

These are broad, non-diagnostic visual categories. They **never** encode a species or genus and must not be interpreted as microbiological diagnoses.

All results from this endpoint have `requires_human_review=true` — expert review is always required for preliminary uploads.

---

## Restrictions (Fase 40.1)

- No authentication required (not added in this phase).
- No CORS headers (not added until a frontend phase is approved).
- No frontend or dashboard.
- No real inference engine — only `PreliminaryTwoImageAnalysisEngine` (simulated).
- No taxonomic labels, species, genus, or diagnostic claims.
- Internal file paths are never exposed in any API response.
- `HumanReview` is **not** created automatically — it requires a separate API call.
- Uploaded images are never added to training datasets automatically.
