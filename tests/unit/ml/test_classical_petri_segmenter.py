from __future__ import annotations

import hashlib
import os
from dataclasses import asdict
from uuid import uuid4

from PIL import Image, ImageDraw

from blueberry_microid.domain.enums.petri_segmentation_status import PetriSegmentationStatus
from blueberry_microid.ml.configs.petri_segmentation_config import PetriSegmentationConfig
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest
from blueberry_microid.ml.preprocessing.classical_petri_segmenter import ClassicalPetriSegmenter

_FORBIDDEN_TAXONOMY_WORDS = ("aspergillus", "penicillium", "botrytis", "escherichia", "salmonella")


def _write_petri(path, *, circles=None, size=(120, 120), corrupt=False):
    if corrupt:
        path.write_bytes(b"not an image")
        return
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    for circle in circles or []:
        draw.ellipse(circle, fill="black")
    image.save(path, format="PNG")


def _manifest(path, *, micro_path="missing-micro.png", items=None) -> TrainingManifest:
    release_id = str(uuid4())
    items = items or [
        {
            "split": "test",
            "analysis_run_id": str(uuid4()),
            "sample_id": str(uuid4()),
            "sample_code": "S-PETRI",
            "dataset_item_id": str(uuid4()),
            "dataset_split_item_id": str(uuid4()),
            "petri_image_path": str(path),
            "micro_image_path": micro_path,
            "ground_truth_label": "suspicious_growth",
            "source_review_decision": "confirmed",
            "prediction_label": "suspicious_growth",
            "final_review_id": str(uuid4()),
        }
    ]
    return TrainingManifest.from_dict(
        {
            "dataset_release_id": release_id,
            "dataset_snapshot_id": str(uuid4()),
            "name": "release",
            "version": "0.1.0",
            "split_strategy": "by_sample",
            "random_seed": 7,
            "counts": {"total": len(items), "train": 0, "validation": 0, "test": len(items)},
            "ratios": {"train": 0.0, "validation": 0.0, "test": 1.0},
            "items": items,
        }
    )


def test_simple_dark_circle_detects_one_candidate_region(tmp_path):
    path = tmp_path / "petri.png"
    _write_petri(path, circles=[(40, 40, 80, 80)])

    report = ClassicalPetriSegmenter().segment(_manifest(path), PetriSegmentationConfig())

    assert report.status == PetriSegmentationStatus.COMPLETED
    assert report.total_regions_detected == 1
    assert report.regions[0].area_px > 1000
    assert report.summary["processed_only_modality"] == "petri"


def test_image_without_detectable_regions_returns_completed_zero_regions(tmp_path):
    path = tmp_path / "blank.png"
    _write_petri(path)

    report = ClassicalPetriSegmenter().segment(_manifest(path), PetriSegmentationConfig())

    assert report.status == PetriSegmentationStatus.COMPLETED
    assert report.total_regions_detected == 0


def test_missing_image_failed_when_all_petri_fail(tmp_path):
    report = ClassicalPetriSegmenter().segment(_manifest(tmp_path / "missing.png"), PetriSegmentationConfig())

    assert report.status == PetriSegmentationStatus.FAILED
    assert report.failed_petri_images == 1


def test_missing_one_of_two_images_is_partial(tmp_path):
    ok_path = tmp_path / "ok.png"
    _write_petri(ok_path, circles=[(40, 40, 80, 80)])
    missing_path = tmp_path / "missing.png"
    first = _manifest(ok_path).items[0]
    second = _manifest(missing_path).items[0]
    manifest = _manifest(ok_path, items=[asdict(first), asdict(second)])

    report = ClassicalPetriSegmenter().segment(manifest, PetriSegmentationConfig())

    assert report.status == PetriSegmentationStatus.PARTIAL
    assert report.processed_petri_images == 1
    assert report.failed_petri_images == 1


def test_corrupt_image_produces_error(tmp_path):
    path = tmp_path / "corrupt.png"
    _write_petri(path, corrupt=True)

    report = ClassicalPetriSegmenter().segment(_manifest(path), PetriSegmentationConfig())

    assert report.status == PetriSegmentationStatus.FAILED
    assert "could not be read" in report.errors[0].message


