"""Contract tests for operational morphology interpretation layers."""

from tests.api.image_helpers import make_valid_jpeg_bytes


def _upload(api_client) -> dict:
    response = api_client.post(
        "/api/v1/analysis/two-image-upload",
        files={
            "petri_image": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg"),
            "micro_image": (
                "micro.jpg",
                make_valid_jpeg_bytes(color="green"),
                "image/jpeg",
            ),
        },
    )
    assert response.status_code == 201
    return response.json()


def test_specialist_detail_exposes_versioned_operational_interpretations(api_client) -> None:
    uploaded = _upload(api_client)

    response = api_client.get(f"/api/v1/analysis-runs/{uploaded['analysis_run_id']}/detail")

    assert response.status_code == 200
    feature_summary = response.json()["prediction"]["feature_summary"]
    differential = feature_summary["taxonomic_differential"]
    assert differential["engine"] == {
        "name": "MorphologicalDifferentialEngine",
        "version": "0.2.0",
    }
    assert differential["status"] in {"available", "insufficient", "unavailable"}
    coherence = feature_summary["coherence_assessment"]
    assert coherence["engine"] == {
        "name": "AnalysisCoherenceResolver",
        "version": "0.1.0",
    }
    assert coherence["status"] in {"coherent", "conflict"}


def test_authoritative_final_result_excludes_operational_interpretations(api_client) -> None:
    uploaded = _upload(api_client)

    response = api_client.get(f"/api/v1/analysis-runs/{uploaded['analysis_run_id']}/final-result")

    assert response.status_code == 200
    result = response.json()
    assert "taxonomic_differential" not in result["feature_summary"]
    assert "coherence_assessment" not in result["feature_summary"]
    assert all(
        step.get("step") not in {"taxonomic_differential", "coherence_resolution"}
        for step in result["decision_trace"]
    )
