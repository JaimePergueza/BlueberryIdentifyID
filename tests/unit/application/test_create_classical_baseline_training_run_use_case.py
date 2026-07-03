from dataclasses import asdict
from uuid import uuid4

import pytest

from blueberry_microid.application.dto.training_run_dto import CreateClassicalBaselineTrainingRunRequest
from blueberry_microid.application.exceptions import BaselineTrainingNotAllowedError
from blueberry_microid.application.use_cases.training.create_classical_baseline_training_run import (
    CreateClassicalBaselineTrainingRunUseCase,
)
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.entities.image_feature_extraction_run import ImageFeatureExtractionRun
from blueberry_microid.domain.entities.image_feature_vector import ImageFeatureVector
from blueberry_microid.domain.entities.training_preflight_run import TrainingPreflightRun
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_feature_extraction_status import ImageFeatureExtractionStatus
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus
from blueberry_microid.ml.configs.tabular_feature_training_config import TabularFeatureTrainingConfig
from blueberry_microid.ml.configs.training_config import TrainingConfig
from blueberry_microid.ml.training.classical_tabular_baseline import ClassicalTabularBaselineTrainer
from blueberry_microid.ml.training.feature_matrix_builder import FeatureMatrixBuilder
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetReleaseRepository,
    InMemoryDatasetSplitItemRepository,
    InMemoryImageFeatureExtractionRunRepository,
    InMemoryImageFeatureVectorRepository,
    InMemoryPredictionRepository,
    InMemoryTrainingPreflightRunRepository,
    InMemoryTrainingPredictionRepository,
    InMemoryTrainingRunRepository,
)


def _training_config() -> TrainingConfig:
    return TrainingConfig(experiment_name="classical", output_dir="out", min_items_per_split=1, min_items_per_class=1)


def _build_context(labels: list[PredictedLabel] | None = None):
    snapshot_id = uuid4()
    release = DatasetRelease(
        dataset_snapshot_id=snapshot_id,
        name="classical-release",
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
    split_labels = labels or [
        PredictedLabel.NO_EVIDENT_GROWTH,
        PredictedLabel.SUSPICIOUS_GROWTH,
        PredictedLabel.NO_EVIDENT_GROWTH,
        PredictedLabel.SUSPICIOUS_GROWTH,
    ]
    splits = [DatasetSplit.TRAIN, DatasetSplit.TRAIN, DatasetSplit.VALIDATION, DatasetSplit.TEST]
    split_items = [
        DatasetSplitItem(
            dataset_release_id=release.id,
            dataset_item_id=uuid4(),
            sample_id=uuid4(),
            split=split,
            ground_truth_label=label,
        )
        for split, label in zip(splits, split_labels)
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
        label_counts={},
        split_counts={"train": 2, "validation": 1, "test": 1},
        split_label_counts={},
        leakage_checks={"sample_split_isolation": True},
    )
    extraction = ImageFeatureExtractionRun(
        dataset_release_id=release.id,
        image_audit_run_id=uuid4(),
        status=ImageFeatureExtractionStatus.COMPLETED,
        is_completed=True,
        config={},
        total_items=4,
        processed_items=4,
        failed_items=0,
        total_feature_vectors=8,
        petri_feature_count=4,
        micro_feature_count=4,
        summary={},
        started_at=preflight.created_at,
        completed_at=preflight.created_at,
    )
    vectors = []
    for index, split_item in enumerate(split_items):
        value = float(index if split_item.ground_truth_label == PredictedLabel.NO_EVIDENT_GROWTH else index + 10)
        for modality in (ImageModality.PETRI, ImageModality.MICRO):
            vectors.append(
                ImageFeatureVector(
                    feature_extraction_run_id=extraction.id,
                    dataset_release_id=release.id,
                    dataset_item_id=split_item.dataset_item_id,
                    dataset_split_item_id=split_item.id,
                    split=split_item.split,
                    modality=modality,
                    image_path=f"/tmp/{modality.value}-{index}.png",
                    features={"intensity": {"mean_intensity": value}},
                    preprocessing={},
                    extraction_version="v1",
                )
            )
    release_repo = InMemoryDatasetReleaseRepository()
    preflight_repo = InMemoryTrainingPreflightRunRepository()
    split_repo = InMemoryDatasetSplitItemRepository()
    extraction_repo = InMemoryImageFeatureExtractionRunRepository()
    vector_repo = InMemoryImageFeatureVectorRepository()
    run_repo = InMemoryTrainingRunRepository()
    prediction_repo = InMemoryTrainingPredictionRepository()
    release_repo.add(release)
    preflight_repo.add(preflight)
    split_repo.add_many(split_items)
    extraction_repo.add(extraction)
    vector_repo.add_many(vectors)
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        dataset_release_repository=release_repo,
        dataset_split_item_repository=split_repo,
        training_preflight_run_repository=preflight_repo,
        training_run_repository=run_repo,
        training_prediction_repository=prediction_repo,
        image_feature_extraction_run_repository=extraction_repo,
        image_feature_vector_repository=vector_repo,
    )
    use_case = CreateClassicalBaselineTrainingRunUseCase(
        release_repo,
        preflight_repo,
        extraction_repo,
        vector_repo,
        split_repo,
        FeatureMatrixBuilder(),
        ClassicalTabularBaselineTrainer(),
        uow,
    )
    return use_case, release, preflight, extraction, run_repo, prediction_repo


