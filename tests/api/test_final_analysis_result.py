"""API tests for the final-result endpoint and the enriched preliminary-result (Fase 42).

Tests cover:
- GET /analysis-runs/{id}/final-result before and after human review
- All four review decisions reflected in final-result
- GET /analysis-runs/{id}/preliminary-result enriched with review status
- End-to-end: upload → preliminary-result → review → final-result
- No taxonomy, no internal paths, X-Request-ID preserved
"""

from tests.api.image_helpers import make_valid_jpeg_bytes


def _upload(api_client, **kwargs):
    petri = kwargs.get("petri", make_valid_jpeg_bytes())
    micro = kwargs.get("micro", make_valid_jpeg_bytes(color="green"))
    files = {
        "petri_image": ("petri.jpg", petri, "image/jpeg"),
        "micro_image": ("micro.jpg", micro, "image/jpeg"),
    }
    return api_client.post("/api/v1/analysis/two-image-upload", files=files)


def _submit_review(api_client, run_id, decision, corrected_label=None, comments=None):
    payload = {
        "reviewer_name": "Dra. Lopez",
        "review_decision": decision,
    }
    if corrected_label is not None:
        payload["corrected_label"] = corrected_label
    if comments is not None:
        payload["comments"] = comments
    return api_client.post(f"/api/v1/analysis-runs/{run_id}/reviews", json=payload)


_FORBIDDEN_TAXONOMY = ("aspergillus", "penicillium", "botrytis", "escherichia", "colletotrichum",
                       "salmonella", "species identified", "genus identified", "confirmed diagnosis",
                       "taxon", "taxonomic identification")
_VALID_LABELS = {
    "no_evident_growth", "suspicious_growth",
    "probable_fungal_growth", "probable_bacterial_growth", "inconclusive",
}


# ─────────────────────────────────────────────────────────────────────────────
# GET /final-result — before review
# ─────────────────────────────────────────────────────────────────────────────

def test_final_result_returns_200_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    response = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result")
    assert response.status_code == 200


def test_final_result_pending_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["status"] == "pending_human_review"


def test_final_result_final_label_none_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["final_label"] is None


def test_final_result_requires_human_review_true_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["requires_human_review"] is True
    assert result["human_review_completed"] is False


def test_final_result_has_preliminary_label_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["preliminary_label"] in _VALID_LABELS


def test_final_result_includes_feature_summary_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    fs = result.get("feature_summary")
    assert fs is not None
    assert "petri" in fs and "micro" in fs


def test_final_result_includes_quality_summary_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    qs = result.get("quality_summary")
    assert qs is not None
    assert "petri_is_sharp" in qs


def test_final_result_includes_decision_trace_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    trace = result.get("decision_trace")
    assert isinstance(trace, list) and len(trace) >= 3


def test_final_result_human_review_fields_none_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["human_review_id"] is None
    assert result["human_review_decision"] is None
    assert result["reviewer_name"] is None
    assert result["reviewed_at"] is None


def test_final_result_404_for_unknown_run(api_client):
    response = api_client.get(
        "/api/v1/analysis-runs/00000000-0000-0000-0000-000000000000/final-result"
    )
    assert response.status_code == 404


def test_final_result_404_when_no_prediction(api_client):
    # AnalysisRun created via the old path (no two-image-upload) without processing
    sample_id = api_client.post("/api/v1/samples", json={"sample_code": "S-FR-NOPRED"}).json()["id"]
    petri_id = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("p.jpg", make_valid_jpeg_bytes(), "image/jpeg")},
    ).json()["id"]
    micro_id = api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("m.jpg", make_valid_jpeg_bytes(color="blue"), "image/jpeg")},
    ).json()["id"]
    mv_id = api_client.post(
        "/api/v1/model-versions",
        json={"name": "MockFR", "version": "0.0.1", "model_type": "mock"},
    ).json()["id"]
    run_id = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id, "petri_image_id": petri_id,
            "micro_image_id": micro_id, "model_version_id": mv_id,
        },
    ).json()["id"]
    response = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "prediction_not_found"


# ─────────────────────────────────────────────────────────────────────────────
# GET /final-result — after review: confirmed
# ─────────────────────────────────────────────────────────────────────────────

def test_final_result_confirmed_status(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "confirmed")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["status"] == "human_confirmed"


