from uuid import uuid4

import pytest

from blueberry_microid.application.dto.dataset_dto import CreateDatasetReleaseFromSnapshotRequest
from blueberry_microid.application.exceptions import (
    DatasetSnapshotNotFoundError,
    DuplicateDatasetReleaseError,
    EmptyDatasetSnapshotError,
)
from blueberry_microid.application.services.dataset_release_from_snapshot_evaluator import (
    DatasetReleaseFromSnapshotEvaluator,
)
from blueberry_microid.application.use_cases.dataset.create_dataset_release_from_snapshot import (
    CreateDatasetReleaseFromSnapshotUseCase,
)
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.review_decision import ReviewDecision
from tests.unit.application.fakes import (
    FakeUnitOfWork,
    InMemoryAnalysisRunRepository,
    InMemoryDatasetItemRepository,
    InMemoryDatasetReleaseRepository,
    InMemoryDatasetSnapshotRepository,
    InMemoryPredictionRepository,
)


def _make_context():
    snapshot_repo = InMemoryDatasetSnapshotRepository()
    item_repo = InMemoryDatasetItemRepository()
    release_repo = InMemoryDatasetReleaseRepository()
    uow = FakeUnitOfWork(
        InMemoryAnalysisRunRepository(),
        InMemoryPredictionRepository(),
        dataset_snapshot_repository=snapshot_repo,
        dataset_item_repository=item_repo,
        dataset_release_repository=release_repo,
    )
    use_case = CreateDatasetReleaseFromSnapshotUseCase(
        snapshot_repo,
        item_repo,
        DatasetReleaseFromSnapshotEvaluator(),
        uow,
    )
    return snapshot_repo, item_repo, release_repo, use_case


def _reviewed_item(snapshot_id, *, label=PredictedLabel.SUSPICIOUS_GROWTH):
    return DatasetItem(
        dataset_snapshot_id=snapshot_id,
        analysis_run_id=uuid4(),
        sample_id=uuid4(),
        petri_image_id=uuid4(),
        micro_image_id=uuid4(),
        prediction_id=uuid4(),
        final_review_id=uuid4(),
        curation_run_id=uuid4(),
        curation_item_id=uuid4(),
        source_review_decision=ReviewDecision.CONFIRMED,
        ground_truth_label=label,
        provenance={"ground_truth_source": "final_human_review"},
    )


def test_create_snapshot_release_requires_existing_snapshot():
    _, _, _, use_case = _make_context()

    with pytest.raises(DatasetSnapshotNotFoundError):
        use_case.execute(
            CreateDatasetReleaseFromSnapshotRequest(
                dataset_snapshot_id=uuid4(),
                name="snapshot-release",
                version="0.1.0",
            )
        )


def test_create_snapshot_release_rejects_empty_snapshot_by_default():
    snapshot_repo, _, _, use_case = _make_context()
    snapshot = DatasetSnapshot(name="empty-snapshot", version="0.1.0")
    snapshot_repo.add(snapshot)

    with pytest.raises(EmptyDatasetSnapshotError):
        use_case.execute(
            CreateDatasetReleaseFromSnapshotRequest(
                dataset_snapshot_id=snapshot.id,
                name="snapshot-release",
                version="0.1.0",
            )
        )


def test_create_snapshot_release_persists_metadata_manifest_and_provenance():
    snapshot_repo, item_repo, release_repo, use_case = _make_context()
    snapshot = DatasetSnapshot(name="curated-snapshot", version="0.1.0")
    snapshot_repo.add(snapshot)
    item = _reviewed_item(snapshot.id)
    item_repo.add_many([item])

    release = use_case.execute(
        CreateDatasetReleaseFromSnapshotRequest(
            dataset_snapshot_id=snapshot.id,
            name="snapshot-release",
            version="0.1.0",
            description="metadata-only release",
            created_by="qa",
            notes="snapshot-only export",
        )
    )

    assert release.release_kind.value == "snapshot_release"
    assert release.status == "completed"
    assert release.description == "metadata-only release"
    assert release.item_count == 1
    assert release.train_count == 0
    assert release.validation_count == 0
    assert release.test_count == 0
    assert release.label_distribution == {"suspicious_growth": 1}
    assert release.split_distribution is None
    assert release.provenance["eligible_item_count"] == 1
    assert release.provenance["split_oriented"] is False
    assert release.manifest["dataset_release_id"] == str(release.id)
    assert release.manifest["dataset_snapshot_id"] == str(snapshot.id)
    assert release.manifest["items"][0]["dataset_item_id"] == str(item.id)
    assert release.manifest["items"][0]["curation_run_id"] == str(item.curation_run_id)
    assert release.manifest["items"][0]["curation_item_id"] == str(item.curation_item_id)
    assert release_repo.get_by_id(release.id) is not None


def test_create_snapshot_release_rejects_duplicate_name_version_for_snapshot():
    snapshot_repo, item_repo, _, use_case = _make_context()
    snapshot = DatasetSnapshot(name="curated-snapshot", version="0.1.0")
    snapshot_repo.add(snapshot)
    item_repo.add_many([_reviewed_item(snapshot.id)])
    request = CreateDatasetReleaseFromSnapshotRequest(
        dataset_snapshot_id=snapshot.id,
        name="snapshot-release",
        version="0.1.0",
    )
    use_case.execute(request)

    with pytest.raises(DuplicateDatasetReleaseError):
        use_case.execute(request)


def test_create_snapshot_release_can_allow_empty_release_explicitly():
    snapshot_repo, _, _, use_case = _make_context()
    snapshot = DatasetSnapshot(name="empty-allowed", version="0.1.0")
    snapshot_repo.add(snapshot)

    release = use_case.execute(
        CreateDatasetReleaseFromSnapshotRequest(
            dataset_snapshot_id=snapshot.id,
            name="empty-release",
            version="0.1.0",
            allow_empty_release=True,
        )
    )

    assert release.item_count == 0
    assert release.manifest["items"] == []


def test_create_snapshot_release_can_exclude_inconclusive():
    snapshot_repo, item_repo, _, use_case = _make_context()
    snapshot = DatasetSnapshot(name="inconclusive-snapshot", version="0.1.0")
    snapshot_repo.add(snapshot)
    item_repo.add_many([_reviewed_item(snapshot.id, label=PredictedLabel.INCONCLUSIVE)])

    with pytest.raises(EmptyDatasetSnapshotError):
        use_case.execute(
            CreateDatasetReleaseFromSnapshotRequest(
                dataset_snapshot_id=snapshot.id,
                name="no-inconclusive-release",
                version="0.1.0",
                include_inconclusive=False,
            )
        )
