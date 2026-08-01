"""Regression tests for structured metadata and automatic coherence resolution."""

from tests.api.image_helpers import make_valid_jpeg_bytes


def _files():
    return {
        "petri_image": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg"),
        "micro_image": ("micro.jpg", make_valid_jpeg_bytes(color="green"), "image/jpeg"),
    }


def test_upload_persists_structured_sample_and_lab_metadata(api_client):
    response = api_client.post(
        "/api/v1/analysis/two-image-upload",
        files=_files(),
        data={
            "sample_code": "BB-META-001",
            "lot_code": "LOTE-CARCHI-07",
            "origin": "Tulcán, Carchi",
            "collection_date": "2026-07-31",
            "notes": "Fruto con lesión superficial.",
            "culture_medium": "PDA",
            "incubation_temperature_c": "25",
            "incubation_time_hours": "168",
            "magnification": "400×",
            "microscope_type": "Óptico de campo claro",
            "staining_method": "Azul de lactofenol",
            "preparation_method": "Cinta adhesiva",
        },
    )
    assert response.status_code == 201

    run_id = response.json()["analysis_run_id"]
    detail = api_client.get(f"/api/v1/analysis-runs/{run_id}/detail")
    assert detail.status_code == 200
    body = detail.json()
    assert body["sample"]["lot_code"] == "LOTE-CARCHI-07"
    assert body["sample"]["origin"] == "Tulcán, Carchi"
    assert body["sample"]["collection_date"].startswith("2026-07-31")
    assert body["petri_image"]["culture_medium"] == "PDA"
    assert body["petri_image"]["incubation_temperature_c"] == 25.0
    assert body["petri_image"]["incubation_time_hours"] == 168.0
    assert body["micro_image"]["magnification"] == "400×"
    assert body["micro_image"]["microscope_type"] == "Óptico de campo claro"
    assert body["micro_image"]["staining_method"] == "Azul de lactofenol"


def test_upload_returns_separated_quality_dimensions(api_client):
    response = api_client.post(
        "/api/v1/analysis/two-image-upload",
        files=_files(),
        data={
            "lot_code": "L-01",
            "origin": "Carchi",
            "collection_date": "2026-07-31",
            "culture_medium": "PDA",
            "incubation_temperature_c": "25",
            "incubation_time_hours": "168",
            "magnification": "400×",
            "microscope_type": "Campo claro",
            "staining_method": "Azul de lactofenol",
        },
    )
    assert response.status_code == 201
    body = response.json()
    quality = body["quality_summary"]
    assert set(quality["quality_dimensions"]) == {
        "technical_capture",
        "segmentation",
        "morphological_sufficiency",
        "metadata_sufficiency",
    }
    assert quality["metadata_sufficiency"]["status"] == "sufficient"


def test_upload_without_metadata_reports_missing_fields(api_client):
    response = api_client.post("/api/v1/analysis/two-image-upload", files=_files())
    assert response.status_code == 201
    body = response.json()
    assessment = body["feature_summary"]["coherence_assessment"]
    assert assessment["metadata"]["status"] == "insufficient"
    assert "Medio de cultivo" in assessment["metadata"]["missing_fields"]
    assert "Aumento microscópico" in assessment["metadata"]["missing_fields"]


def test_taxonomic_differential_contains_multiple_blueberry_profiles(api_client):
    response = api_client.post("/api/v1/analysis/two-image-upload", files=_files())
    assert response.status_code == 201
    differential = response.json()["feature_summary"]["taxonomic_differential"]
    if differential["status"] == "available":
        ids = {candidate["id"] for candidate in differential["candidates"]}
        assert {
            "penicillium_like",
            "aspergillus_like",
            "botrytis_like",
            "colletotrichum_like",
            "alternaria_like",
            "fusarium_like",
            "mucorales_like",
        }.issubset(ids)
        assert all(candidate["compatibility_index"] < 0.50 for candidate in differential["candidates"])
