# Analysis history and consolidated detail API

The official MVP workflow starts with `POST /api/v1/analysis/two-image-upload`.
That operation persists the `Sample`, both image records, `ModelVersion`,
`AnalysisRun`, and its immutable automatic `Prediction`. The endpoints below
are read-only views over that traceability data.

## List history

```http
GET /api/v1/analysis-runs
```

All filters are optional and can be combined.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `page` | integer | `1` | Page number, minimum `1`. |
| `page_size` | integer | `20` | Items per page, minimum `1`, maximum `100`. |
| `sample_code` | string | — | Case-insensitive partial sample-code search. |
| `status` | `AnalysisStatus` | — | Pipeline state. |
| `review_status` | `pending` / `reviewed` | — | Whether a final `HumanReview` exists. |
| `preliminary_label` | `PredictedLabel` | — | Original automatic visual category. |
| `final_label` | `PredictedLabel` | — | Label resolved from the current final review. |
| `created_from` | ISO 8601 datetime | — | Inclusive creation-date lower bound. |
| `created_to` | ISO 8601 datetime | — | Inclusive creation-date upper bound. |

Rows are always ordered by `created_at DESC, id DESC`, so pagination is stable.

```json
{
  "items": [
    {
      "analysis_run_id": "8f70d0bd-20e8-49f0-9bfd-c9ae3908ae0c",
      "sample_id": "ba517dfa-6683-4759-94ed-2974402f5551",
      "sample_code": "BB-42",
      "petri_image_id": "9ec9e5f0-6b85-42eb-89b6-7f4acf3faa2a",
      "micro_image_id": "c667bb08-8df2-4066-b76e-9d95f3d86a16",
      "model_version_id": "bf826975-573c-4ee3-92ec-cc6294f16e8c",
      "model_name": "PreliminaryTwoImageEngine",
      "model_version": "0.2.0",
      "model_type": "classical",
      "analysis_status": "needs_review",
      "created_at": "2026-07-30T16:00:00Z",
      "completed_at": "2026-07-30T16:00:01Z",
      "preliminary_label": "suspicious_growth",
      "confidence_score": 0.71,
      "requires_human_review": true,
      "review_status": "pending",
      "final_review_id": null,
      "review_decision": null,
      "reviewer_name": null,
      "reviewed_at": null,
      "final_label": null,
      "final_status": "pending_human_review"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "total_pages": 1
}
```

`pending` means no `HumanReview.is_final=true` row exists; historical,
non-final reviews do not change the summary.

## Consolidated detail

```http
GET /api/v1/analysis-runs/{analysis_run_id}/detail
```

The response has nested `analysis_run`, `sample`, `petri_image`,
`micro_image`, and `model_version` objects. It returns `prediction` and
`human_review` as `null` when either record is absent. Image objects expose
safe file metadata plus available culture/microscopy metadata only.

```json
{
  "analysis_run": {"id": "8f70d0bd-20e8-49f0-9bfd-c9ae3908ae0c", "status": "needs_review", "created_at": "2026-07-30T16:00:00Z", "started_at": "2026-07-30T16:00:00Z", "completed_at": "2026-07-30T16:00:01Z", "error_message": null},
  "sample": {"id": "ba517dfa-6683-4759-94ed-2974402f5551", "sample_code": "BB-42", "product": "blueberry", "lot_code": null, "origin": null, "collection_date": null, "notes": null, "created_at": "2026-07-30T16:00:00Z"},
  "petri_image": {"id": "9ec9e5f0-6b85-42eb-89b6-7f4acf3faa2a", "file_name": "petri.jpg", "mime_type": "image/jpeg", "file_size_bytes": 14203, "width": 1200, "height": 900, "captured_at": null, "culture_medium": null, "incubation_temperature_c": null, "incubation_time_hours": null, "seeding_date": null, "observed_colony_color": null, "observed_colony_shape": null, "observed_colony_margin": null, "observed_colony_texture": null, "notes": null},
  "micro_image": {"id": "c667bb08-8df2-4066-b76e-9d95f3d86a16", "file_name": "micro.png", "mime_type": "image/png", "file_size_bytes": 8341, "width": 1024, "height": 768, "captured_at": null, "magnification": null, "microscope_type": null, "staining_method": null, "preparation_method": null, "observed_structures": null, "notes": null},
  "model_version": {"id": "bf826975-573c-4ee3-92ec-cc6294f16e8c", "name": "PreliminaryTwoImageEngine", "version": "0.2.0", "model_type": "classical", "description": "Classical two-image heuristic engine."},
  "prediction": {"id": "5f6e1111-6d7f-4c54-a9c9-17cc40a86021", "predicted_label": "suspicious_growth", "confidence_score": 0.71, "class_probabilities": {"suspicious_growth": 0.71}, "technical_observation": "Preliminary, non-diagnostic visual result.", "requires_human_review": true, "explanation": "Transparent classical visual-rule output.", "feature_summary": {}, "quality_summary": {}, "decision_trace": [], "warnings": [], "created_at": "2026-07-30T16:00:01Z"},
  "human_review": null,
  "final_label": null,
  "final_status": "pending_human_review",
  "human_review_completed": false,
  "requires_human_review": true
}
```

An unknown run returns the controlled `analysis_run_not_found` error.

## Preliminary versus final result

`preliminary_label` is always the original `Prediction`. A final human review
resolves the final fields without changing it: `confirmed` uses the preliminary
label, `corrected` uses `corrected_label`, `marked_inconclusive` produces
`inconclusive`, and `rejected_invalid_sample` has no final label. Without a
final review, the result is `pending_human_review` with no final label.

## Internal-data safety

Neither endpoint serializes `file_path`, filesystem paths, `STORAGE_ROOT`,
secrets, credentials, ORM objects, or stack traces.
