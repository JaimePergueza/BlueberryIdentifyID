import json
from uuid import uuid4

from blueberry_microid.application.services.annotation_bundle_validator import AnnotationBundleValidationReport
from blueberry_microid.application.services.annotation_bundle_writer import AnnotationBundleWriter
from blueberry_microid.application.services.annotation_quality_gate_validator import AnnotationQualityGateValidator
from blueberry_microid.domain.entities.annotation_bundle_run import AnnotationBundleRun
from blueberry_microid.domain.enums.annotation_bundle_file_role import AnnotationBundleFileRole
from blueberry_microid.domain.enums.annotation_bundle_status import AnnotationBundleStatus
from blueberry_microid.ml.configs.annotation_bundle_config import AnnotationBundleConfig
from blueberry_microid.ml.configs.annotation_quality_gate_config import AnnotationQualityGateConfig
from tests.unit.application.test_annotation_bundle_services import _export_run, _item


def _completed_bundle(tmp_path, *, items=None):
    items = items or [_item()]
    export_run = _export_run(items)
    config = AnnotationBundleConfig(output_dir=str(tmp_path / "bundle"), dry_run=False)
    write = AnnotationBundleWriter().write(
        bundle_run_id=uuid4(),
        export_run=export_run,
        items=items,
        config=config,
        validation_report=AnnotationBundleValidationReport(is_valid=True),
    )
    bundle = AnnotationBundleRun(
        id=write.files[0].bundle_run_id,
        petri_annotation_export_run_id=export_run.id,
        dataset_release_id=export_run.dataset_release_id,
        petri_segmentation_run_id=export_run.petri_segmentation_run_id,
        status=AnnotationBundleStatus.COMPLETED,
        is_completed=True,
        config=config.to_dict(),
        output_dir=str(tmp_path / "bundle"),
        dry_run=False,
        file_count=len(write.files),
        annotation_count=len(items),
        image_count=len({item.petri_image_path for item in items}),
        label_count=len([file for file in write.files if file.file_role == AnnotationBundleFileRole.YOLO_LABEL]),
        validation_summary={},
        bundle_manifest=write.bundle_manifest,
    )
    return bundle, write.files


def _passing_config(**overrides):
    values = {
        "fail_on_empty_split": False,
        "warn_on_single_class": False,
        "min_bbox_width_px": 2,
        "min_bbox_height_px": 2,
    }
    values.update(overrides)
    return AnnotationQualityGateConfig(**values)


def test_completed_valid_bundle_passes(tmp_path):
    bundle, files = _completed_bundle(tmp_path)

    report = AnnotationQualityGateValidator().validate(bundle, files, _passing_config())

    assert report.is_passed
    assert report.status.value == "passed"
    assert report.total_images == 1
    assert report.total_annotations == 1
    assert report.split_distribution["train"]["annotations"] == 1
    assert report.bbox_statistics["count"] == 1
    assert report.category_distribution == {"candidate_region": 1}


