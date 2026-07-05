# Two-Image Upload Preliminary Analysis API (Fase 40)

## Overview

Fase 40 adds a stateless endpoint that accepts two raw image uploads (Petri dish + microscopy) and returns a preliminary visual label immediately, **without requiring prior sample registration or an existing AnalysisRun**.

A second endpoint exposes the same "preliminary result" format for an already-processed `AnalysisRun`.

**Both endpoints use the mock inference engine. Results carry no diagnostic or taxonomic validity.**

---

## Endpoints

### POST /api/v1/analysis/two-image-upload

Upload a Petri dish photograph and a microscopy photograph. Both images are validated (MIME type, extension, Pillow-decodable format) and stored in `upload_storage_dir` for traceability. A preliminary visual label is returned immediately.

**Content-Type**: `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `petri_image` | file | yes | Petri dish photograph (JPEG/PNG/TIFF). Never a fruit photo. |
| `micro_image` | file | yes | Microscopy photograph from the same sample. |

**Response 200**:

```json
{
  "upload_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "predicted_label": "probable_fungal_growth",
  "confidence_score": 0.65,
  "class_probabilities": {
    "no_evident_growth": 0.0875,
    "suspicious_growth": 0.0875,
    "probable_fungal_growth": 0.65,
    "probable_bacterial_growth": 0.0875,
    "inconclusive": 0.0875
  },
  "requires_human_review": false,
  "disclaimer": "SIMULATED RESULT (mock inference engine — Fase 40 preliminary endpoint): ..."
}
```

Internal storage paths are **never** included in the response.

**Error responses**:
- `400 invalid_image` — corrupted, disallowed MIME/extension, or format mismatch
- `413 image_too_large` — file exceeds `BLUEBERRY_MICROID_UPLOAD_STORAGE_DIR` limit

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
  "technical_observation": "SIMULATED RESULT ...",
  "disclaimer": "This result was produced by a simulated (mock) inference engine ..."
}
```

**Error responses**:
- `404 analysis_run_not_found` — no such AnalysisRun
- `404 prediction_not_found` — AnalysisRun exists but has no Prediction yet (still pending or failed)

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
| `inconclusive` | Cannot be classified reliably (`requires_human_review=true`) |

These are broad, non-diagnostic visual categories. They **never** encode a species or genus and must not be interpreted as microbiological diagnoses.

---

## Restrictions (Fase 40)

- No authentication required (not added in this phase).
- No CORS headers (not added until a frontend phase is approved).
- No frontend or dashboard.
- No real inference engine — only `MockInferenceEngine` / `PreliminaryTwoImageAnalysisEngine`.
- No taxonomic labels, species, genus, or diagnostic claims.
- Internal file paths are never exposed in any API response.
