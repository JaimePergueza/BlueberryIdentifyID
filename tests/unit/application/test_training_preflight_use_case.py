from __future__ import annotations

import copy
from uuid import uuid4

import pytest

from blueberry_microid.application.dto.ml_preflight_dto import CreateTrainingPreflightRunRequest
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.application.use_cases.ml_preflight.create_training_preflight_run import (
    CreateTrainingPreflightRunUseCase,
)
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
from blueberry_microid.domain.enums.training_preflight_issue_severity import TrainingPreflightIssueSeverity
from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus
from blueberry_microid.ml.configs.training_config import TrainingConfig
from blueberry_microid.ml.validation.image_path_validator import ImagePathValidator
from blueberry_microid.ml.validation.manifest_validator import ManifestValidator
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetItemRepository,
    InMemoryDatasetReleaseRepository,
    InMemoryDatasetSplitItemRepository,
    InMemoryMicroImageRepository,
    InMemoryPetriImageRepository,
    InMemoryPredictionRepository,
    InMemorySampleRepository,
    InMemoryTrainingPreflightIssueRepository,
    InMemoryTrainingPreflightRunRepository,
)


class _StaticManifestExporter:
    def __init__(self, manifest: dict) -> None:
        self.manifest = manifest

    def export(self, _dataset_release_id):
        return copy.deepcopy(self.manifest)


class _FailingTrainingPreflightIssueRepository(InMemoryTrainingPreflightIssueRepository):
    def add_many(self, issues):
        super().add_many(issues)
        raise RuntimeError("simulated preflight issue persistence failure")


def _manifest(items=None, release_id=None) -> dict:
    release_id = release_id or uuid4()
    items = items or [
        _item(1, "train", "suspicious_growth"),
        _item(2, "validation", "no_evident_growth"),
        _item(3, "test", "probable_fungal_growth"),
    ]
    return {
        "dataset_release_id": str(release_id),
        "dataset_snapshot_id": str(uuid4()),
        "name": "release",
        "version": "0.1.0",
        "split_strategy": "by_sample",
        "random_seed": 42,
        "ratios": {"train": 0.7, "validation": 0.15, "test": 0.15},
        "counts": {"total": len(items), "train": 1, "validation": 1, "test": 1},
        "label_distribution": {},
        "split_distribution": {},
        "items": items,
    }


def _item(index: int, split: str, label: str, **overrides) -> dict:
    data = {
        "split": split,
        "analysis_run_id": str(uuid4()),
        "sample_id": str(uuid4()),
        "sample_code": f"S-{index}",
        "lot_code": f"L-{index}",
        "origin": "farm-a",
        "petri_image_path": f"petri-{index}.jpg",
        "micro_image_path": f"micro-{index}.png",
        "ground_truth_label": label,
        "source_review_decision": "confirmed",
        "prediction_label": label,
        "final_review_id": str(uuid4()),
    }
    data.update(overrides)
    return data


def _config(**overrides) -> TrainingConfig:
    data = {"experiment_name": "preflight", "output_dir": "out"}
    data.update(overrides)
    return TrainingConfig(**data)


def _use_case(manifest: dict, issue_repo=None, run_repo=None):
    run_repo = run_repo or InMemoryTrainingPreflightRunRepository()
    issue_repo = issue_repo or InMemoryTrainingPreflightIssueRepository()
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        training_preflight_run_repository=run_repo,
        training_preflight_issue_repository=issue_repo,
    )
    return (
        CreateTrainingPreflightRunUseCase(
            _StaticManifestExporter(manifest),
            ManifestValidator(),
            ImagePathValidator(),
            uow,
        ),
        run_repo,
        issue_repo,
        uow,
    )


def test_valid_manifest_creates_passed_preflight():
    release_id = uuid4()
    use_case, _, _, _ = _use_case(_manifest(release_id=release_id))

    dto = use_case.execute(CreateTrainingPreflightRunRequest(release_id, _config()))

    assert dto.status == TrainingPreflightStatus.PASSED
    assert dto.is_valid is True
    assert dto.issues == []


def test_manifest_with_warnings_creates_warning_status_and_warning_issue():
    release_id = uuid4()
    manifest = _manifest(
        [
            _item(1, "train", "suspicious_growth"),
            _item(2, "validation", "suspicious_growth"),
            _item(3, "test", "suspicious_growth"),
        ],
        release_id=release_id,
    )
    use_case, _, _, _ = _use_case(manifest)

    dto = use_case.execute(CreateTrainingPreflightRunRequest(release_id, _config()))

    assert dto.status == TrainingPreflightStatus.WARNING
    assert dto.is_valid is True
    assert len(dto.issues) == 1
    assert dto.issues[0].severity == TrainingPreflightIssueSeverity.WARNING


def test_invalid_manifest_creates_failed_status_and_error_issue():
    release_id = uuid4()
    manifest = _manifest([_item(1, "train", "suspicious_growth"), _item(2, "test", "no_evident_growth")], release_id)
    use_case, _, _, _ = _use_case(manifest)

    dto = use_case.execute(CreateTrainingPreflightRunRequest(release_id, _config()))

    assert dto.status == TrainingPreflightStatus.FAILED
    assert dto.is_valid is False
    assert any(issue.severity == TrainingPreflightIssueSeverity.ERROR for issue in dto.issues)


def test_config_and_counts_are_persisted_as_json_metadata():
    release_id = uuid4()
    use_case, run_repo, _, _ = _use_case(_manifest(release_id=release_id))

    dto = use_case.execute(
        CreateTrainingPreflightRunRequest(
            release_id,
            _config(batch_size=16, min_items_per_class=1),
            created_by="qa",
            notes="preflight only",
        )
    )
    persisted = run_repo.get_by_id(dto.id)

    assert persisted.config["experiment_name"] == "preflight"
    assert persisted.config["batch_size"] == 16
    assert persisted.item_count == 3
    assert persisted.train_count == 1
    assert persisted.validation_count == 1
    assert persisted.test_count == 1
    assert persisted.created_by == "qa"
    assert persisted.notes == "preflight only"