def test_dry_run_bundle_fails_when_completed_required(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    bundle.status = AnnotationBundleStatus.DRY_RUN
    bundle.dry_run = True

    report = AnnotationQualityGateValidator().validate(bundle, files, _passing_config())

    assert report.status.value == "failed"
    assert any(issue.code == "bundle_not_completed" for issue in report.errors)


def test_failed_bundle_fails(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    bundle.status = AnnotationBundleStatus.FAILED
    bundle.is_completed = False

    report = AnnotationQualityGateValidator().validate(bundle, files, _passing_config(require_completed_bundle=False))

    assert report.status.value == "failed"
    assert any(issue.code == "bundle_not_completed" for issue in report.errors)


def test_missing_coco_yolo_and_blueberry_files_are_errors(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    files = [file for file in files if file.file_role == AnnotationBundleFileRole.BUNDLE_MANIFEST]

    report = AnnotationQualityGateValidator().validate(bundle, files, _passing_config())

    codes = {issue.code for issue in report.errors}
    assert {"coco_missing", "yolo_missing", "blueberry_manifest_missing", "dataset_yaml_missing"} <= codes


def test_invalid_split_and_taxonomic_category_are_errors(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    manifest_file = next(file for file in files if file.file_role == AnnotationBundleFileRole.BLUEBERRY_MANIFEST)
    manifest_path = tmp_path / "bundle" / manifest_file.relative_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["category"]["name"] = "bacteria_species"
    manifest["images"][0]["split"] = "holdout"
    manifest["annotations"][0]["split"] = "holdout"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = AnnotationQualityGateValidator().validate(bundle, files, _passing_config())

    codes = {issue.code for issue in report.errors}
    assert "taxonomic_category_detected" in codes
    assert "invalid_split" in codes


def test_bbox_invalid_too_small_and_duplicate_are_detected(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    manifest_file = next(file for file in files if file.file_role == AnnotationBundleFileRole.BLUEBERRY_MANIFEST)
    manifest_path = tmp_path / "bundle" / manifest_file.relative_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["annotations"][0]["bbox"] = [0, 0, 1, 1]
    duplicate = manifest["annotations"][0].copy()
    duplicate["annotation_id"] = "duplicate"
    manifest["annotations"].append(duplicate)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = AnnotationQualityGateValidator().validate(bundle, files, _passing_config())

    codes = {issue.code for issue in report.warnings}
    assert "bbox_too_small" in codes
    assert "duplicate_bbox" in codes


def test_image_without_annotations_and_single_class_warn(tmp_path):
    item_a = _item(image_path="/data/a.png")
    item_b = _item(image_path="/data/b.png")
    bundle, files = _completed_bundle(tmp_path, items=[item_a, item_b])
    manifest_file = next(file for file in files if file.file_role == AnnotationBundleFileRole.BLUEBERRY_MANIFEST)
    manifest_path = tmp_path / "bundle" / manifest_file.relative_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["images"] = [
        {"image_id": "/data/a.png", "petri_image_path": "/data/a.png", "split": "train"},
        {"image_id": "/data/b.png", "petri_image_path": "/data/b.png", "split": "train"},
    ]
    manifest["annotations"] = [
        {
            "annotation_id": "a-1",
            "image_id": "/data/a.png",
            "bbox": [10, 12, 20, 22],
            "split": "train",
            "label": "candidate_region",
        }
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = AnnotationQualityGateValidator().validate(bundle, files, _passing_config(warn_on_single_class=True))

    codes = {issue.code for issue in report.warnings}
    assert "image_without_annotations" in codes
    assert "single_class_only" in codes


def test_invalid_yolo_line_and_out_of_range_coordinates_error(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    yolo_file = next(file for file in files if file.file_role == AnnotationBundleFileRole.YOLO_LABEL)
    yolo_path = tmp_path / "bundle" / yolo_file.relative_path
    yolo_path.write_text("0 1.2 0.5 0.2 0.2\nnot enough\n", encoding="utf-8")

    report = AnnotationQualityGateValidator().validate(bundle, files, _passing_config())

    assert len([issue for issue in report.errors if issue.code in {"bbox_invalid", "manifest_inconsistent"}]) >= 2


def test_coco_annotation_with_missing_image_id_errors(tmp_path):
    bundle, files = _completed_bundle(tmp_path)
    coco_file = next(file for file in files if file.file_role == AnnotationBundleFileRole.COCO_ANNOTATIONS)
    coco_path = tmp_path / "bundle" / coco_file.relative_path
    coco = json.loads(coco_path.read_text(encoding="utf-8"))
    coco["annotations"][0]["image_id"] = "missing"
    coco_path.write_text(json.dumps(coco), encoding="utf-8")

    report = AnnotationQualityGateValidator().validate(bundle, files, _passing_config())

    assert any(issue.code == "manifest_inconsistent" for issue in report.errors)
