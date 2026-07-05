from uuid import uuid4

import pytest

from blueberry_microid.application.dto.dataset_curation_dto import (
    SnapshotFromCurationPolicy,
    SnapshotFromCurationRunRequestDTO,
)
from blueberry_microid.application.exceptions import DatasetSnapshotFromCurationNotAllowedError
from blueberry_microid.application.services.snapshot_from_curation_evaluator import (
    SnapshotFromCurationRunEvaluator,
)
from blueberry_microid.application.use_cases.dataset.create_dataset_snapshot_from_curation_run import (
    CreateDatasetSnapshotFromCurationRunUseCase,
)
from blueberry_microid.domain.entities.dataset_curation_item import DatasetCurationItem
from blueberry_microid.domain.entities.dataset_curation_run import DatasetCurationRun
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetCurationItemRepository,
    InMemoryDatasetCurationRunRepository,
    InMemoryDatasetItemRepository,
    InMemoryDatasetSnapshotRepository,
    InMemoryPredictionRepository,
)


def _included_item(curation_run_id, *, analysis_run_id=None, final_label=None):
    return DatasetCurationItem(
        curation_run_id=curation_run_id,
        curation_status=DatasetCurationStatus.INCLUDED,
        sample_id=uuid4(),
        analysis_run_id=analysis_run_id or uuid4(),
        prediction_id=uuid4(),
        human_review_id=uuid4(),
        petri_image_id=uuid4(),
        micro_image_id=uuid4(),
        automatic_label=PredictedLabel.SUSPICIOUS_GROWTH,
        final_label=final_label or PredictedLabel.SUSPICIOUS_GROWTH,
        review_decision=ReviewDecision.CONFIRMED,
        provenance={"prediction_is_ground_truth": False},
    )


def _uow(curation_run, curation_items):
    run_repo = InMemoryDatasetCurationRunRepository()
    run_repo.add(curation_run)
    item_repo = InMemoryDatasetCurationItemRepository()
    item_repo.add_many(curation_items)
    snapshot_repo = InMemoryDatasetSnapshotRepository()
    dataset_item_repo = InMemoryDatasetItemRepository()
    return (
        FakeUnitOfWork(
            InMemoryAnalysisRunRepository(),
            InMemoryPredictionRepository(),
            dataset_snapshot_repository=snapshot_repo,
            dataset_item_repository=dataset_item_repo,
            dataset_curation_run_repository=run_repo,
            dataset_curation_item_repository=item_repo,
        ),
        run_repo,
        item_repo,
        snapshot_repo,
        dataset_item_repo,
    )


def test_snapshot_evaluator_uses_only_included_human_reviewed_curation_items():
    curation_run = DatasetCurationRun()
    included = _included_item(curation_run.id)
    excluded = DatasetCurationItem(
        curation_run_id=curation_run.id,
        curation_status=DatasetCurationStatus.EXCLUDED_PENDING_REVIEW,
        sample_id=uuid4(),
        analysis_run_id=uuid4(),
    )

    result = SnapshotFromCurationRunEvaluator().evaluate(
        curation_run=curation_run,
        curation_items=[included, excluded],
        policy=SnapshotFromCurationPolicy(),
    )

    assert result.included_items_for_snapshot == [included]
    assert result.skipped_items == [excluded]
    assert result.labels_distribution == {"suspicious_growth": 1}


def test_snapshot_evaluator_skips_duplicate_analysis_runs():
    curation_run = DatasetCurationRun()
    analysis_run_id = uuid4()
    first = _included_item(curation_run.id, analysis_run_id=analysis_run_id)
    duplicate = _included_item(curation_run.id, analysis_run_id=analysis_run_id)

    result = SnapshotFromCurationRunEvaluator().evaluate(
        curation_run=curation_run,
        curation_items=[first, duplicate],
        policy=SnapshotFromCurationPolicy(),
    )

    assert result.included_items_for_snapshot == [first]
    assert result.duplicate_items_skipped == 1
    assert any("duplicate analysis_run_id" in warning for warning in result.warnings)


def test_create_snapshot_from_curation_run_persists_provenance_and_back_reference():
    curation_run = DatasetCurationRun()
    curation_item = _included_item(curation_run.id)
    uow, run_repo, _, snapshot_repo, dataset_item_repo = _uow(curation_run, [curation_item])

    result = CreateDatasetSnapshotFromCurationRunUseCase(
        SnapshotFromCurationRunEvaluator(),
        uow,
    ).execute(
        SnapshotFromCurationRunRequestDTO(
            curation_run_id=curation_run.id,
            snapshot_name="reviewed-blueberry-smoke",
            created_by="tester",
        )
    )

    updated_run = run_repo.get_by_id(curation_run.id)
    snapshot = snapshot_repo.get_by_id(result.snapshot_id)
    dataset_items = dataset_item_repo.list_by_dataset_snapshot_id(result.snapshot_id)

    assert result.status == "completed"
    assert result.dataset_items_created == 1
    assert updated_run is not None
    assert updated_run.created_snapshot_id == result.snapshot_id
    assert snapshot is not None
    assert snapshot.selection_criteria["source"] == "human_reviewed_curation_run"
    assert snapshot.item_count == 1
    assert dataset_items[0].curation_run_id == curation_run.id
    assert dataset_items[0].curation_item_id == curation_item.id
    assert dataset_items[0].provenance["ground_truth_source"] == "final_human_review"
    assert dataset_items[0].provenance["prediction_is_ground_truth"] is False


def test_create_snapshot_from_curation_run_rejects_second_snapshot():
    existing_snapshot_id = uuid4()
    curation_run = DatasetCurationRun(created_snapshot_id=existing_snapshot_id)
    curation_item = _included_item(curation_run.id)
    uow, _, _, _, _ = _uow(curation_run, [curation_item])

    use_case = CreateDatasetSnapshotFromCurationRunUseCase(
        SnapshotFromCurationRunEvaluator(),
        uow,
    )

    with pytest.raises(DatasetSnapshotFromCurationNotAllowedError):
        use_case.execute(SnapshotFromCurationRunRequestDTO(curation_run_id=curation_run.id))


def test_create_snapshot_from_curation_run_excludes_inconclusive_when_requested():
    curation_run = DatasetCurationRun()
    curation_item = _included_item(curation_run.id, final_label=PredictedLabel.INCONCLUSIVE)
    uow, _, _, _, _ = _uow(curation_run, [curation_item])

    use_case = CreateDatasetSnapshotFromCurationRunUseCase(
        SnapshotFromCurationRunEvaluator(),
        uow,
    )

    with pytest.raises(DatasetSnapshotFromCurationNotAllowedError):
        use_case.execute(
            SnapshotFromCurationRunRequestDTO(
                curation_run_id=curation_run.id,
                include_inconclusive=False,
            )
        )