def _request(release, preflight, extraction) -> CreateClassicalBaselineTrainingRunRequest:
    return CreateClassicalBaselineTrainingRunRequest(
        dataset_release_id=release.id,
        preflight_run_id=preflight.id,
        image_feature_extraction_run_id=extraction.id,
        experiment_name="classical-unit",
        tabular_training_config=TabularFeatureTrainingConfig(feature_extraction_run_id=extraction.id),
        created_by="qa",
    )


def test_creates_completed_training_run_and_predictions():
    use_case, release, preflight, extraction, run_repo, prediction_repo = _build_context()

    dto = use_case.execute(_request(release, preflight, extraction))

    assert dto.status == TrainingRunStatus.COMPLETED
    assert dto.baseline_model_type.value == "logistic_regression_tabular"
    assert dto.baseline_state["feature_extraction_run_id"] == str(extraction.id)
    assert dto.baseline_state["feature_names"] == ["micro__intensity__mean_intensity", "petri__intensity__mean_intensity"]
    assert "accuracy_overall" in dto.metrics
    assert "precision" not in dto.metrics
    assert run_repo.get_by_id(dto.id) is not None
    assert len(prediction_repo.list_by_training_run_id(dto.id)) == 4


def test_rejects_failed_or_partial_extraction():
    use_case, release, preflight, extraction, _run_repo, _prediction_repo = _build_context()
    failed = ImageFeatureExtractionRun(
        dataset_release_id=release.id,
        image_audit_run_id=uuid4(),
        status=ImageFeatureExtractionStatus.PARTIAL,
        is_completed=True,
        config={},
        total_items=1,
        processed_items=1,
        failed_items=1,
        total_feature_vectors=1,
        petri_feature_count=1,
        micro_feature_count=0,
        summary={},
        started_at=extraction.started_at,
    )
    use_case._image_feature_extraction_run_repository.add(failed)

    with pytest.raises(BaselineTrainingNotAllowedError, match="must be completed"):
        use_case.execute(_request(release, preflight, failed))


def test_failed_preflight_blocks_classical_baseline():
    use_case, release, _preflight, extraction, _run_repo, _prediction_repo = _build_context()
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
        use_case.execute(_request(release, failed_preflight, extraction))


def test_one_train_class_is_persisted_as_failed_run_without_predictions():
    labels = [
        PredictedLabel.SUSPICIOUS_GROWTH,
        PredictedLabel.SUSPICIOUS_GROWTH,
        PredictedLabel.NO_EVIDENT_GROWTH,
        PredictedLabel.NO_EVIDENT_GROWTH,
    ]
    use_case, release, preflight, extraction, _run_repo, prediction_repo = _build_context(labels)

    dto = use_case.execute(_request(release, preflight, extraction))

    assert dto.status == TrainingRunStatus.FAILED
    assert "at least two classes" in dto.error_message
    assert prediction_repo.list_by_training_run_id(dto.id) == []
