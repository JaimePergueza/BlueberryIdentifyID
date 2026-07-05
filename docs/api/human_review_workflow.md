# Human Review Workflow for Preliminary Analysis Results

**Fase 42** — connects the two-image upload preliminary result with the expert
human review system so every preliminary classification can be audited,
confirmed, corrected, or rejected by a domain expert.

---

## Overview

```
POST /api/v1/analysis/two-image-upload
         │
         ▼
   Sample + PetriImage + MicroImage + AnalysisRun + Prediction
   (requires_human_review = true, status = needs_review)
         │
         ▼
GET /api/v1/analysis-runs/{id}/preliminary-result
   (shows automatic result + current review status)
         │
         ▼
POST /api/v1/analysis-runs/{id}/reviews
   (expert submits review decision)
         │
         ▼
GET /api/v1/analysis-runs/{id}/final-result
   (automatic Prediction + human review → resolved final_label)
```

---

## Preliminary visual categories (all five)

| Label | Description |
|---|---|
| `no_evident_growth` | No candidate growth regions detected in the Petri image |
| `suspicious_growth` | Growth signal present but microscopy structure ambiguous |
| `probable_fungal_growth` | High structural complexity in microscopy |
| `probable_bacterial_growth` | Dense cellular morphology in microscopy |
| `inconclusive` | Signals present but no heuristic rule matches |

**None of these are microbiological identifications.** They are preliminary
visual categories that require expert review.  No species, genus, or
diagnostic conclusion is ever asserted by the system.

---

## Expert review decisions

| Decision | Effect on `final_label` | When to use |
|---|---|---|
| `confirmed` | `= Prediction.predicted_label` | Expert agrees with the automatic result |
| `corrected` | `= corrected_label` (required) | Expert assigns a different visual category |
| `marked_inconclusive` | `= inconclusive` | Expert cannot determine a category |
| `rejected_invalid_sample` | `= null` | Plate is not suitable for analysis |

`rejected_invalid_sample` items are **never** used as ground truth for future
training.  `confirmed`, `corrected`, and `marked_inconclusive` *may* be used
in future dataset curation phases (explicit action required — no automatic
export).

Fase 44 makes that explicit action a separate snapshot step:
`POST /api/v1/datasets/snapshots/from-curation-run` can freeze an already
completed `DatasetCurationRun` into a `DatasetSnapshot`. The snapshot keeps
metadata-only provenance back to the curation item and final human review. It
does not create releases, split data, train, copy images, or add taxonomy.

---

## Endpoints

### POST `/api/v1/analysis-runs/{analysis_run_id}/reviews`

Submit a human review.  The AnalysisRun must have a Prediction (status
`completed` or `needs_review`).

**Request body:**

```json
{
  "reviewer_name": "Dra. Lopez",
  "review_decision": "corrected",
  "corrected_label": "probable_fungal_growth",
  "comments": "High edge density pattern consistent with filamentous morphology (preliminary).",
  "is_final": true
}
```

Fields:
- `reviewer_name` (required) — identifier for the expert
- `review_decision` (required) — one of the four decisions above
- `corrected_label` (required when `review_decision = corrected`) — must be one of the five preliminary visual categories
- `comments` (optional) — free-text technical observation
- `is_final` (default `true`) — marks this review as the current standing decision

**Response:** `HTTP 201`

```json
{
  "id": "...",
  "analysis_run_id": "...",
  "reviewer_name": "Dra. Lopez",
  "review_decision": "corrected",
  "corrected_label": "probable_fungal_growth",
  "comments": "...",
  "is_final": true,
  "created_at": "2026-07-04T12:00:00Z"
}
```

**Example (curl):**

```bash
curl -X POST "http://localhost:8000/api/v1/analysis-runs/{run_id}/reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_name": "Dra. Lopez",
    "review_decision": "confirmed",
    "comments": "Automatic classification matches observed colony morphology."
  }'
```

---

### GET `/api/v1/analysis-runs/{analysis_run_id}/reviews`

List all human reviews for an AnalysisRun (chronological order, oldest first).

**Response:**

```json
{
  "reviews": [
    {
      "id": "...",
      "analysis_run_id": "...",
      "reviewer_name": "Dra. Lopez",
      "review_decision": "confirmed",
      "corrected_label": null,
      "comments": null,
      "is_final": true,
      "created_at": "..."
    }
  ]
}
```

Returns an empty list `{"reviews": []}` when no review has been submitted.

---

### GET `/api/v1/analysis-runs/{analysis_run_id}/reviews/final`

Returns the current standing (final) human review.  `HTTP 404` if none exists.

---

### GET `/api/v1/analysis-runs/{analysis_run_id}/preliminary-result`

Returns the Prediction enriched with current human review status (Fase 42).

New fields (all optional, `null` when no review yet):
- `human_review_status` — one of the five statuses below
- `human_review_completed` — `true` once any final review is submitted
- `latest_human_review_id` — UUID of the current final review
- `latest_human_review_decision` — decision code
- `final_label` — resolved final label (or `null`)
- `reviewed_at` — timestamp of the review

---

### GET `/api/v1/analysis-runs/{analysis_run_id}/final-result`

Full combined view.

**Example response (after confirmed review):**

```json
{
  "analysis_run_id": "...",
  "sample_id": "...",
  "prediction_id": "...",
  "preliminary_label": "suspicious_growth",
  "confidence_score": 0.48,
  "explanation": "Candidate growth regions detected ...",
  "feature_summary": { "petri": {...}, "micro": {...} },
  "quality_summary": { "petri_is_sharp": true, "micro_is_sharp": false, ... },
  "decision_trace": [ ... ],
  "automatic_warnings": null,
  "human_review_id": "...",
  "human_review_decision": "confirmed",
  "corrected_label": null,
  "reviewer_name": "Dra. Lopez",
  "human_comments": "...",
  "reviewed_at": "2026-07-04T14:30:00Z",
  "final_label": "suspicious_growth",
  "status": "human_confirmed",
  "human_review_completed": true,
  "requires_human_review": false,
  "disclaimer": "PRELIMINARY RESULT — expert review required. ..."
}
```

**Workflow status values:**

| Status | Meaning |
|---|---|
| `pending_human_review` | No review submitted yet |
| `human_confirmed` | Expert confirmed the automatic label |
| `human_corrected` | Expert replaced with a different label |
| `inconclusive` | Expert marked as inconclusive |
| `rejected_invalid_sample` | Sample excluded — not suitable for analysis |

---

## Key invariants

1. **Prediction is never modified.** `preliminary_label` always reflects the
   automatic engine output, even after a human review.
2. **HumanReview is the source of truth for `final_label`.**
3. **No HumanReview is created automatically** during upload.
4. **No automatic dataset export.** A `confirmed`/`corrected` review may be
   used in future dataset curation phases, but only via explicit action.
5. **At most one final review per AnalysisRun** at any given time.  Submitting
   a second `is_final=true` review demotes the previous one to historical.
6. **`rejected_invalid_sample` is never ground truth** for training.
7. **No taxonomy.** The system never asserts species, genus, or diagnosis.

---

## Error codes

| HTTP | Code | Trigger |
|---|---|---|
| 404 | `analysis_run_not_found` | AnalysisRun does not exist |
| 404 | `prediction_not_found` | AnalysisRun has no Prediction yet |
| 404 | `human_review_not_found` | No final review exists |
| 409 | `analysis_run_not_reviewable` | AnalysisRun status is `pending` or `processing` |
| 422 | Pydantic validation | Missing `corrected_label` for `corrected` decision, etc. |
