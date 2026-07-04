import json
from uuid import uuid4

import pytest

from blueberry_microid.application.services.annotation_bundle_validator import AnnotationBundleValidator
from blueberry_microid.application.services.annotation_bundle_writer import AnnotationBundleWriter
from blueberry_microid.domain.entities.petri_annotation_export_item import PetriAnnotationExportItem
from blueberry_microid.domain.entities.petri_annotation_export_run import PetriAnnotationExportRun
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.petri_annotation_bbox_source import PetriAnnotationBboxSource
from blueberry_microid.domain.enums.petri_annotation_export_format import PetriAnnotationExportFormat
from blueberry_microid.domain.enums.petri_annotation_export_status import PetriAnnotationExportStatus
from blueberry_microid.ml.configs.annotation_bundle_config import AnnotationBundleConfig


def _item(*, image_path="/data/petri-a.png", split=DatasetSplit.TRAIN):
    return PetriAnnotationExportItem(
        export_run_id=uuid4(),
        petri_region_review_id=uuid4(),
        petri_segmentation_region_id=uuid4(),
        dataset_release_id=uuid4(),
        dataset_item_id=uuid4(),
        dataset_split_item_id=uuid4(),
        split=split,
        petri_image_path=image_path,
        export_label="candidate_region",
        bbox_x=10,
        bbox_y=12,
        bbox_width=20,
        bbox_height=22,
        bbox_source=PetriAnnotationBboxSource.ORIGINAL,
        export_payload={"decision": "candidate_valid"},
    )


def _export_run(items=None, *, manifest=None, export_format=PetriAnnotationExportFormat.BLUEBERRY_MANIFEST):
    items = items or [_item()]
    if manifest is None:
        manifest = {
            "format": "blueberry_manifest",
            "category": {"id": 1, "name": "candidate_region"},
            "images": [
                {"image_id": items[0].petri_image_path, "petri_image_path": items[0].petri_image_path, "width": 100, "height": 100}
            ],
            "annotations": [
                {
                    "annotation_id": str(items[0].id),
                    "image_id": items[0].petri_image_path,
                    "bbox": [10, 12, 20, 22],
                    "label": "candidate_region",
                }
            ],
        }
    return PetriAnnotationExportRun(
        dataset_release_id=items[0].dataset_release_id,
        petri_segmentation_run_id=uuid4(),
        export_format=export_format,
        status=PetriAnnotationExportStatus.COMPLETED,
        is_completed=True,
        config={},
        exported_annotation_count=len(items),
        skipped_review_count=0,
        image_count=len({item.petri_image_path for item in items}),
        category_count=1,
        output_manifest=manifest,
        summary={},
    )


def test_validator_accepts_reviewed_candidate_region_bundle():
    items = [_item()]
    report = AnnotationBundleValidator().validate(_export_run(items), items, AnnotationBundleConfig())

    assert report.is_valid
    assert report.annotation_count == 1
    assert report.image_count == 1
    assert report.split_counts == {"train": 1}
    assert report.format_checks["blueberry_manifest"] is True


def test_validator_rejects_taxonomy_terms_in_manifest():
    items = [_item()]
    manifest = {
        "format": "blueberry_manifest",
        "category": {"id": 1, "name": "bacteria_species"},
        "annotations": [{"bbox": [1, 2, 3, 4], "label": "bacteria_species"}],
    }

    report = AnnotationBundleValidator().validate(_export_run(items, manifest=manifest), items, AnnotationBundleConfig())

    assert not report.is_valid
    assert any("forbidden taxonomy-like term" in error for error in report.errors)


def test_writer_dry_run_plans_files_without_writing(tmp_path):
    items = [_item()]
    export_run = _export_run(items)
    output_dir = tmp_path / "bundle"
    config = AnnotationBundleConfig(output_dir=str(output_dir), dry_run=True)
    report = AnnotationBundleValidator().validate(export_run, items, config)

    result = AnnotationBundleWriter().write(
        bundle_run_id=uuid4(),
        export_run=export_run,
        items=items,
        config=config,
        validation_report=report,
    )

    assert not output_dir.exists()
    assert {file.relative_path for file in result.files} >= {
        "README.md",
        "annotations/blueberry_manifest.json",
        "annotations/coco_annotations.json",
        "annotations/yolo/train/petri-a.txt",
        "dataset.yaml",
        "manifest.json",
    }
    assert result.bundle_manifest["contains_training"] is False
    assert result.bundle_manifest["contains_taxonomy"] is False


def test_writer_real_bundle_is_deterministic_and_has_checksums(tmp_path):
    items = [_item()]
    export_run = _export_run(items)
    config = AnnotationBundleConfig(output_dir=str(tmp_path / "bundle"), dry_run=False)
    report = AnnotationBundleValidator().validate(export_run, items, config)

    result = AnnotationBundleWriter().write(
        bundle_run_id=uuid4(),
        export_run=export_run,
        items=items,
        config=config,
        validation_report=report,
    )

    paths = [file.relative_path for file in result.files]
    assert paths == sorted(paths)
    assert paths.count("manifest.json") == 1
    assert all(file.checksum_sha256 for file in result.files)
    manifest = json.loads((tmp_path / "bundle" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["copy_images"] is False
    assert "pytorch" not in json.dumps(manifest).lower()


def test_writer_derives_non_empty_yolo_labels_from_blueberry_manifest(tmp_path):
    items = [_item()]
    export_run = _export_run(items)
    config = AnnotationBundleConfig(output_dir=str(tmp_path / "bundle"), dry_run=False)
    report = AnnotationBundleValidator().validate(export_run, items, config)

    result = AnnotationBundleWriter().write(
        bundle_run_id=uuid4(),
        export_run=export_run,
        items=items,
        config=config,
        validation_report=report,
    )

    yolo_file = next(file for file in result.files if file.relative_path.startswith("annotations/yolo/"))
    label_text = (tmp_path / "bundle" / yolo_file.relative_path).read_text(encoding="utf-8").strip()
    assert label_text == "0 0.200000 0.230000 0.200000 0.220000"


def test_writer_rejects_copy_images_mode():
    with pytest.raises(ValueError, match="copy_images=true"):
        AnnotationBundleConfig(copy_images=True)
