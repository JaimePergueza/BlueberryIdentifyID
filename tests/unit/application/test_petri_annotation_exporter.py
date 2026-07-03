from datetime import datetime, timezone
from uuid import uuid4

import pytest
from PIL import Image

from blueberry_microid.application.services.petri_annotation_exporter import PetriAnnotationExporter
from blueberry_microid.domain.entities.petri_region_review import PetriRegionReview
from blueberry_microid.domain.entities.petri_segmentation_region import PetriSegmentationRegion
from blueberry_microid.domain.entities.petri_segmentation_run import PetriSegmentationRun
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_annotation_export_decision_filter import (
    PetriAnnotationExportDecisionFilter,
)
from blueberry_microid.domain.enums.petri_annotation_export_format import PetriAnnotationExportFormat
from blueberry_microid.domain.enums.petri_region_review_decision import PetriRegionReviewDecision
from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus
from blueberry_microid.ml.configs.petri_annotation_export_config import PetriAnnotationExportConfig


def _run(release_id):
    return PetriSegmentationRun(
        id=uuid4(),
        dataset_release_id=release_id,
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


def _region(run, image_path, *, index=0):
    return PetriSegmentationRegion(
        id=uuid4(),
        segmentation_run_id=run.id,
        dataset_release_id=run.dataset_release_id,
        dataset_item_id=uuid4(),
        dataset_split_item_id=uuid4(),
        split=DatasetSplit.TRAIN,
        petri_image_path=str(image_path),
        region_index=index,
        area_px=100.0,
        centroid_x=15.0,
        centroid_y=15.0,
        bbox_x=10,
        bbox_y=20,
        bbox_width=30,
        bbox_height=40,
    )


def _review(region, *, decision=PetriRegionReviewDecision.CANDIDATE_VALID, final=True, corrected=False):
    kwargs = {}
    if corrected:
        kwargs = {
            "corrected_bbox_x": 11,
            "corrected_bbox_y": 21,
            "corrected_bbox_width": 31,
            "corrected_bbox_height": 41,
        }
    return PetriRegionReview(
        id=uuid4(),
        petri_segmentation_region_id=region.id,
        petri_segmentation_run_id=region.segmentation_run_id,
        dataset_release_id=region.dataset_release_id,
        dataset_item_id=region.dataset_item_id,
        dataset_split_item_id=region.dataset_split_item_id,
        decision=decision,
        is_final=final,
        **kwargs,
    )


def _image(tmp_path, name="petri.png"):
    path = tmp_path / name
    Image.new("RGB", (100, 200), "white").save(path)
    return path


def test_exports_only_candidate_valid_by_default_and_uses_corrected_bbox(tmp_path):
    release_id = uuid4()
    run = _run(release_id)
    image_path = _image(tmp_path)
    region_valid = _region(run, image_path, index=0)
    region_false = _region(run, image_path, index=1)
    reviews = [
        _review(region_valid, corrected=True),
        _review(region_false, decision=PetriRegionReviewDecision.CANDIDATE_FALSE_POSITIVE),
    ]

    result = PetriAnnotationExporter().export(
        segmentation_run=run,
        regions=[region_valid, region_false],
        reviews=reviews,
        config=PetriAnnotationExportConfig(),
        export_run_id=uuid4(),
    )

    assert len(result.items) == 1
    assert result.items[0].bbox_x == 11
    assert result.items[0].bbox_source.value == "corrected"
    assert result.summary["skipped_review_count"] == 1
    assert result.output_manifest["category"]["name"] == "candidate_region"


def test_uses_original_bbox_when_no_corrected_bbox(tmp_path):
    run = _run(uuid4())
    region = _region(run, _image(tmp_path))
    result = PetriAnnotationExporter().export(
        segmentation_run=run,
        regions=[region],
        reviews=[_review(region)],
        config=PetriAnnotationExportConfig(),
        export_run_id=uuid4(),
    )

    assert result.items[0].bbox_x == 10
    assert result.items[0].bbox_source.value == "original"


def test_valid_and_uncertain_filter_includes_uncertain(tmp_path):
    run = _run(uuid4())
    region = _region(run, _image(tmp_path))
    result = PetriAnnotationExporter().export(
        segmentation_run=run,
        regions=[region],
        reviews=[_review(region, decision=PetriRegionReviewDecision.CANDIDATE_UNCERTAIN)],
        config=PetriAnnotationExportConfig(
            decision_filter=PetriAnnotationExportDecisionFilter.VALID_AND_UNCERTAIN
        ),
        export_run_id=uuid4(),
    )

    assert len(result.items) == 1


def test_coco_json_has_basic_annotation_shape(tmp_path):
    run = _run(uuid4())
    region = _region(run, _image(tmp_path))
    result = PetriAnnotationExporter().export(
        segmentation_run=run,
        regions=[region],
        reviews=[_review(region)],
        config=PetriAnnotationExportConfig(export_format=PetriAnnotationExportFormat.COCO_JSON),
        export_run_id=uuid4(),
    )

    annotation = result.output_manifest["annotations"][0]
    assert annotation["bbox"] == [10, 20, 30, 40]
    assert annotation["area"] == 1200
    assert "segmentation" not in annotation
    assert result.output_manifest["categories"] == [{"id": 1, "name": "candidate_region"}]


def test_yolo_manifest_has_normalized_label_line(tmp_path):
    run = _run(uuid4())
    region = _region(run, _image(tmp_path))
    result = PetriAnnotationExporter().export(
        segmentation_run=run,
        regions=[region],
        reviews=[_review(region)],
        config=PetriAnnotationExportConfig(export_format=PetriAnnotationExportFormat.YOLO_TXT),
        export_run_id=uuid4(),
    )

    assert result.errors == []
    assert result.output_manifest["labels"][0]["lines"] == ["0 0.250000 0.200000 0.300000 0.200000"]


def test_yolo_fails_without_image_dimensions_when_required(tmp_path):
    run = _run(uuid4())
    region = _region(run, tmp_path / "missing.png")
    result = PetriAnnotationExporter().export(
        segmentation_run=run,
        regions=[region],
        reviews=[_review(region)],
        config=PetriAnnotationExportConfig(export_format=PetriAnnotationExportFormat.YOLO_TXT),
        export_run_id=uuid4(),
    )

    assert result.items == []
    assert result.errors


def test_handles_zero_exportable_annotations_and_has_no_taxonomy_or_masks(tmp_path):
    run = _run(uuid4())
    region = _region(run, _image(tmp_path))
    result = PetriAnnotationExporter().export(
        segmentation_run=run,
        regions=[region],
        reviews=[_review(region, decision=PetriRegionReviewDecision.NEEDS_RESEGMENTATION)],
        config=PetriAnnotationExportConfig(),
        export_run_id=uuid4(),
    )

    payload = str(result.output_manifest).lower() + str(result.summary).lower()
    assert result.items == []
    assert "species" not in payload
    assert "genus" not in payload
    assert "segmentation" not in result.output_manifest.get("annotations", [{}])[0] if result.output_manifest.get("annotations") else True
    assert result.summary["contains_taxonomy"] is False
    assert result.summary["contains_masks"] is False


def test_rejects_taxonomic_category_name():
    with pytest.raises(ValueError):
        PetriAnnotationExportConfig(category_name="bacteria")