def test_area_filters_remove_small_and_large_regions(tmp_path):
    path = tmp_path / "circles.png"
    _write_petri(path, circles=[(10, 10, 16, 16), (40, 40, 90, 90)])

    small_filtered = ClassicalPetriSegmenter().segment(
        _manifest(path), PetriSegmentationConfig(min_region_area_px=100)
    )
    large_filtered = ClassicalPetriSegmenter().segment(
        _manifest(path), PetriSegmentationConfig(max_region_area_px=200)
    )

    assert small_filtered.total_regions_detected == 1
    assert large_filtered.total_regions_detected == 1
    assert large_filtered.regions[0].area_px < small_filtered.regions[0].area_px


def test_exclude_border_regions_filters_touching_border(tmp_path):
    path = tmp_path / "border.png"
    _write_petri(path, circles=[(0, 0, 30, 30), (60, 60, 90, 90)])

    report = ClassicalPetriSegmenter().segment(
        _manifest(path), PetriSegmentationConfig(exclude_border_regions=True)
    )

    assert report.total_regions_detected == 1
    assert report.regions[0].bbox_x > 0


def test_circularity_bbox_centroid_and_manual_threshold_are_stable(tmp_path):
    path = tmp_path / "manual.png"
    _write_petri(path, circles=[(40, 40, 80, 80)])

    report = ClassicalPetriSegmenter().segment(
        _manifest(path),
        PetriSegmentationConfig(threshold_method="manual", manual_threshold=127, morphological_opening=False),
    )
    region = report.regions[0]

    assert 0.75 <= region.circularity <= 1.2
    assert 35 <= region.bbox_x <= 45
    assert 35 <= region.bbox_y <= 45
    assert 55 <= region.centroid_x <= 65
    assert 55 <= region.centroid_y <= 65


def test_otsu_and_adaptive_threshold_methods_work(tmp_path):
    path = tmp_path / "thresholds.png"
    _write_petri(path, circles=[(35, 35, 85, 85)])

    otsu = ClassicalPetriSegmenter().segment(_manifest(path), PetriSegmentationConfig(threshold_method="otsu"))
    adaptive = ClassicalPetriSegmenter().segment(
        _manifest(path), PetriSegmentationConfig(threshold_method="adaptive")
    )

    assert otsu.total_regions_detected == 1
    assert adaptive.total_regions_detected >= 1


def test_result_is_deterministic_and_does_not_modify_file(tmp_path):
    path = tmp_path / "deterministic.png"
    _write_petri(path, circles=[(40, 40, 80, 80)])
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    segmenter = ClassicalPetriSegmenter()

    first = segmenter.segment(_manifest(path), PetriSegmentationConfig())
    second = segmenter.segment(_manifest(path), PetriSegmentationConfig())

    assert [
        (
            region.region_index,
            region.area_px,
            region.centroid_x,
            region.centroid_y,
            region.bbox_x,
            region.bbox_y,
            region.bbox_width,
            region.bbox_height,
        )
        for region in first.regions
    ] == [
        (
            region.region_index,
            region.area_px,
            region.centroid_x,
            region.centroid_y,
            region.bbox_x,
            region.bbox_y,
            region.bbox_width,
            region.bbox_height,
        )
        for region in second.regions
    ]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_does_not_process_micro_image_path(tmp_path):
    petri_path = tmp_path / "petri.png"
    _write_petri(petri_path, circles=[(40, 40, 80, 80)])
    micro_path = tmp_path / "does-not-exist-micro.png"

    report = ClassicalPetriSegmenter().segment(
        _manifest(petri_path, micro_path=str(micro_path)), PetriSegmentationConfig()
    )

    assert report.status == PetriSegmentationStatus.COMPLETED
    assert not os.path.exists(micro_path)


def test_no_pytorch_tensorflow_or_taxonomy_in_report(tmp_path):
    path = tmp_path / "safe.png"
    _write_petri(path, circles=[(40, 40, 80, 80)])

    report = ClassicalPetriSegmenter().segment(_manifest(path), PetriSegmentationConfig())

    haystack = str(report.summary).lower() + str([region.region_features for region in report.regions]).lower()
    assert "pytorch" not in haystack
    assert "tensorflow" not in haystack
    for word in _FORBIDDEN_TAXONOMY_WORDS:
        assert word not in haystack
    assert report.summary["contains_deep_learning"] is False
    assert report.summary["contains_taxonomy"] is False
