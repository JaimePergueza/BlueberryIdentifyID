from tests.api.image_helpers import make_valid_jpeg_bytes, make_valid_png_bytes

_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")


def _create_reviewed_run(api_client, sample_code: str, *, lot_code: str | None = None, origin: str | None = None) -> dict:
    """Create a sample (optionally with lot_code/origin) through to a final
    human review, returning the ids/labels a release test needs."""
    sample_response = api_client.post(
        "/api/v1/samples",
        json={"sample_code": sample_code, "lot_code": lot_code, "origin": origin},
    )
    assert sample_response.status_code == 201
    sample_id = sample_response.json()["id"]

    model_version_response = api_client.post(
        "/api/v1/model-versions",
        json={"name": f"strategy-flow-{sample_code}", "version": "0.1.0", "model_type": "mock"},
    )
    assert model_version_response.status_code == 201
    model_version_id = model_version_response.json()["id"]

    petri_response = api_client.post(
        f"/api/v1/samples/{sample_id}/petri-images",
        files={"file": ("petri.jpg", make_valid_jpeg_bytes(), "image/jpeg")},
    )
    assert petri_response.status_code == 201
    petri_image_id = petri_response.json()["id"]

    micro_response = api_client.post(
        f"/api/v1/samples/{sample_id}/micro-images",
        files={"file": ("micro.png", make_valid_png_bytes(), "image/png")},
    )
    assert micro_response.status_code == 201
    micro_image_id = micro_response.json()["id"]

    run_response = api_client.post(
        "/api/v1/analysis-runs",
        json={
            "sample_id": sample_id,
            "petri_image_id": petri_image_id,
            "micro_image_id": micro_image_id,
            "model_version_id": model_version_id,
        },
    )
    assert run_response.status_code == 201
    analysis_run_id = run_response.json()["id"]

    process_response = api_client.post(f"/api/v1/analysis-runs/{analysis_run_id}/process")
    assert process_response.status_code == 200
    prediction_label = process_response.json()["prediction"]["predicted_label"]

    review_response = api_client.post(
        f"/api/v1/analysis-runs/{analysis_run_id}/reviews",
        json={"reviewer_name": "Dr. Ibarra", "review_decision": "confirmed"},
    )
    assert review_response.status_code == 201

    return {
        "sample_id": sample_id,
        "analysis_run_id": analysis_run_id,
        "prediction_label": prediction_label,
    }


def _create_snapshot(api_client, name: str) -> dict:
    response = api_client.post("/api/v1/datasets/snapshots", json={"name": name, "version": "0.1.0"})
    assert response.status_code == 201
    return response.json()


def test_create_release_default_strategy_is_by_sample(api_client):
    for i in range(3):
        _create_reviewed_run(api_client, f"S-STRAT-DEFAULT-{i}")
    snapshot = _create_snapshot(api_client, "snapshot-default-strategy")

    response = api_client.post(
        "/api/v1/datasets/releases",
        json={"dataset_snapshot_id": snapshot["id"], "name": "release-default", "version": "0.1.0"},
    )

    assert response.status_code == 201
    assert response.json()["split_strategy"] == "by_sample"


def test_create_release_with_by_lot_strategy(api_client):
    for i in range(3):
        for lot in range(2):
            _create_reviewed_run(api_client, f"S-STRAT-LOT-{lot}-{i}", lot_code=f"LOT-{lot}")
    snapshot = _create_snapshot(api_client, "snapshot-by-lot")

    response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot["id"],
            "name": "release-by-lot",
            "version": "0.1.0",
            "split_strategy": "by_lot",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["split_strategy"] == "by_lot"
    assert body["item_count"] == 6


def test_create_release_with_by_origin_lot_strategy(api_client):
    for i in range(3):
        for lot in range(2):
            _create_reviewed_run(
                api_client, f"S-STRAT-OL-{lot}-{i}", lot_code=f"LOT-{lot}", origin=f"ORIGIN-{lot}"
            )
    snapshot = _create_snapshot(api_client, "snapshot-by-origin-lot")

    response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot["id"],
            "name": "release-by-origin-lot",
            "version": "0.1.0",
            "split_strategy": "by_origin_lot",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["split_strategy"] == "by_origin_lot"
    assert body["item_count"] == 6


def test_create_release_with_by_lot_fails_when_lot_code_missing(api_client):
    _create_reviewed_run(api_client, "S-STRAT-NOLOT")
    snapshot = _create_snapshot(api_client, "snapshot-missing-lot")

    response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot["id"],
            "name": "release-missing-lot",
            "version": "0.1.0",
            "split_strategy": "by_lot",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "dataset_split_metadata_error"


def test_create_release_with_by_origin_lot_fails_when_origin_missing(api_client):
    _create_reviewed_run(api_client, "S-STRAT-NOORIGIN", lot_code="LOT-1")
    snapshot = _create_snapshot(api_client, "snapshot-missing-origin")

    response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot["id"],
            "name": "release-missing-origin",
            "version": "0.1.0",
            "split_strategy": "by_origin_lot",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "dataset_split_metadata_error"


def test_manifest_includes_split_strategy_lot_code_and_origin(api_client):
    run = _create_reviewed_run(api_client, "S-STRAT-MANIFEST", lot_code="LOT-9", origin="ORIGIN-9")
    snapshot = _create_snapshot(api_client, "snapshot-manifest")
    release_response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot["id"],
            "name": "release-manifest",
            "version": "0.1.0",
            "split_strategy": "by_origin_lot",
        },
    )
    assert release_response.status_code == 201
    release_id = release_response.json()["id"]

    manifest_response = api_client.get(f"/api/v1/datasets/releases/{release_id}/manifest")

    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["split_strategy"] == "by_origin_lot"
    item = manifest["items"][0]
    assert item["sample_id"] == run["sample_id"]
    assert item["lot_code"] == "LOT-9"
    assert item["origin"] == "ORIGIN-9"


def test_create_release_preserves_x_request_id(api_client):
    _create_reviewed_run(api_client, "S-STRAT-REQID", lot_code="LOT-1")
    snapshot = _create_snapshot(api_client, "snapshot-request-id")

    response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot["id"],
            "name": "release-request-id",
            "version": "0.1.0",
            "split_strategy": "by_lot",
        },
        headers={"X-Request-ID": "strategy-request-1"},
    )

    assert response.status_code == 201
    assert response.headers["X-Request-ID"] == "strategy-request-1"


def test_by_lot_flow_never_exposes_taxonomy(api_client):
    for i in range(2):
        for lot in range(2):
            _create_reviewed_run(api_client, f"S-STRAT-TAX-{lot}-{i}", lot_code=f"LOT-{lot}", origin=f"ORIGIN-{lot}")
    snapshot = _create_snapshot(api_client, "snapshot-taxonomy-check")

    release_response = api_client.post(
        "/api/v1/datasets/releases",
        json={
            "dataset_snapshot_id": snapshot["id"],
            "name": "release-taxonomy-check",
            "version": "0.1.0",
            "split_strategy": "by_origin_lot",
        },
    )
    release_id = release_response.json()["id"]
    items_response = api_client.get(f"/api/v1/datasets/releases/{release_id}/items")
    manifest_response = api_client.get(f"/api/v1/datasets/releases/{release_id}/manifest")

    haystack = str(release_response.json()) + str(items_response.json()) + str(manifest_response.json())
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack.lower()
