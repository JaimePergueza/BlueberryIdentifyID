from __future__ import annotations

from dataclasses import asdict
from uuid import uuid4

import pytest

from blueberry_microid.application.dto.training_run_dto import CreateBaselineTrainingRunRequest
from blueberry_microid.application.exceptions import BaselineTrainingNotAllowedError
from blueberry_microid.application.use_cases.training.create_baseline_training_run import (
    CreateBaselineTrainingRunUseCase,
)
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.entities.training_preflight_run import TrainingPreflightRun
from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus
from blueberry_microid.ml.configs.training_config import TrainingConfig
from blueberry_microid.ml.training.majority_class_baseline import MajorityClassBaselineTrainer
from blueberry_microid.ml.validation.manifest_validator import ManifestValidator
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetItemRepository,
    InMemoryDatasetReleaseRepository,
    InMemoryDatasetSplitItemRepository,
    InMemoryPredictionRepository,
    InMemoryTrainingPreflightRunRepository,
    InMemoryTrainingPredictionRepository,
    InMemoryTrainingRunRepository,
)


class _StaticManifestExporter:
    def __init__(self, manifest: dict) -> None:
        self._manifest = manifest

    def export(self, _dataset_release_id):
        return self._manifest


def _training_config() -> TrainingConfig:
    return TrainingConfig(
        experiment_name="baseline-unit",
        output_dir="out",
        min_items_per_split=1,
        min_items_per_class=1,
    )


def _manifest(release: DatasetRelease, split_items: list[DatasetSplitItem], dataset_items: list[DatasetItem]) -> dict:
    items_by_id = {item.id: item for item in dataset_items}
    manifest_items = []
    for split_item in split_items:
        dataset_item = items_by_id[split_item.dataset_item_id]
        manifest_items.append(
            {
                "split": split_item.split.value,
                "analysis_run_id": str(dataset_item.analysis_run_id),
                "sample_id": str(dataset_item.sample_id),
                "sample_code": f"S-{str(dataset_item.sample_id)[:8]}",
                "lot_code": None,
                "origin": None,
                "petri_image_path": f"storage/petri/{dataset_item.petri_image_id}.jpg",
                "micro_image_path": f"storage/micro/{dataset_item.micro_image_id}.png",
                "ground_truth_label": split_item.ground_truth_label.value,
                "source_review_decision": dataset_item.source_review_decision.value,
                "prediction_label": PredictedLabel.NO_EVIDENT_GROWTH.value,
                "final_review_id": str(dataset_item.final_review_id),
            }
        )
    label_distribution: dict[str, int] = {}
    split_distribution: dict[str, dict[str, int]] = {}
    for item in manifest_items:
        label_distribution[item["ground_truth_label"]] = label_distribution.get(item["ground_truth_label"], 0) + 1
        split_distribution.setdefault(item["split"], {})
        split_distribution[item["split"]][item["ground_truth_label"]] = (
            split_distribution[item["split"]].get(item["ground_truth_label"], 0) + 1
        )
    return {
        "dataset_release_id": str(release.id),
        "dataset_snapshot_id": str(release.dataset_snapshot_id),
        "name": release.name,
        "version": release.version,
        "split_strategy": release.split_strategy.value,
        "random_seed": release.random_seed,
        "ratios": {"train": release.train_ratio, "validation": release.validation_ratio, "test": release.test_ratio},
        "counts": {
            "total": len(manifest_items),
            "train": sum(1 for item in manifest_items if item["split"] == "train"),
            "validation": sum(1 for item in manifest_items if item["split"] == "validation"),
            "test": sum(1 for item in manifest_items if item["split"] == "test"),
        },
        "label_distribution": label_distribution,
        "split_distribution": split_distribution,
        "items": manifest_items,
    }


