# Official MVP Two-Image Analysis API

## Purpose

`POST /api/v1/analysis/two-image-upload` is the official analysis entry point
for the demonstrable MVP.

It receives two photographs from the same laboratory sample:

- a Petri dish image;
- a microscopy image.

The endpoint validates and stores both files, reads their real pixel content,
extracts transparent classical visual signals, applies non-trained heuristic
rules, persists the complete analysis trace, and returns a preliminary visual
category.

The result is **not a microbiological diagnosis** and does not identify genus
or species. Human expert review is mandatory for every analysis.

## Engine identity

The official flow uses:

- model name: `PreliminaryTwoImageEngine`;
- model version: `0.2.0`;
- model type: `classical`.

Version `0.1.0` was historically registered as `mock`. It is not reused by the
official MVP upload flow.

The classical engine uses Pillow, NumPy, and OpenCV image-processing operations.
It is not a trained machine-learning model and has not been scientifically
validated against a labelled dataset.

## POST /api/v1/analysis/two-image-upload

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---:|---|
| `petri_image` | file | yes | Petri dish photograph in an allowed image format. It must not be a photograph of the fruit. |
| `micro_image` | file | yes | Microscopy photograph from the same sample. |
| `sample_code` | string | no | Laboratory code. An `AUTO-XXXXXXXX` code is generated when omitted. |
| `notes` | string | no | Optional sample notes. |

### Successful response

Status: `201 Created`

```json
{
  "analysis_run_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "prediction_id": "4985f64a-5717-4562-b3fc-2c963f66afa6",
  "sample_id": "1c2d3e4f-5678-9abc-def0-123456789abc",
  "petri_image_id": "aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb",
  "micro_image_id": "11112222-3333-4444-5555-666677778888",
  "predicted_label": "probable_fungal_growth",
  "confidence_score": 0.55,
  "class_probabilities": {
    "no_evident_growth": 0.1125,
    "suspicious_growth": 0.1125,
    "probable_fungal_growth": 0.55,
    "probable_bacterial_growth": 0.1125,
    "inconclusive": 0.1125
  },
  "requires_human_review": true,
  "disclaimer": "PRELIMINARY RESULT ...",
  "explanation": "Candidate growth regions were detected ...",
  "feature_summary": {
    "petri": {},
    "micro": {}
  },
  "quality_summary": {},
  "decision_trace": [],
  "warnings": []
}
```

Internal storage paths are never returned.

### Validation errors

- `400 invalid_image`: corrupt content, disallowed format, or mismatch between
  extension, MIME type, and decoded image.
- `413 image_too_large`: uploaded file exceeds the configured maximum size.

## Persistent workflow

1. Validate both files.
2. Store the Petri image.
3. Store the microscopy image.
4. Create the `Sample`.
5. Create `PetriImage` and `MicroImage` records linked to the sample.
6. Register or reuse `PreliminaryTwoImageEngine` version `0.2.0` as
   `ModelType.CLASSICAL`.
7. Create the `AnalysisRun`.
8. Extract real visual signals from both images.
9. Apply transparent heuristic rules.
10. Persist the `Prediction` and mark the run as `needs_review`.
11. Return the real database identifiers.

If microscopy file storage fails after the Petri file was saved, the Petri file
is deleted as compensation.

## Reading the result

### GET /api/v1/analysis-runs/{analysis_run_id}/preliminary-result

Returns the automatic prediction, explanation, visual features, quality flags,
warnings, and the current human-review status.

### GET /api/v1/analysis-runs/{analysis_run_id}/final-result

Returns the immutable automatic prediction together with the current final
expert review. Until a final review exists, the status is
`pending_human_review`.

### POST /api/v1/analysis-runs/{analysis_run_id}/reviews

Records an expert decision without overwriting the original prediction. The
reviewer may confirm, correct, mark the result inconclusive, or reject an
invalid sample.

## Preliminary visual categories

| Value | User-facing meaning |
|---|---|
| `no_evident_growth` | No evident growth |
| `suspicious_growth` | Suspicious or ambiguous growth |
| `probable_fungal_growth` | Probable fungal-type visual pattern |
| `probable_bacterial_growth` | Probable bacterial-type visual pattern |
| `inconclusive` | Inconclusive result |

These labels are broad visual categories. They are not taxonomic labels and
must not be presented as confirmed laboratory findings.

## Legacy mock pipeline

The repository still contains `MockInferenceEngine` for older synchronous and
Celery pipeline tests. Those routes validate orchestration and state changes;
they do not inspect image pixels. The frontend MVP must use
`POST /api/v1/analysis/two-image-upload` instead.

## Current MVP limitations

- Authentication and frontend are handled by later MVP issues.
- The classical thresholds are technical heuristics, not expert-validated
  microbiological decision limits.
- No species or genus identification exists.
- No automatic training-dataset inclusion occurs.
- Every result requires human review.