def test_final_result_confirmed_final_label_equals_preliminary(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    preliminary = body["predicted_label"]
    _submit_review(api_client, run_id, "confirmed")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["final_label"] == preliminary


def test_final_result_confirmed_human_review_completed(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "confirmed")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["human_review_completed"] is True
    assert result["requires_human_review"] is False


def test_final_result_confirmed_prediction_unchanged(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    original_label = body["predicted_label"]
    _submit_review(api_client, run_id, "confirmed")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["preliminary_label"] == original_label


# ─────────────────────────────────────────────────────────────────────────────
# GET /final-result — after review: corrected
# ─────────────────────────────────────────────────────────────────────────────

def test_final_result_corrected_status(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "corrected", corrected_label="no_evident_growth")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["status"] == "human_corrected"


def test_final_result_corrected_final_label(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "corrected", corrected_label="probable_fungal_growth")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["final_label"] == "probable_fungal_growth"


def test_final_result_corrected_corrected_label_field(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "corrected", corrected_label="probable_bacterial_growth")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["corrected_label"] == "probable_bacterial_growth"


# ─────────────────────────────────────────────────────────────────────────────
# GET /final-result — after review: marked_inconclusive
# ─────────────────────────────────────────────────────────────────────────────

def test_final_result_inconclusive_status(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "marked_inconclusive",
                   corrected_label="inconclusive")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["status"] == "inconclusive"


def test_final_result_inconclusive_final_label(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "marked_inconclusive",
                   corrected_label="inconclusive")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["final_label"] == "inconclusive"


# ─────────────────────────────────────────────────────────────────────────────
# GET /final-result — after review: rejected_invalid_sample
# ─────────────────────────────────────────────────────────────────────────────

def test_final_result_rejected_status(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "rejected_invalid_sample",
                   comments="Sample preparation error.")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["status"] == "rejected_invalid_sample"


def test_final_result_rejected_final_label_is_none(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "rejected_invalid_sample",
                   comments="Contaminated plate.")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["final_label"] is None


# ─────────────────────────────────────────────────────────────────────────────
# GET /preliminary-result — enriched with review status (Fase 42)
# ─────────────────────────────────────────────────────────────────────────────

def test_preliminary_result_has_review_status_before_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result").json()
    assert result["human_review_status"] == "pending_human_review"
    assert result["human_review_completed"] is False
    assert result["final_label"] is None


def test_preliminary_result_has_review_status_after_confirmed(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "confirmed")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result").json()
    assert result["human_review_status"] == "human_confirmed"
    assert result["human_review_completed"] is True
    assert result["final_label"] == body["predicted_label"]


def test_preliminary_result_requires_human_review_false_after_confirmed(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "confirmed")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result").json()
    assert result["requires_human_review"] is False


def test_preliminary_result_latest_review_id_set_after_review(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "confirmed")
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result").json()
    assert result["latest_human_review_id"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# Safety: no taxonomy, no internal paths, X-Request-ID
# ─────────────────────────────────────────────────────────────────────────────

def test_final_result_contains_no_taxonomy(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    _submit_review(api_client, run_id, "confirmed")
    result_str = str(api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()).lower()
    for word in _FORBIDDEN_TAXONOMY:
        assert word not in result_str, f"Taxonomy word '{word}' found in final-result response"


def test_final_result_no_internal_paths(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    result_str = str(result)
    assert "storage" not in result_str.lower() or "upload_storage" not in result_str.lower()
    for key in result:
        if isinstance(result[key], str):
            assert "\\" not in result[key], f"Backslash path found in field '{key}'"


def test_final_result_preserves_x_request_id(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    response = api_client.get(
        f"/api/v1/analysis-runs/{run_id}/final-result",
        headers={"X-Request-ID": "final-req-007"},
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "final-req-007"


def test_final_result_disclaimer_present(api_client):
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]
    result = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert result["disclaimer"]
    assert len(result["disclaimer"]) > 50


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end traceability: upload → preliminary-result → review → final-result
# ─────────────────────────────────────────────────────────────────────────────

def test_end_to_end_upload_review_final_result(api_client):
    """Full traceability: upload → preliminary-result → human review → final-result."""
    # Step 1: upload
    upload_body = _upload(api_client).json()
    run_id = upload_body["analysis_run_id"]
    sample_id = upload_body["sample_id"]
    prediction_id = upload_body["prediction_id"]
    preliminary_label = upload_body["predicted_label"]

    # Step 2: preliminary-result
    prelim = api_client.get(f"/api/v1/analysis-runs/{run_id}/preliminary-result").json()
    assert prelim["human_review_status"] == "pending_human_review"
    assert prelim["human_review_completed"] is False

    # Step 3: submit review
    review_body = _submit_review(
        api_client, run_id, "corrected",
        corrected_label="probable_bacterial_growth",
        comments="Growth pattern consistent with bacterial morphology (preliminary assessment).",
    ).json()
    review_id = review_body["id"]

    # Step 4: final-result
    final = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert final["analysis_run_id"] == run_id
    assert final["sample_id"] == sample_id
    assert final["prediction_id"] == prediction_id
    assert final["preliminary_label"] == preliminary_label  # unchanged
    assert final["final_label"] == "probable_bacterial_growth"
    assert final["status"] == "human_corrected"
    assert final["human_review_id"] == review_id
    assert final["human_review_decision"] == "corrected"
    assert final["corrected_label"] == "probable_bacterial_growth"
    assert final["human_review_completed"] is True
    assert final["requires_human_review"] is False
    assert "preliminary assessment" in final["human_comments"]
    # Prediction not modified
    assert final["preliminary_label"] == preliminary_label


def test_end_to_end_rejected_sample_excluded_from_ground_truth(api_client):
    """rejected_invalid_sample: final_label=None, human_review_completed=True."""
    body = _upload(api_client).json()
    run_id = body["analysis_run_id"]

    _submit_review(
        api_client, run_id, "rejected_invalid_sample",
        comments="Plate contaminated — not suitable for analysis.",
    )

    final = api_client.get(f"/api/v1/analysis-runs/{run_id}/final-result").json()
    assert final["final_label"] is None
    assert final["status"] == "rejected_invalid_sample"
    assert final["human_review_completed"] is True
    # Prediction still visible for traceability
    assert final["preliminary_label"] in _VALID_LABELS
