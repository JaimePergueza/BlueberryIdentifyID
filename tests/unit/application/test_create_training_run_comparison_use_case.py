from datetime import datetime, timezone
from uuid import uuid4

import pytest

from blueberry_microid.application.dto.training_run_comparison_dto import CreateTrainingRunComparisonRequest
from blueberry_microid.application.exceptions import TrainingRunComparisonNotAllowedError
from blueberry_microid.application.services.training_run_comparator import TrainingRunComparator
from blueberry_microid.application.use_cases.training.create_training_run_comparison import (
    CreateTrainingRunComparisonUseCase,
)
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.training_run import TrainingRun
from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.comparison_selection_policy import ComparisonSelectionPolicy
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetReleaseRepository,
    InMemoryPredictionRepository,
    InMemoryTrainingRunComparisonEntryRepository,
    InMemoryTrainingRunComparisonRepository,
    InMemoryTrainingRunRepository,
)


def _release() -> DatasetRelease:
    return DatasetRelease(
        dataset_snapshot_id=uuid4(),
        name="comparison-release",
        version="0.1.0",
        split_strategy=SplitStrategy.BY_SAMPLE,
        random_seed=17,
        train_ratio=0.5,
        validation_ratio=0.25,
        test_ratio=0.25,
        item_count=4,
        train_count=2,
        validation_count=1,
        test_count=1,
    )


def _training_run(dataset_release_id, model_type, test_accuracy) -> TrainingRun:
    return TrainingRun(
        dataset_release_id=dataset_release_id,
        preflight_run_id=uuid4(),
        run_kind=TrainingRunKind.BASELINE,
        baseline_model_type=model_type,
        status=TrainingRunStatus.COMPLETED,
        experiment_name=f"{model_type.value}-comparison",
        config={},
        baseline_state={},
        metrics={
            "accuracy_by_split": {"train": 1.0, "validation": 0.5, "test": test_accuracy},
            "support_by_split": {"train": 2, "validation": 1, "test": 1},
        },
        summary={"contains_deep_learning": False},
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


def _use_case():
    release_repo = InMemoryDatasetReleaseRepository()
    run_repo = InMemoryTrainingRunRepository()
    comparison_repo = InMemoryTrainingRunComparisonRepository()
    entry_repo = InMemoryTrainingRunComparisonEntryRepository()
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        dataset_release_repository=release_repo,
        training_run_repository=run_repo,
        training_run_comparison_repository=comparison_repo,
        training_run_comparison_entry_repository=entry_repo,
    )
    use_case = CreateTrainingRunComparisonUseCase(
        release_repo,
        run_repo,
        TrainingRunComparator(),
        uow,
    )
    return use_case, release_repo, run_repo, comparison_repo, entry_repo, uow


def test_create_training_run_comparison_persists_snapshot_entries_and_selection():
    use_case, release_repo, run_repo, comparison_repo, entry_repo, uow = _use_case()
    release = _release()
    release_repo.add(release)
    majority = _training_run(release.id, BaselineModelType.MAJORITY_CLASS, 0.25)
    classical = _training_run(release.id, BaselineModelType.LOGISTIC_REGRESSION_TABULAR, 0.75)
    run_repo.add(majority)
    run_repo.add(classical)

    dto = use_case.execute(
        CreateTrainingRunComparisonRequest(
            dataset_release_id=release.id,
            training_run_ids=[majority.id, classical.id],
            name="phase-17-comparison",
            selection_policy=ComparisonSelectionPolicy.BEST_PRIMARY_METRIC,
            created_by="qa",
        )
    )

    assert dto.dataset_release_id == release.id
    assert dto.selected_training_run_id == classical.id
    assert dto.comparison_summary["contains_deep_learning"] is False
    assert dto.comparison_summary["selection_is_preliminary"] is True
    assert [entry.training_run_id for entry in dto.entries] == [classical.id, majority.id]
    assert dto.entries[0].rank == 1
    assert dto.entries[0].primary_metric_value == 0.75
    assert uow.committed is True
    assert comparison_repo.get_by_id(dto.id) is not None
    assert len(entry_repo.list_by_comparison_id(dto.id)) == 2


def test_create_training_run_comparison_requires_unique_runs_same_release_and_completed_metrics():
    use_case, release_repo, run_repo, _comparison_repo, _entry_repo, _uow = _use_case()
    release = _release()
    other_release = _release()
    release_repo.add(release)
    release_repo.add(other_release)
    majority = _training_run(release.id, BaselineModelType.MAJORITY_CLASS, 0.25)
    other = _training_run(other_release.id, BaselineModelType.LOGISTIC_REGRESSION_TABULAR, 0.75)
    run_repo.add(majority)
    run_repo.add(other)

    with pytest.raises(TrainingRunComparisonNotAllowedError, match="unique"):
        use_case.execute(
            CreateTrainingRunComparisonRequest(
                dataset_release_id=release.id,
                training_run_ids=[majority.id, majority.id],
                name="duplicate",
            )
        )

    with pytest.raises(TrainingRunComparisonNotAllowedError, match="does not belong"):
        use_case.execute(
            CreateTrainingRunComparisonRequest(
                dataset_release_id=release.id,
                training_run_ids=[majority.id, other.id],
                name="mixed-release",
            )
        )