def _build_context(manifest: dict | None = None):
    snapshot_id = uuid4()
    release = DatasetRelease(
        dataset_snapshot_id=snapshot_id,
        name="baseline-release",
        version="0.1.0",
        split_strategy=SplitStrategy.BY_SAMPLE,
        random_seed=13,
        train_ratio=0.5,
        validation_ratio=0.25,
        test_ratio=0.25,
        item_count=4,
        train_count=2,
        validation_count=1,
        test_count=1,
    )
    labels = [
        PredictedLabel.SUSPICIOUS_GROWTH,
        PredictedLabel.SUSPICIOUS_GROWTH,
        PredictedLabel.NO_EVIDENT_GROWTH,
        PredictedLabel.PROBABLE_FUNGAL_GROWTH,
    ]
    splits = [DatasetSplit.TRAIN, DatasetSplit.TRAIN, DatasetSplit.VALIDATION, DatasetSplit.TEST]
    dataset_items = [
        DatasetItem(
            dataset_snapshot_id=snapshot_id,
            analysis_run_id=uuid4(),
            sample_id=uuid4(),
            petri_image_id=uuid4(),
            micro_image_id=uuid4(),
            prediction_id=uuid4(),
            final_review_id=uuid4(),
            source_review_decision=ReviewDecision.CORRECTED,
            ground_truth_label=label,
        )
        for label in labels
    ]
    split_items = [
        DatasetSplitItem(
            dataset_release_id=release.id,
            dataset_item_id=dataset_item.id,
            sample_id=dataset_item.sample_id,
            split=split,
            ground_truth_label=dataset_item.ground_truth_label,
        )
        for dataset_item, split in zip(dataset_items, splits)
    ]
    preflight = TrainingPreflightRun(
        dataset_release_id=release.id,
        status=TrainingPreflightStatus.PASSED,
        is_valid=True,
        config=asdict(_training_config()),
        summary={},
        item_count=4,
        train_count=2,
        validation_count=1,
        test_count=1,
        label_counts={label.value: labels.count(label) for label in set(labels)},
        split_counts={"train": 2, "validation": 1, "test": 1},
        split_label_counts={},
        leakage_checks={"sample_split_isolation": True},
    )
    release_repo = InMemoryDatasetReleaseRepository()
    item_repo = InMemoryDatasetItemRepository()
    split_item_repo = InMemoryDatasetSplitItemRepository()
    preflight_repo = InMemoryTrainingPreflightRunRepository()
    training_run_repo = InMemoryTrainingRunRepository()
    training_prediction_repo = InMemoryTrainingPredictionRepository()
    release_repo.add(release)
    item_repo.add_many(dataset_items)
    split_item_repo.add_many(split_items)
    preflight_repo.add(preflight)
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        dataset_item_repository=item_repo,
        dataset_release_repository=release_repo,
        dataset_split_item_repository=split_item_repo,
        training_preflight_run_repository=preflight_repo,
        training_run_repository=training_run_repo,
        training_prediction_repository=training_prediction_repo,
    )
    use_case = CreateBaselineTrainingRunUseCase(
        release_repo,
        preflight_repo,
        split_item_repo,
        item_repo,
        _StaticManifestExporter(manifest or _manifest(release, split_items, dataset_items)),
        ManifestValidator(),
        MajorityClassBaselineTrainer(),
        uow,
    )
    return use_case, release, preflight, training_run_repo, training_prediction_repo, uow


def test_create_baseline_training_run_persists_completed_run_and_predictions():
    use_case, release, preflight, run_repo, prediction_repo, uow = _build_context()

    dto = use_case.execute(
        CreateBaselineTrainingRunRequest(
            dataset_release_id=release.id,
            preflight_run_id=preflight.id,
            experiment_name="majority-baseline-unit",
            training_config=_training_config(),
            baseline_model_type=BaselineModelType.MAJORITY_CLASS,
            created_by="qa",
        )
    )

    assert dto.status == TrainingRunStatus.COMPLETED
    assert dto.baseline_state["majority_label"] == "suspicious_growth"
    assert dto.summary["uses_image_pixels"] is False
    assert dto.metrics["accuracy_overall"] == 2 / 4
    assert "precision" not in dto.metrics
    assert "recall" not in dto.metrics
    assert "f1" not in dto.metrics
    assert uow.committed is True
    assert run_repo.get_by_id(dto.id) is not None
    predictions = prediction_repo.list_by_training_run_id(dto.id)
    assert len(predictions) == 4
    assert {prediction.predicted_label for prediction in predictions} == {PredictedLabel.SUSPICIOUS_GROWTH}


def test_manifest_validation_failure_is_persisted_as_failed_run_without_predictions():
    invalid_manifest = {
        "dataset_release_id": str(uuid4()),
        "dataset_snapshot_id": str(uuid4()),
        "name": "invalid",
        "version": "0.1.0",
        "split_strategy": "by_sample",
        "random_seed": 1,
        "ratios": {"train": 0.5, "validation": 0.25, "test": 0.25},
        "counts": {"total": 0, "train": 0, "validation": 0, "test": 0},
        "items": [],
    }
    use_case, release, preflight, run_repo, prediction_repo, _uow = _build_context(invalid_manifest)

    dto = use_case.execute(
        CreateBaselineTrainingRunRequest(
            dataset_release_id=release.id,
            preflight_run_id=preflight.id,
            experiment_name="invalid-baseline",
            training_config=_training_config(),
        )
    )

    assert dto.status == TrainingRunStatus.FAILED
    assert dto.error_message == "manifest validation failed before baseline execution"
    assert dto.summary["contains_deep_learning"] is False
    assert dto.summary["validation_errors"]
    assert run_repo.get_by_id(dto.id) is not None
    assert prediction_repo.list_by_training_run_id(dto.id) == []


def test_failed_preflight_blocks_baseline_training_run():
    use_case, release, preflight, _run_repo, _prediction_repo, _uow = _build_context()
    failed_preflight = TrainingPreflightRun(
        dataset_release_id=release.id,
        status=TrainingPreflightStatus.FAILED,
        is_valid=False,
        config=asdict(_training_config()),
        summary={},
        item_count=0,
        train_count=0,
        validation_count=0,
        test_count=0,
        label_counts={},
        split_counts={},
        split_label_counts={},
        leakage_checks={},
    )
    use_case._preflight_run_repository.add(failed_preflight)

    with pytest.raises(BaselineTrainingNotAllowedError, match="failed preflight"):
        use_case.execute(
            CreateBaselineTrainingRunRequest(
                dataset_release_id=release.id,
                preflight_run_id=failed_preflight.id,
                experiment_name="blocked",
                training_config=_training_config(),
            )
        )