def test_validate_image_paths_false_does_not_check_filesystem():
    release_id = uuid4()
    manifest = _manifest(release_id=release_id)
    use_case, _, _, _ = _use_case(manifest)

    dto = use_case.execute(
        CreateTrainingPreflightRunRequest(release_id, _config(), validate_image_paths=False)
    )

    assert dto.status == TrainingPreflightStatus.PASSED


def test_validate_image_paths_true_detects_missing_paths_and_saves_issues():
    release_id = uuid4()
    manifest = _manifest(release_id=release_id)
    use_case, _, _, _ = _use_case(manifest)

    dto = use_case.execute(
        CreateTrainingPreflightRunRequest(release_id, _config(), validate_image_paths=True)
    )

    assert dto.status == TrainingPreflightStatus.FAILED
    assert any("does not exist" in issue.message for issue in dto.issues)
    assert all(issue.severity == TrainingPreflightIssueSeverity.ERROR for issue in dto.issues)


def test_does_not_modify_dataset_release_or_dataset_item():
    release_repo = InMemoryDatasetReleaseRepository()
    split_repo = InMemoryDatasetSplitItemRepository()
    item_repo = InMemoryDatasetItemRepository()
    sample_repo = InMemorySampleRepository()
    petri_repo = InMemoryPetriImageRepository()
    micro_repo = InMemoryMicroImageRepository()
    prediction_repo = InMemoryPredictionRepository()
    release, dataset_item = _seed_release_graph(
        release_repo,
        split_repo,
        item_repo,
        sample_repo,
        petri_repo,
        micro_repo,
        prediction_repo,
    )
    release_before = copy.deepcopy(release)
    item_before = copy.deepcopy(dataset_item)
    run_repo = InMemoryTrainingPreflightRunRepository()
    issue_repo = InMemoryTrainingPreflightIssueRepository()
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        training_preflight_run_repository=run_repo,
        training_preflight_issue_repository=issue_repo,
    )
    exporter = DatasetReleaseManifestExporter(
        release_repo,
        split_repo,
        item_repo,
        sample_repo,
        petri_repo,
        micro_repo,
        prediction_repo,
    )
    use_case = CreateTrainingPreflightRunUseCase(exporter, ManifestValidator(), ImagePathValidator(), uow)

    use_case.execute(CreateTrainingPreflightRunRequest(release.id, _config()))

    assert release_repo.get_by_id(release.id) == release_before
    assert item_repo.list_by_dataset_snapshot_id(release.dataset_snapshot_id)[0] == item_before


def test_issue_persistence_failure_rolls_back_preflight_run():
    release_id = uuid4()
    run_repo = InMemoryTrainingPreflightRunRepository()
    issue_repo = _FailingTrainingPreflightIssueRepository()
    use_case, _, _, _ = _use_case(
        _manifest([_item(1, "train", "suspicious_growth"), _item(2, "test", "no_evident_growth")], release_id),
        issue_repo=issue_repo,
        run_repo=run_repo,
    )

    with pytest.raises(RuntimeError):
        use_case.execute(CreateTrainingPreflightRunRequest(release_id, _config()))

    assert run_repo.list_all() == []
    assert issue_repo._by_id == {}


def _seed_release_graph(
    release_repo,
    split_repo,
    item_repo,
    sample_repo,
    petri_repo,
    micro_repo,
    prediction_repo,
):
    snapshot_id = uuid4()
    sample = sample_repo.add(Sample(sample_code="S-PREFLIGHT", lot_code="L-1", origin="farm-a"))
    petri = petri_repo.add(
        PetriImage(
            sample_id=sample.id,
            file_path="petri.jpg",
            file_name="petri.jpg",
            mime_type="image/jpeg",
            file_size_bytes=10,
        )
    )
    micro = micro_repo.add(
        MicroImage(
            sample_id=sample.id,
            file_path="micro.png",
            file_name="micro.png",
            mime_type="image/png",
            file_size_bytes=10,
        )
    )
    analysis_run_id = uuid4()
    prediction = prediction_repo.add(
        Prediction(analysis_run_id=analysis_run_id, predicted_label=PredictedLabel.SUSPICIOUS_GROWTH)
    )
    dataset_item = DatasetItem(
        dataset_snapshot_id=snapshot_id,
        analysis_run_id=analysis_run_id,
        sample_id=sample.id,
        petri_image_id=petri.id,
        micro_image_id=micro.id,
        prediction_id=prediction.id,
        final_review_id=uuid4(),
        source_review_decision=ReviewDecision.CONFIRMED,
        ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
    )
    item_repo.add_many([dataset_item])
    release = release_repo.add(
        DatasetRelease(
            dataset_snapshot_id=snapshot_id,
            name="release",
            version="0.1.0",
            split_strategy=SplitStrategy.BY_SAMPLE,
            random_seed=42,
            train_ratio=0.7,
            validation_ratio=0.15,
            test_ratio=0.15,
            item_count=1,
            test_count=1,
            label_distribution={"suspicious_growth": 1},
            split_distribution={"test": {"suspicious_growth": 1}},
        )
    )
    split_repo.add_many(
        [
            DatasetSplitItem(
                dataset_release_id=release.id,
                dataset_item_id=dataset_item.id,
                sample_id=sample.id,
                split=DatasetSplit.TEST,
                ground_truth_label=PredictedLabel.SUSPICIOUS_GROWTH,
            )
        ]
    )
    return release, dataset_item
