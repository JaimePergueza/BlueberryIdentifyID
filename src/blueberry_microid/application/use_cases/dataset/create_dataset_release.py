from __future__ import annotations

from blueberry_microid.application.dto.dataset_dto import CreateDatasetReleaseRequest, DatasetReleaseDTO
from blueberry_microid.application.exceptions import DatasetSnapshotNotFoundError, EmptyDatasetSnapshotError
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.dataset_splitter import DatasetSplitter, SampleSplitMetadata
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.enums.split_strategy import SplitStrategy


class CreateDatasetReleaseUseCase:
    """Create a reproducible train/validation/test DatasetRelease from an
    existing DatasetSnapshot.

    Never modifies the DatasetSnapshot or its DatasetItems — it only reads
    the snapshot's already-`included` items, partitions them deterministically
    according to `request.split_strategy` (see `DatasetSplitter`), and
    persists the resulting DatasetRelease + DatasetSplitItems atomically.
    """

    def __init__(
        self,
        dataset_snapshot_repository: DatasetSnapshotRepositoryPort,
        dataset_item_repository: DatasetItemRepositoryPort,
        sample_repository: SampleRepositoryPort,
        dataset_splitter: DatasetSplitter,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._dataset_snapshot_repository = dataset_snapshot_repository
        self._dataset_item_repository = dataset_item_repository
        self._sample_repository = sample_repository
        self._dataset_splitter = dataset_splitter
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateDatasetReleaseRequest) -> DatasetReleaseDTO:
        snapshot = self._dataset_snapshot_repository.get_by_id(request.dataset_snapshot_id)
        if snapshot is None:
            raise DatasetSnapshotNotFoundError(f"dataset_snapshot '{request.dataset_snapshot_id}' does not exist")

        items = [
            item
            for item in self._dataset_item_repository.list_by_dataset_snapshot_id(request.dataset_snapshot_id)
            if item.included
        ]
        if not items:
            raise EmptyDatasetSnapshotError(
                f"dataset_snapshot '{request.dataset_snapshot_id}' has no included items to release"
            )

        # Sample metadata (lot_code/origin) is only needed by strategies
        # stricter than the default — skip the extra repository round-trips
        # entirely for the common `by_sample` case.
        sample_metadata = None
        if request.split_strategy != SplitStrategy.BY_SAMPLE:
            sample_metadata = self._load_sample_metadata(items)

        result = self._dataset_splitter.split(
            items,
            train_ratio=request.train_ratio,
            validation_ratio=request.validation_ratio,
            test_ratio=request.test_ratio,
            random_seed=request.random_seed,
            strategy=request.split_strategy,
            sample_metadata=sample_metadata,
        )

        # Ratio validation already happened inside the splitter (before any
        # grouping/shuffling work); constructing the entity re-validates the
        # same invariant as a domain-level defense-in-depth check.
        release = DatasetRelease(
            dataset_snapshot_id=request.dataset_snapshot_id,
            name=request.name,
            version=request.version,
            split_strategy=request.split_strategy,
            random_seed=request.random_seed,
            train_ratio=request.train_ratio,
            validation_ratio=request.validation_ratio,
            test_ratio=request.test_ratio,
            item_count=result.item_count,
            train_count=result.train_count,
            validation_count=result.validation_count,
            test_count=result.test_count,
            label_distribution=result.label_distribution,
            split_distribution=result.split_distribution,
            created_by=request.created_by,
            notes=request.notes,
        )
        split_items = [
            DatasetSplitItem(
                dataset_release_id=release.id,
                dataset_item_id=assignment.dataset_item_id,
                sample_id=assignment.sample_id,
                split=assignment.split,
                ground_truth_label=assignment.ground_truth_label,
            )
            for assignment in result.assignments
        ]

        with self._unit_of_work as uow:
            created_release = uow.dataset_release_repository.add(release)
            uow.dataset_split_item_repository.add_many(split_items)
            uow.commit()

        return DatasetReleaseDTO.from_entity(created_release)

    def _load_sample_metadata(self, items) -> dict:
        """Resolve `lot_code`/`origin` for every Sample referenced by
        `items`. `DatasetItem` itself never carries this — it only has to
        exist because the strategy needs to group by it (see
        ARCHITECTURE.md for why `DatasetItem` was not widened instead).
        """
        metadata: dict = {}
        for sample_id in {item.sample_id for item in items}:
            if sample_id in metadata:
                continue
            sample = self._sample_repository.get_by_id(sample_id)
            if sample is None:
                # A DatasetItem's sample_id is a foreign key to samples.id,
                # so this should be unreachable outside of data corruption —
                # DatasetSplitter's own metadata check below only ever fires
                # for a *missing lot_code/origin*, not a missing Sample.
                continue
            metadata[sample_id] = SampleSplitMetadata(
                sample_id=sample.id, lot_code=sample.lot_code, origin=sample.origin
            )
        return metadata
