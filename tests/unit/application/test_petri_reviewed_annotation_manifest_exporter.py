from uuid import uuid4

import pytest

from blueberry_microid.application.exceptions import PetriSegmentationRunNotFoundError
from blueberry_microid.application.services.petri_reviewed_annotation_manifest_exporter import (
    PetriReviewedAnnotationManifestExporter,
)
from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.entities.petri_segmentation_run import PetriSegmentationRun
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_region_review_decision import PetriRegionReviewDecision
from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus
from tests.unit.application.fakes import (
    InMemoryPetriRegionReviewRepository,
    InMemoryPetriSegmentationRegionRepository,
    InMemoryPetriSegmentationRunRepository,
)
from datetime import datetime, timezone


def _build_run(run_repository, dataset_release_id):
    run = PetriSegmentationRun(
        dataset_release_id=dataset_release_id,
        status=PetriSegmentationStatus.COMPLETED,
        is_completed=True,
        config={},
        total_items=1,
        processed_petri_images=1,
        failed_petri_images=0,
        total_regions_detected=1,
        summary={},
        started_at=datetime.now(timezone.utc),
    )
    return run_repository.add(run)


def _build_region(region_repository, run_id, dataset_release_id, *, region_index=0, path="/data/petri/a.jpg"):
    region = PetriSegmentationRegion(
        segmentation_run_id=run_id,
        dataset_release_id=dataset_release_id,
        dataset_item_id=uuid4(),
        dataset_split_item_id=uuid4(),
        split=DatasetSplit.TRAIN,
        petri_image_path=path,
        region_index=region_index,
        area_px=100.0,
        centroid_x=5.0,
        centroid_y=5.0,
        bbox_x=1,
        bbox_y=1,
        bbox_width=10,
        bbox_height=10,
    )
    region_repository.add_many([region])
    return region


def _build_exporter():
    run_repo = InMemoryPetriSegmentationRunRepository()
    region_repo = InMemoryPetriSegmentationRegionRepository()
    review_repo = InMemoryPetriRegionReviewRepository()
    exporter = PetriReviewedAnnotationManifestExporter(run_repo, region_repo, review_repo)
    return exporter, run_repo, region_repo, review_repo


def _add_review(review_repo, region, *, decision=PetriRegionReviewDecision.CANDIDATE_VALID, is_final=True, **kwargs):
    review = PetriRegionReview(
        petri_segmentation_region_id=region.id,
        petri_segmentation_run_id=region.segmentation_run_id,
        dataset_release_id=region.dataset_release_id,
        dataset_item_id=region.dataset_item_id,
        dataset_split_item_id=region.dataset_split_item_id,
        decision=decision,
        is_final=is_final,
        **kwargs,
    )
    return review_repo.add(review)


def test_raises_when_segmentation_run_does_not_exist():
    exporter, *_ = _build_exporter()

    with pytest.raises(PetriSegmentationRunNotFoundError):
        exporter.export(uuid4())


def test_exports_only_final_reviews_by_default():
    exporter, run_repo, region_repo, review_repo = _build_exporter()
    dataset_release_id = uuid4()
    run = _build_run(run_repo, dataset_release_id)
    region = _build_region(region_repo, run.id, dataset_release_id)
    _add_review(review_repo, region, is_final=False)
    final_review = _add_review(review_repo, region, is_final=True)

    manifest = exporter.export(run.id)

    assert len(manifest["annotations"]) == 1
    assert manifest["annotations"][0]["is_final"] is True


def test_include_non_final_includes_historical_reviews():
    exporter, run_repo, region_repo, review_repo = _build_exporter()
    dataset_release_id = uuid4()
    run = _build_run(run_repo, dataset_release_id)
    region = _build_region(region_repo, run.id, dataset_release_id)
    _add_review(review_repo, region, is_final=False)
    _add_review(review_repo, region, is_final=True)

    manifest = exporter.export(run.id, include_non_final=True)

    assert len(manifest["annotations"]) == 2


def test_uses_corrected_bbox_as_effective_bbox_when_present():
    exporter, run_repo, region_repo, review_repo = _build_exporter()
    dataset_release_id = uuid4()
    run = _build_run(run_repo, dataset_release_id)
    region = _build_region(region_repo, run.id, dataset_release_id)
    _add_review(
        review_repo,
        region,
        corrected_bbox_x=5,
        corrected_bbox_y=6,
        corrected_bbox_width=30,
        corrected_bbox_height=32,
    )

    manifest = exporter.export(run.id)

    annotation = manifest["annotations"][0]
    assert annotation["corrected_bbox"] == {"x": 5, "y": 6, "width": 30, "height": 32}
    assert annotation["effective_bbox"] == {"x": 5, "y": 6, "width": 30, "height": 32}


def test_uses_original_bbox_as_effective_bbox_when_absent():
    exporter, run_repo, region_repo, review_repo = _build_exporter()
    dataset_release_id = uuid4()
    run = _build_run(run_repo, dataset_release_id)
    region = _build_region(region_repo, run.id, dataset_release_id)
    _add_review(review_repo, region)

    manifest = exporter.export(run.id)

    annotation = manifest["annotations"][0]
    assert annotation["corrected_bbox"] is None
    assert annotation["effective_bbox"] == {"x": 1, "y": 1, "width": 10, "height": 10}


def test_calculates_decision_distribution():
    exporter, run_repo, region_repo, review_repo = _build_exporter()
    dataset_release_id = uuid4()
    run = _build_run(run_repo, dataset_release_id)
    region_a = _build_region(region_repo, run.id, dataset_release_id, region_index=0, path="/data/petri/a.jpg")
    region_b = _build_region(region_repo, run.id, dataset_release_id, region_index=1, path="/data/petri/b.jpg")
    _add_review(review_repo, region_a, decision=PetriRegionReviewDecision.CANDIDATE_VALID)
    _add_review(review_repo, region_b, decision=PetriRegionReviewDecision.CANDIDATE_FALSE_POSITIVE)

    manifest = exporter.export(run.id)

    assert manifest["decision_distribution"] == {"candidate_valid": 1, "candidate_false_positive": 1}


def test_annotations_are_ordered_deterministically():
    exporter, run_repo, region_repo, review_repo = _build_exporter()
    dataset_release_id = uuid4()
    run = _build_run(run_repo, dataset_release_id)
    region_b = _build_region(region_repo, run.id, dataset_release_id, region_index=1, path="/data/petri/b.jpg")
    region_a = _build_region(region_repo, run.id, dataset_release_id, region_index=0, path="/data/petri/a.jpg")
    _add_review(review_repo, region_b)
    _add_review(review_repo, region_a)

    manifest = exporter.export(run.id)

    paths = [annotation["petri_image_path"] for annotation in manifest["annotations"]]
    assert paths == sorted(paths)


def test_manifest_never_includes_taxonomy_or_yolo_labels():
    exporter, run_repo, region_repo, review_repo = _build_exporter()
    dataset_release_id = uuid4()
    run = _build_run(run_repo, dataset_release_id)
    region = _build_region(region_repo, run.id, dataset_release_id)
    _add_review(review_repo, region)

    manifest = exporter.export(run.id)

    manifest_keys = set(manifest.keys())
    assert "species" not in manifest_keys
    assert "genus" not in manifest_keys
    assert "yolo_labels" not in manifest_keys
    annotation_keys = set(manifest["annotations"][0].keys())
    assert "species" not in annotation_keys
    assert "genus" not in annotation_keys
